from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from .config import CELERY_CONFIG
from .db import get_session
from .escalation import scan_and_escalate

celery_app = Celery(
    "alert_engine",
    broker=CELERY_CONFIG.broker_url,
    backend=CELERY_CONFIG.result_backend,
)

celery_app.conf.beat_schedule = {
    "scan-and-escalate-every-minute": {
        "task": "alert_engine.celery_app.run_escalation_scan",
        "schedule": crontab(minute="*/1"),
    }
}
celery_app.conf.timezone = "UTC"


@celery_app.task(name="alert_engine.celery_app.run_escalation_scan")
def run_escalation_scan() -> int:
    with get_session() as session:
        escalated = scan_and_escalate(session)
    return len(escalated)
