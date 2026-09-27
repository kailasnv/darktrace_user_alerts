import json
import logging
import os
from datetime import datetime, timezone

LOG_FILE = os.getenv("AUDIT_LOG_FILE", "audit_log.jsonl")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def write_audit_event(event: dict) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event,
    }

    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    logging.info("Audit event written: %s", record)
