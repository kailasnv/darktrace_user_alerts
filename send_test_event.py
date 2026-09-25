from dotenv import load_dotenv
import os
from datetime import datetime, timezone
from elasticsearch import Elasticsearch

load_dotenv()

client = Elasticsearch(
    hosts=[os.getenv("ELASTIC_URL")],
    api_key=os.getenv("ELASTIC_API_KEY"),
    request_timeout=10
)

event = {
    "@timestamp": datetime.now(timezone.utc).isoformat(),
    "event": {
        "kind": "alert",
        "category": ["threat"],
        "type": ["credential_exposure"],
        "severity": 4,
    },
    "message": "Dark web credential exposure detected",
    "rule": {
        "name": "Dark Web Credential Exposure"
    },
    "threat": {
        "indicator": {
            "type": "email-addr",
            "name": "test-user@example.com"
        }
    },
    "source": {
        "domain": "example-darkweb-source.test"
    },
    "labels": {
        "alert_severity": "High",
        "affected_asset": "example.com",
        "alert_source": "dark_web_monitoring"
    }
}

response = client.index(
    index="dark-web-alerts",
    document=event
)

print("EVENT SENT SUCCESSFULLY")
print("Index:", response["_index"])
print("Document ID:", response["_id"])
