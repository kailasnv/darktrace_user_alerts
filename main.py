""" Email alerting module """

import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()


from hardcoded_alerts import ALERTS  # hardcoded alerts for testing purposes
from email_templates import EMAIL_TEMPLATES  # severity-specific email templates





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
def render_email(alert: dict) -> tuple[str, str]:
    template = EMAIL_TEMPLATES[alert["severity"]]
    body = template.format(**alert)  # **alert unpacks the dict into keyword arguments.
    subject = f"[{alert['severity'].upper()}] DarkTrace alert {alert['alert_id']}"
    return subject, body
 

# send email. 
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")
 
 
def send_email(alert):
    subject, body = render_email(alert)

 #(if SMTP not configured, just prints to stdout for dry-run testing)
    if not SMTP_HOST:
        print(f"\n\n[+] --- DRY RUN EMAIL [{alert['severity'].upper()}] ---")
        print(f"[+] To: {EMAIL_TO}\nSubject: {subject}\n{body}\n")
        return True
 
    try:
        msg = MIMEText(body)
        #Wraps your plain-text email body into a properly formatted email message object — MIMEText
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
 
        print(f"[+] Alert: {alert['alert_id']} [{alert['severity'].upper()}] "
              f"| channels: {channels}")
 
        send_email(alert)
 
        print(f"====================================================================\n")
 
 
if __name__ == "__main__":
    main()
 