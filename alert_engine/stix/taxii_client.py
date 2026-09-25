from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import TaxiiConfig


TAXII_MEDIA_TYPE = "application/taxii+json;version=2.1"
STIX_MEDIA_TYPE = "application/stix+json;version=2.1"


@dataclass
class TaxiiPublishResult:
    success: bool
    status_code: Optional[int]
    response_body: Optional[Dict[str, Any]]
    error_message: Optional[str] = None


class TaxiiClient:
    def __init__(self, config: TaxiiConfig) -> None:
        if not config.api_root or not config.collection_id:
            raise ValueError(
                "TAXII api_root and collection_id must be configured"
            )

        self._config = config

        # TAXII must use HTTPS
        parsed = urlparse(self._config.api_root)
        if parsed.scheme != "https":
            raise ValueError("TAXII api_root must use HTTPS")

        self._session = requests.Session()

        if config.username:
            self._session.auth = (config.username, config.password)

        retry = Retry(
            total=config.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
        )

        adapter = HTTPAdapter(max_retries=retry)

        self._session.mount("https://", adapter)

    @property
    def _objects_url(self) -> str:
        root = self._config.api_root.rstrip("/")

        return (
            f"{root}/collections/"
            f"{self._config.collection_id}/objects/"
        )

    def publish_bundle(self, bundle_json: str) -> TaxiiPublishResult:
        headers = {
            "Content-Type": TAXII_MEDIA_TYPE,
            "Accept": TAXII_MEDIA_TYPE,
        }

        try:
            response = self._session.post(
                self._objects_url,
                data=bundle_json,
                headers=headers,
                timeout=self._config.timeout_seconds,
                verify=self._config.verify_tls,
            )

        except requests.RequestException as exc:
            return TaxiiPublishResult(
                success=False,
                status_code=None,
                response_body=None,
                error_message=str(exc),
            )

        if response.status_code not in (200, 201, 202):
            return TaxiiPublishResult(
                success=False,
                status_code=response.status_code,
                response_body=_safe_json(response),
                error_message=(
                    f"TAXII server returned status "
                    f"{response.status_code}"
                ),
            )

        return TaxiiPublishResult(
            success=True,
            status_code=response.status_code,
            response_body=_safe_json(response),
        )


def _safe_json(
    response: requests.Response,
) -> Optional[Dict[str, Any]]:
    try:
        return response.json()
    except ValueError:
        return None