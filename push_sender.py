import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging


_app = None


def _get_firebase_app():
    global _app

    if _app is not None:
        return _app

    credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not credentials_path:
        raise RuntimeError(
            "FIREBASE_CREDENTIALS_PATH is not configured."
        )

    path = Path(credentials_path)
    if not path.exists():
        raise RuntimeError(
            f"Firebase credentials file not found: {path}"
        )

    if not firebase_admin._apps:
        _app = firebase_admin.initialize_app(
            credentials.Certificate(str(path))
        )
    else:
        _app = firebase_admin.get_app()

    return _app


def send_push(
    title: str,
    body: str,
    fcm_token: str | None = None,
) -> dict:
    """
    Send a Firebase Cloud Messaging notification to one device.

    Required:
      FIREBASE_CREDENTIALS_PATH
      FCM_DEVICE_TOKEN (used when fcm_token is not supplied)
    """
    token = fcm_token or os.getenv("FCM_DEVICE_TOKEN")

    if not token:
        raise RuntimeError(
            "No FCM token supplied. Set FCM_DEVICE_TOKEN or pass fcm_token."
        )

    _get_firebase_app()

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
    )

    message_id = messaging.send(message)

    return {
        "provider": "firebase_fcm",
        "status": "sent",
        "message_id": message_id,
    }
