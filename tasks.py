from celery_app import celery_app
from email_sender import send_email, send_batch_email

""" 
rate_limit="20/m" (~1 every 3s) keeps this under Mailtrap's free-tier per-second cap, 
even when several critical/high alerts fire at once across multiple worker processes
"""

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, rate_limit="20/m")
def send_immediate_email_task(self, alert: dict):
    #rate_limit="20/m" (~1 every 3s) keeps this under Mailtrap's free-tier per-second cap, even when several critical/high alerts fire at once across multiple worker processes.

    try:
        success = send_email(alert)
        if not success:
            raise Exception(f"send_email failed for {alert['alert_id']}")
    except Exception as exc:
        raise self.retry(exc=exc)


 
@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_batched_medium_task(self, alerts: list):
    # no ratelimiting needed here
    try:
        success = send_batch_email(alerts, title="Medium Severity Alerts (batched)")
        if not success:
            raise Exception("send_batch_email failed for medium batch")
    except Exception as exc:
        raise self.retry(exc=exc)
 
 
@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_daily_digest_task(self, alerts: list):
    try:
        success = send_batch_email(alerts, title="Daily Digest -- Low/Informational Alerts")
        if not success:
            raise Exception("send_batch_email failed for digest")
    except Exception as exc:
        raise self.retry(exc=exc)
 
    