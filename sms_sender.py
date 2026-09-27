import os
from twilio.rest import Client


def send_sms(message: str, to_number: str | None = None) -> dict:
    """
    Send an SMS through Twilio.

    Required environment variables:
      TWILIO_ACCOUNT_SID
      TWILIO_AUTH_TOKEN
      TWILIO_FROM_NUMBER
      ALERT_TO_NUMBER (used when to_number is not supplied)
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    destination = to_number or os.getenv("ALERT_TO_NUMBER")

    missing = []
    if not account_sid:
        missing.append("TWILIO_ACCOUNT_SID")
    if not auth_token:
        missing.append("TWILIO_AUTH_TOKEN")
    if not from_number:
        missing.append("TWILIO_FROM_NUMBER")
    if not destination:
        missing.append("ALERT_TO_NUMBER or phone_number")

    if missing:
        raise RuntimeError(
            "Missing SMS configuration: " + ", ".join(missing)
        )

    client = Client(account_sid, auth_token)

    msg = client.messages.create(
        body=message,
        from_=from_number,
        to=destination,
    )

    return {
        "provider": "twilio",
        "status": msg.status,
        "message_sid": msg.sid,
        "to": destination,
    }
