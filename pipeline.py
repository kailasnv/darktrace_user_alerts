"""
Core alert pipeline: dedup, sort by severity, decide where each alert goes. 
-both a manual run (main.py) and the automatic scheduled trigger (run_pipeline_task)
call this same function, so there's never two competing copies.
"""
from hardcoded_alerts import ALERTS  # hardcoded alerts for testing purposes
from tasks import send_immediate_email_task, send_batched_medium_task, send_daily_digest_task
from celery_app import celery_app
 

# severity ranking +  channel map.
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}

""" Lower rank = more urgent. 
Channels beyond email are listed for reference/task-allocation, but only email is actually wired up below for now.
 -- everything else just prints what WOULD have been notified.
"""

# Currently only email is implemented, but this dict shows what channels would be used for each severity level.
SEVERITY_CHANNELS = {
    "critical": ["email", "webhook", "dashboard", "sms", "siem"],
    "high": ["email", "webhook", "dashboard"],
    "medium": ["email", "dashboard"],
    "low": ["email", "dashboard"],
    "informational": ["email", "dashboard"],
}

#EMAIL DELAYS
MEDIUM_BATCH_DELAY_SECONDS = 300 #5minuts
DIGEST_DELAY_SECONDS = 360 #5minuts - demo - needed to change to for like 1 day


# deduplication function for alerts
def dedupe_alerts(alerts):
    merged = {} 

    for alert in alerts:
        fp = alert["fingerprint"]

        already_seen = fp in merged
        if already_seen == False:
            # First time seeing this fingerprint -- just store it.
            merged[fp] = dict(alert)  
        else:
            # We've seen this fingerprint before -- merge instead of adding a second, separate alert.
            existing_alert = merged[fp]
            # Add the new duplicate's count onto the existing total.
            # old_count = existing_alert["count"]
            # new_count = alert["count"]
            existing_alert["count"] = existing_alert["count"] + alert["count"]

            # Keep the higher of the two confidence scores.
            old_confidence = existing_alert["confidence"]
            new_confidence = alert["confidence"]
            if new_confidence > old_confidence:
                existing_alert["confidence"] = new_confidence

    # We just want the alert dicts, not the fingerprint labels.
    result = []
    for alert_dict in merged.values():
        result.append(alert_dict)
        #print(f"resulttttttttttttttttttttt {result}")
    return result



def process_and_dispatch(alerts, already_processed=None):
    """ ------------------------------------------------------------
   `already_processed`: optional set of alert_ids to SKIP. 
    Manual runs (main.py) don't pass this -- every alert dispatches for firsttime from ALERTS.

    The scheduled trigger DOES pass it, so re-running on the same static list every 30s doesn't re-email the same alerts forever. 
    Returns the list of alert_ids actually dispatched this run. 
    ------------------------------------------------------------ """
 
    print(f"[+] Starting with {len(alerts)} raw alerts.\n")
 
    deduped = dedupe_alerts(alerts)
    print(f"[+] {len(deduped)} unique alerts after dedup.\n")
 
    deduped.sort(key=lambda a: SEVERITY_RANK[a["severity"]])  # sort based on severity ranks
 
    medium_batch = []
    digest_batch = []
    newly_dispatched = [] # this list will be used to know already dispatched alerts.
 
    for alert in deduped:
        if already_processed is not None and alert["alert_id"] in already_processed:
            continue  # already handled by an earlier scheduled run
 
        channels = SEVERITY_CHANNELS[alert["severity"]]
        print(f"[+] Alert: {alert['alert_id']} [{alert['severity'].upper()}] | channels: {channels}")
 
        if "email" not in channels:
            print(f"[+] Skipping email for {alert['alert_id']} -- not in its channel list")
            print("====================================================================\n")
            continue
 
        if alert["severity"] in ("critical", "high"):
            send_immediate_email_task.delay(alert)
            print(f"[+] Queued immediate email for {alert['alert_id']}")
        elif alert["severity"] == "medium":
            medium_batch.append(alert)
            print(f"[+] Added {alert['alert_id']} to the medium batch")
        else:
            digest_batch.append(alert)
            print(f"[+] Added {alert['alert_id']} to the digest batch")
 
        newly_dispatched.append(alert["alert_id"])
        print("====================================================================\n")
 
    if medium_batch:
        send_batched_medium_task.apply_async(args=[medium_batch], countdown=MEDIUM_BATCH_DELAY_SECONDS)
        print(f"[+] Scheduled batched medium email for {len(medium_batch)} alert(s) in {MEDIUM_BATCH_DELAY_SECONDS}s")
 
    if digest_batch:
        send_daily_digest_task.apply_async(args=[digest_batch], countdown=DIGEST_DELAY_SECONDS)
        print(f"[+] Scheduled digest email for {len(digest_batch)} alert(s) in {DIGEST_DELAY_SECONDS}s")
 
    return newly_dispatched
 
 
# --- Automatic trigger ---  --- -- -- -- 
""" This set lives in the worker's memory and persists across every scheduled run, AS LONG AS the worker process itself isn't restarted. 
If the worker restarts, this resets and one duplicate round of emails is possible -- acceptable for a demo, 
"""
import os
import redis
 
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis_client = redis.from_url(REDIS_URL, decode_responses=True)
PROCESSED_KEY = "darktrace:already_processed_alert_ids"
 
 
class RedisProcessedSet:
    """Drop-in replacement for a Python set (supports `in` and .update()),
    but backed by a Redis set so every worker process sees the same data."""
 
    def __contains__(self, alert_id):
        return _redis_client.sismember(PROCESSED_KEY, alert_id)
 
    def update(self, alert_ids):
        if alert_ids:
            _redis_client.sadd(PROCESSED_KEY, *alert_ids)
 
 
_already_processed = RedisProcessedSet()
 
 
@celery_app.task
def run_pipeline_task():
    newly = process_and_dispatch(ALERTS, already_processed=_already_processed)
    _already_processed.update(newly)
    if not newly:
        print("[+] Scheduled run: nothing new -- all alerts already processed.")