import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.database import SessionLocal
from app.models import WebhookEndpoint

from celery_app import deliver_webhook


router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["webhooks"],
)


class WebhookEndpointRequest(BaseModel):
    endpoint_id: str
    name: str
    url: str
    endpoint_type: str = "webhook"


@router.post("/endpoints")
def register_endpoint(request: WebhookEndpointRequest):
    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)

        endpoint = WebhookEndpoint(
            endpoint_id=request.endpoint_id,
            name=request.name,
            endpoint_type=request.endpoint_type,
            url=request.url,
            hmac_secret=secrets.token_hex(32),
            enabled=True,
            created_at=now,
            updated_at=now,
        )

        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)

        return {
            "status": "registered",
            "endpoint_id": endpoint.endpoint_id,
            "name": endpoint.name,
            "endpoint_type": endpoint.endpoint_type,
            "url": endpoint.url,
            "enabled": endpoint.enabled,
            "created_at": endpoint.created_at,
        }

    finally:
        db.close()


class WebhookRequest(BaseModel):
    endpoint_id: str
    alert: dict


@router.post("/deliver")
def deliver(request: WebhookRequest):
    alert_id = request.alert["alert_id"]
    severity = request.alert["severity"].lower()

    if severity not in {"high", "critical"}:
        return {
            "status": "ignored",
            "reason": "Webhook delivery is only for High and Critical alerts",
            "alert_id": alert_id,
            "severity": request.alert["severity"],
        }

    db = SessionLocal()

    try:
        endpoint = (
            db.query(WebhookEndpoint)
            .filter(
                WebhookEndpoint.endpoint_id == request.endpoint_id
            )
            .first()
        )

        if endpoint is None:
            return {
                "status": "error",
                "reason": "Webhook endpoint not found",
                "endpoint_id": request.endpoint_id,
            }

        if not endpoint.enabled:
            return {
                "status": "error",
                "reason": "Webhook endpoint is disabled",
                "endpoint_id": request.endpoint_id,
            }

        task = deliver_webhook.delay(
            endpoint.url,
            json.dumps(
                request.alert,
                default=str,
                separators=(",", ":"),
            ).encode("utf-8"),
            endpoint.hmac_secret,
            alert_id,
        )

        return {
            "status": "queued",
            "task_id": task.id,
            "alert_id": alert_id,
            "endpoint_id": endpoint.endpoint_id,
            "severity": request.alert["severity"],
        }

    finally:
        db.close()
