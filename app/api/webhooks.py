import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.database import SessionLocal
from app.models import Alert, WebhookEndpoint

from celery_app import deliver_webhook
from delivery import redis_client


router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["webhooks"],
)

QUALIFYING_SEVERITIES = {"high", "critical"}

SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "informational": 4,
}


def dedupe_alerts(alerts):
    merged = {}

    for alert in alerts:
        fingerprint = alert.fingerprint

        if fingerprint not in merged:
            merged[fingerprint] = {
                "alert_id": alert.alert_id,
                "fingerprint": alert.fingerprint,
                "source_id": alert.source_id,
                "watchlist_id": alert.watchlist_id,
                "severity": alert.severity,
                "confidence": alert.confidence,
                "state": alert.state,
                "first_seen": alert.first_seen,
                "last_seen": alert.last_seen,
                "count": alert.count,
            }
            continue

        existing = merged[fingerprint]
        existing["count"] += alert.count

        if alert.confidence > existing["confidence"]:
            existing["confidence"] = alert.confidence

        if alert.last_seen > existing["last_seen"]:
            existing["last_seen"] = alert.last_seen

    deduped = list(merged.values())

    deduped.sort(
        key=lambda a: SEVERITY_RANK[a["severity"].lower()]
    )

    return deduped


def process_alerts(endpoint_id: str):
    db = SessionLocal()

    try:
        endpoint = (
            db.query(WebhookEndpoint)
            .filter(
                WebhookEndpoint.endpoint_id == endpoint_id
            )
            .first()
        )

        if endpoint is None:
            print(f"Endpoint not found: {endpoint_id}")
            return

        if not endpoint.enabled:
            print(f"Endpoint disabled: {endpoint_id}")
            return

        alerts = (
            db.query(Alert)
            .order_by(Alert.first_seen.asc())
            .all()
        )

        alerts = dedupe_alerts(alerts)

        for alert in alerts:
            severity = alert["severity"].lower()

            dedup_key = f"webhook:delivered:{alert['alert_id']}"

            if redis_client.exists(dedup_key):
                print(
                    f"Already delivered alert={alert['alert_id']}, "
                    f"skipping"
                )
                continue

            print(
                f"Checking alert={alert['alert_id']} "
                f"severity={severity}"
            )

            if severity not in QUALIFYING_SEVERITIES:
                print(
                    f"Skipping alert={alert['alert_id']} "
                    f"severity={severity}"
                )
                continue

            payload = json.dumps(
                {
                    "alert_id": alert["alert_id"],
                    "fingerprint": alert["fingerprint"],
                    "source_id": alert["source_id"],
                    "watchlist_id": alert["watchlist_id"],
                    "severity": alert["severity"],
                    "confidence": alert["confidence"],
                    "state": alert["state"],
                    "first_seen": alert["first_seen"],
                    "last_seen": alert["last_seen"],
                    "count": alert["count"],
                },
                default=str,
                separators=(",", ":"),
            ).encode("utf-8")

            task = deliver_webhook.delay(
                endpoint.url,
                payload,
                endpoint.hmac_secret,
                alert["alert_id"],
            )

            print(
                f"Queued alert={alert['alert_id']} "
                f"severity={severity} "
                f"task_id={task.id}"
            )

    finally:
        db.close()


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
                "endpoint_id": endpoint.endpoint_id,
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

