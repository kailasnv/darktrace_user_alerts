from celery_app import celery_app
from email_sender import send_email, send_batch_email


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, rate_limit="20/m")
def send_immediate_email_task(self, alert: dict):
    #rate_limit="20/m" (~1 every 3s) keeps this under Mailtrap's free-tier per-second cap, even when several critical/high alerts fire at once across multiple worker processes.

    success = send_email(alert)
    if not success:
        # send_email() catches its own exceptions and returns False --
        raise self.retry(exc=Exception(f"send_email failed for {alert['alert_id']}"))


 
@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_batched_medium_task(self, alerts: list):
    # no ratelimiting needed here
    success = send_batch_email(alerts, title="Medium Severity Alerts (batched)")
    if not success:
        raise self.retry(exc=Exception("send_batch_email failed for medium batch"))
 
 
@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_daily_digest_task(self, alerts: list):
    success = send_batch_email(alerts, title="Daily Digest -- Low/Informational Alerts")
    if not success:
        raise self.retry(exc=Exception("send_batch_email failed for digest"))
 
    