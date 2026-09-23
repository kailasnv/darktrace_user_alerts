""" Email alerting module """

import os
import smtplib
from email.mime.text import MIMEText

from hardcoded_alerts import ALERTS  # hardcoded alerts for testing purposes
from email_templates import EMAIL_TEMPLATES  # severity-specific email templates





# severity ranking +  channel map.
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}

""" Lower rank = more urgent. 
Channels beyond email are listed for reference/task-allocation, but only email is actually wired up below for now.
 -- everything else just prints what WOULD have been notified.
"""


SEVERITY_CHANNELS = {
    "critical": ["email", "webhook", "dashboard", "sms", "siem"],
    "high": ["email", "webhook", "dashboard"],
    "medium": ["email", "dashboard"],
    "low": ["email", "dashboard"],
    "informational": ["email", "dashboard"],
}


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


 
#Render email using templates
"""Returns (subject, body) using the template for this alert's
    severity. Relies on first_seen/last_seen being real datetime objects
    (not strings) -- that's what makes the {first_seen:%Y-%m-%d %H:%M}
    formatting above work."""

def render_email(alert: dict) -> tuple[str, str]:
    template = EMAIL_TEMPLATES[alert["severity"]]
    body = template.format(**alert)
    subject = f"[{alert['severity'].upper()}] DarkTrace alert {alert['alert_id']}"
    return subject, body
 
 
 

# send email. --  (if not configured, just prints to stdout for dry-run testing)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "alerts@darktrace.local")
EMAIL_TO = os.getenv("EMAIL_TO", "security-team@example.com")
 
 
def send_email(alert):
    subject, body = render_email(alert)
 
    if not SMTP_HOST:
        print(f"\n\n[+] --- DRY RUN EMAIL [{alert['severity'].upper()}] ---")
        print(f"[+] To: {EMAIL_TO}\nSubject: {subject}\n{body}\n")
        return True
 
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

        print(f"[sent] {alert['alert_id']} ({alert['severity']}) email delivered.")
        return True
    except Exception as exc:
        print(f"[FAILED] {alert['alert_id']} email error: {exc}")
        return False
 
 
 
def main():
    print(f"[+] Starting with {len(ALERTS)} raw alerts.\n")
 
    deduped = dedupe_alerts(ALERTS)
    print(f"[+] {len(deduped)} unique alerts after dedup.\n")
     
 
    # Most urgent first -- sort based on severity rank.
    deduped.sort(key=lambda a: SEVERITY_RANK[a["severity"]])
 
    for alert in deduped:
        channels = SEVERITY_CHANNELS[alert["severity"]]
        # other_channels = [c for c in channels if c != "email"]
 
        print(f"[+] Alert: {alert['alert_id']} [{alert['severity'].upper()}] "
              f"| channels: {channels}")
 
        send_email(alert)
 
        # if other_channels:
        #     print(f"  (would also notify via: {', '.join(other_channels)} "
        #           f"-- not implemented in this demo)")
        print(f"====================================================================\n")
 
 
if __name__ == "__main__":
    main()
 