from celery import Celery

from delivery import send_webhook

# TODO (team integration):
# Replace local Redis URL with the shared project Redis configuration.

app = Celery(
    "webhook",
    broker="redis://127.0.0.1:6379/0",
    backend="redis://127.0.0.1:6379/0",
)


@app.task(bind=True, max_retries=3)
def deliver_webhook(
    self,
    url: str,
    payload: bytes,
    secret: str,
    alert_id: str,
) -> int:
    # Celery retry count starts at 0, so convert it to a human-readable
    # delivery attempt number starting at 1.
    attempt_number = self.request.retries + 1

    print(
        f"Webhook delivery attempt={attempt_number} "
        f"alert_id={alert_id}"
    )

    try:
        status_code = send_webhook(
            url=url,
            payload=payload,
            secret=secret,
            alert_id=alert_id,
            attempt_number=attempt_number,
        )

        if not 200 <= status_code < 300:
            raise RuntimeError(
                f"Webhook delivery failed with status {status_code}"
            )

        print(
            f"Webhook delivery succeeded "
            f"alert_id={alert_id} "
            f"attempt={attempt_number}"
        )

        return status_code

    except Exception as exc:
        retry_count = self.request.retries

        print(
            f"Webhook delivery failed "
            f"alert_id={alert_id} "
            f"attempt={attempt_number} "
            f"retry_count={retry_count} "
            f"error={exc}"
        )

        raise self.retry(
            exc=exc,
            countdown=2 ** retry_count,
        )
