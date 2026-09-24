from fastapi import APIRouter
from pydantic import BaseModel

from celery_app import deliver_webhook


router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["webhooks"],
)


class WebhookRequest(BaseModel):
    url: str
    secret: str
    alert: dict


@router.post("/deliver")
def deliver(request: WebhookRequest):
    alert_id = request.alert["alert_id"]
    severity = request.alert["severity"].lower()

    # Webhook delivery is only for High and Critical alerts.
    if severity not in {"high", "critical"}:
        return {
            "status": "ignored",
            "reason": "Webhook delivery is only for High and Critical alerts",
            "alert_id": alert_id,
            "severity": request.alert["severity"],
        }

    task = deliver_webhook.delay(
        request.url,
        __import__("json").dumps(
            request.alert,
            default=str,
            separators=(",", ":"),
        ).encode("utf-8"),
        request.secret,
        alert_id,
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "alert_id": alert_id,
        "severity": request.alert["severity"],
    }
