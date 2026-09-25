import hashlib
import json
import time
import uuid
from datetime import datetime, timezone

import httpx
import redis

from app.database import SessionLocal
from app.models import AuditEvent
from signer import generate_signature, SIGNATURE_HEADER


redis_client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=True,
)


def alert_to_payload(alert: dict) -> bytes:
    payload = json.dumps(
        alert,
        default=str,
        separators=(",", ":"),
    )

    return payload.encode("utf-8")


def record_delivery(
    alert_id: str,
    url: str,
    attempt_number: int,
    status_code: int | None,
    status: str,
    error_message: str | None = None,
) -> None:
    db = SessionLocal()

    try:
        previous_event = (
            db.query(AuditEvent)
            .order_by(AuditEvent.seq.desc())
            .first()
        )

        prev_hash = (
            previous_event.entry_hash
            if previous_event
            else "0" * 64
        )

        event_id = str(uuid.uuid4())
        occurred_at = datetime.now(timezone.utc)

        details = {
            "url": url,
            "attempt_number": attempt_number,
            "status_code": status_code,
            "status": status,
        }

        if error_message is not None:
            details["error_message"] = error_message

        hash_input = (
            f"{prev_hash}|"
            f"{event_id}|"
            f"system|"
            f"webhook_delivery|"
            f"{alert_id}|"
            f"{json.dumps(details, sort_keys=True, separators=(',', ':'))}|"
            f"{occurred_at.isoformat()}"
        )

        entry_hash = hashlib.sha256(
            hash_input.encode("utf-8")
        ).hexdigest()

        audit_event = AuditEvent(
            event_id=event_id,
            actor_usr="system",
            action="webhook_delivery",
            object_type="alert",
            object_id=alert_id,
            details=details,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            occurred_at=occurred_at,
        )

        db.add(audit_event)
        db.commit()

    finally:
        db.close()


def send_webhook(
    url: str,
    payload: bytes,
    secret: str,
    alert_id: str,
    attempt_number: int = 1,
) -> int:
    dedup_key = f"webhook:delivered:{alert_id}"

    if redis_client.exists(dedup_key):
        print(f"Duplicate alert skipped: {alert_id}")
        return 200

    timestamp = str(int(time.time()))

    signature = generate_signature(
        timestamp,
        payload,
        secret,
    )

    headers = {
        "Content-Type": "application/json",
        SIGNATURE_HEADER: signature,
        "Idempotency-Key": alert_id,
    }

    try:
        response = httpx.post(
            url,
            content=payload,
            headers=headers,
        )

    except Exception as exc:
        record_delivery(
            alert_id=alert_id,
            url=url,
            attempt_number=attempt_number,
            status_code=None,
            status="failure",
            error_message=str(exc),
        )

        raise

    if 200 <= response.status_code < 300:
        redis_client.set(dedup_key, "1")

        record_delivery(
            alert_id=alert_id,
            url=url,
            attempt_number=attempt_number,
            status_code=response.status_code,
            status="success",
        )

    else:
        record_delivery(
            alert_id=alert_id,
            url=url,
            attempt_number=attempt_number,
            status_code=response.status_code,
            status="failure",
            error_message=f"HTTP {response.status_code}",
        )

    return response.status_code
