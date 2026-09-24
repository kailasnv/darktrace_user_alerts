""" Email sending Logic. 
"""

import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()
 
from email_templates import render_email, render_batch_email


SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")



# this takes ready subject and body and send email / just prints if smtp is not configured
def send_raw(subject: str, body: str, label: str = ""):
    #if SMTP isnot configued, just run a DRY run for testing.
    if not SMTP_HOST:
        print(f"[+] ---- DRY RUN EMAIL {label} ----")
        print(f"[+] To: {EMAIL_TO}\nSubject: {subject}\n\n")
        return True

    if not EMAIL_TO:
        print(f"[FAILED] {label} email error: EMAIL_TO is not set in .env")
        return False

    try:
        msg = MIMEText(body,"html") # using html templates
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
        print(f"[sent] {label} email delivered.")
        return True
    except Exception as exc:
        print(f"[FAILED] {label} email error: {exc}")
        return False


 
# Single alert send -- used for critical/high, sent immediately.
def send_email(alert: dict) -> bool:
    subject, body = render_email(alert)
    label = f"[{alert['severity'].upper()}] {alert['alert_id']}"
    return send_raw(subject, body, label=label)
 


# Combines several alerts into ONE email -- used for medium
#(batched every 5-15 min) and low/informational (daily digest).

#The looping over alerts now happens inside batch.html via Jinja2 
def send_batch_email(alerts: list, title: str) -> bool:
    if not alerts:
        return True
 
    subject, body = render_batch_email(alerts, title)
    return send_raw(subject, body, label=title)