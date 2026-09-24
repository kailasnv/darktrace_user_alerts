from hardcoded_alerts import ALERTS  # hardcoded alerts for testing purposes
from tasks import (
    send_immediate_email_task,
    send_batched_medium_task,
    send_daily_digest_task,
)



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
MEDIUM_BATCH_DELAY_SECONDS = 300 # How long to wait before sending each batch- 5min=300s
DIGEST_DELAY_SECONDS = 60  # demo value, not a real "once a day" delay
 

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


 

def main():
    print(f"[+] Starting with {len(ALERTS)} raw alerts.\n")
 
    deduped = dedupe_alerts(ALERTS)
    print(f"[+] {len(deduped)} unique alerts after dedup.\n")
     
    # Most urgent first -- sort based on severity rank.
    deduped.sort(key=lambda a: SEVERITY_RANK[a["severity"]])


    medium_batch = []
    digest_batch = []
    for alert in deduped:
        channels = SEVERITY_CHANNELS[alert["severity"]]
 
        print(f"[+] Alert: {alert['alert_id']} [{alert['severity'].upper()}] "
              f"| channels: {channels}")

        if "email" not in channels:
            print(f"[+] Skipping email for {alert['alert_id']} -- not in its channel list")
            print(f"====================================================================\n")
            continue

        # logic for sending email based on severity
        if alert["severity"] in ("critical", "high"):
            send_immediate_email_task.delay(alert)
            print(f"[+] Queued immediate email for {alert['alert_id']}")
        elif alert["severity"] == "medium":
            medium_batch.append(alert)
            print(f"[+] Added {alert['alert_id']} to the medium batch")
        else: # for low / informational
            digest_batch.append(alert)
            print(f"[+] Added {alert['alert_id']} to the digest batch")
 
        print(f"====================================================================\n")


    if medium_batch:
        send_batched_medium_task.apply_async(
            args=[medium_batch], countdown=MEDIUM_BATCH_DELAY_SECONDS
        )
        print(f"[+] Scheduled batched medium email for {len(medium_batch)} "
              f"alert(s) in {MEDIUM_BATCH_DELAY_SECONDS}s")
 
    if digest_batch:
        send_daily_digest_task.apply_async(
            args=[digest_batch], countdown=DIGEST_DELAY_SECONDS
        )
        print(f"[+] Scheduled digest email for {len(digest_batch)} alert(s) "
              f"in {DIGEST_DELAY_SECONDS}s (demo delay -- production would use "
              f"Celery Beat on a fixed daily schedule instead)")
 
 
if __name__ == "__main__":
    main()
