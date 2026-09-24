from celery_app import celery_app
from email_sender import send_email, send_batch_email


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_immediate_email_task(self, alert: dict):
    try:
        send_email(alert)
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_batched_medium_task(self, alerts: list):
    try:
        send_batch_email(alerts, title="Medium Severity Alerts (batched)")
    except Exception as exc:
        raise self.retry(exc=exc)
 

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_daily_digest_task(self, alerts: list):
    try:
        send_batch_email(alerts, title="Daily Digest -- Low/Informational Alerts")
    except Exception as exc:
        raise self.retry(exc=exc)
    