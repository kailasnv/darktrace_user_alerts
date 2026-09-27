from celery_app import celery_app
from notification_service import send_notifications


@celery_app.task(
    name="tasks.send_alert_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_alert_task(alert: dict):
    """
    Celery background task for SMS / Push alert delivery.
    """
    return send_notifications(alert)
