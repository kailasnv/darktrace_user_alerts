from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import ValidationError

from .db import get_session, init_db , record_alert_audit
from .engine import evaluate_alerts, get_alert_by_id, persist_alert
from .hitl import HitlPolicyError, approve_stix_export, reject_stix_export
from .models import EnrichedFinding, StixExportStatus
from .stix.export import StixExportError, alert_to_finding_projection, export_alert_to_taxii

_INGEST_API_KEY = os.environ.get("ALERT_ENGINE_INGEST_API_KEY", "")


def verify_api_key(x_api_key: str = Header(default="")) -> None:
    if not _INGEST_API_KEY:
        return
    if x_api_key != _INGEST_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="Alert Logic & STIX/TAXII Export Service", version="1.0.0", lifespan=lifespan)


@app.post("/v1/findings", dependencies=[Depends(verify_api_key)])
def ingest_finding(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        finding = EnrichedFinding.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())

    with get_session() as session:
        alert = evaluate_alerts(finding, session=session)
        alert_payload = alert.to_channel_payload()

        export_result = None
        if alert.suppressed:
            export_result = None
        elif alert.stix_export_status == StixExportStatus.APPROVED:
            try:
                result = export_alert_to_taxii(alert, finding, session=session)
                export_result = {"success": result.success, "status_code": result.status_code}
                alert_payload = alert.to_channel_payload()
            except StixExportError as exc:
                export_result = {"success": False, "error": str(exc)}
        elif alert.stix_export_status == StixExportStatus.PENDING_APPROVAL:
            export_result = {"success": False, "pending_approval": True}

    return {"alert": alert_payload, "stix_export": export_result}


@app.get("/v1/alerts/{alert_id}", dependencies=[Depends(verify_api_key)])
def get_alert(alert_id: str) -> Dict[str, Any]:
    with get_session() as session:
        alert = get_alert_by_id(session, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        return alert.to_channel_payload()


@app.post("/v1/alerts/{alert_id}/stix-export/approve", dependencies=[Depends(verify_api_key)])
def approve_export(
    alert_id: str,
    x_actor_id: str = Header(..., alias="X-Actor-ID"),
) -> Dict[str, Any]:

    with get_session() as session:
        alert = get_alert_by_id(session, alert_id)

        if alert is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found",
            )

        try:
            approve_stix_export(alert)

            record_alert_audit(
                session=session,
                alert_id=alert.alert_id,
                action="STIX_EXPORT_APPROVED",
                actor_id=x_actor_id,
            )

        except HitlPolicyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            )

        persist_alert(session, alert)

        finding = alert_to_finding_projection(alert)

        try:
            result = export_alert_to_taxii(
                alert,
                finding,
                session=session,
            )

            export_result = {
                "success": result.success,
                "status_code": result.status_code,
            }

        except StixExportError as exc:
            export_result = {
                "success": False,
                "error": str(exc),
            }

    return {
        "alert": alert.to_channel_payload(),
        "stix_export": export_result,
    }


@app.post("/v1/alerts/{alert_id}/stix-export/reject", dependencies=[Depends(verify_api_key)])
def reject_export(
    alert_id: str,
    x_actor_id: str = Header(..., alias="X-Actor-ID"),
) -> Dict[str, Any]:

    with get_session() as session:
        alert = get_alert_by_id(session, alert_id)

        if alert is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found",
            )

        try:
            reject_stix_export(alert)

            record_alert_audit(
                session=session,
                alert_id=alert.alert_id,
                action="STIX_EXPORT_REJECTED",
                actor_id=x_actor_id,
            )

        except HitlPolicyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            )

        persist_alert(session, alert)

    return {
        "alert": alert.to_channel_payload(),
    }
@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}
