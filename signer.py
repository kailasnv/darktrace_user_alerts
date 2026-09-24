import hashlib
import hmac


def generate_signature(timestamp: str, body: bytes, secret: str) -> str:
    """
    Generate the CyArt webhook HMAC-SHA256 signature.

    The signature is calculated over:
        timestamp + body

    using the endpoint secret.
    """
    message = timestamp.encode("utf-8") + body
    return hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


SIGNATURE_HEADER = "X-CyArt-Signature"


from datetime import datetime, timezone


def validate_timestamp(timestamp: str, max_age_seconds: int = 300) -> bool:
    received_at = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    now = datetime.now(timezone.utc)

    return abs((now - received_at).total_seconds()) <= max_age_seconds
