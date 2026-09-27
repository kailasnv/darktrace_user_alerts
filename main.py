from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional
from tasks import send_alert_task
from hardcoded_alerts import HARDCODED_ALERTS

app = FastAPI(
    title="DarkTrace SMS / Push Alerting",
    description="Demo alerting API for DarkTrace-style threat intelligence findings.",
    version="1.0.0",
)


class AlertRequest(BaseModel):
    alert_id: str
    fingerprint: str
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    summary: str
    channel: Literal["sms", "push", "both"] = "both"
    phone_number: Optional[str] = None
    fcm_token: Optional[str] = None


@app.get("/")
def root():
    return {
        "service": "DarkTrace SMS / Push Alerting",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/alerts")
def get_alerts():
    return {"count": len(HARDCODED_ALERTS), "alerts": HARDCODED_ALERTS}


@app.post("/alerts/send")
def send_alert(alert: AlertRequest):
    # For a demo, the API queues the notification instead of blocking
    # while external providers send SMS/push messages.
    payload = alert.model_dump()
    task = send_alert_task.delay(payload)

    return {
        "status": "queued",
        "task_id": task.id,
        "alert_id": alert.alert_id,
        "channels": alert.channel,
    }


@app.post("/alerts/demo/{alert_id}")
def send_demo_alert(alert_id: str, channel: Literal["sms", "push", "both"] = "both"):
    alert = next(
        (item for item in HARDCODED_ALERTS if item["alert_id"] == alert_id),
        None,
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    payload = {
        **alert,
        "channel": channel,
    }

    task = send_alert_task.delay(payload)

    return {
        "status": "queued",
        "task_id": task.id,
        "alert_id": alert_id,
        "channels": channel,
    }
