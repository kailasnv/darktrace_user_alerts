import os

from dotenv import load_dotenv
from elasticsearch import Elasticsearch


load_dotenv()


class ElasticSIEMClient:
    """Client responsible for sending security events to Elastic SIEM."""

    def __init__(self):
        self.elastic_url = os.getenv("ELASTIC_URL")
        self.api_key = os.getenv("ELASTIC_API_KEY")
        self.index_name = "dark-web-alerts"

        # Deduplication window: 24 hours
        self.dedup_window = "24h"

        if not self.elastic_url:
            raise ValueError("ELASTIC_URL is not configured")

        if not self.api_key:
            raise ValueError("ELASTIC_API_KEY is not configured")

        self.client = Elasticsearch(
            hosts=[self.elastic_url],
            api_key=self.api_key,
            request_timeout=10,
        )

    def _is_duplicate(self, event):
        """Check whether the same event was already indexed recently."""

        fingerprint = (
            event
            .get("labels", {})
            .get("dedup_fingerprint")
        )

        if not fingerprint:
            return False

        response = self.client.search(
            index=self.index_name,
            query={
                "bool": {
                    "must": [
                        {
                            "term": {
                                "labels.dedup_fingerprint": fingerprint
                            }
                        }
                    ],
                    "filter": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{self.dedup_window}"
                                }
                            }
                        }
                    ],
                }
            },
            size=1,
        )

        return response["hits"]["total"]["value"] > 0

    def send_event(self, event):
        """Send a security event unless it is a recent duplicate."""

        if self._is_duplicate(event):
            return {
                "status": "duplicate",
                "message": "Duplicate event skipped",
            }

        response = self.client.index(
            index=self.index_name,
            document=event,
        )

        return {
            "status": "indexed",
            "index": response["_index"],
            "id": response["_id"],
        }
