"""DashAlert real-time alert backend.

Run:
    python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

Environment:
    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/alerts
    PG_CHANNEL=alerts_channel
    PG_POOL_MIN=2
    PG_POOL_MAX=10
    NOTIFY_SOURCE=postgres
    REDIS_URL=redis://localhost:6379/0
    REDIS_CHANNEL=alerts:events

Main endpoints:
    GET  /
    GET  /healthz
    GET  /alerts
    POST /alerts
    PATCH /alerts/{alert_id}/state
    POST /demo/replay
    GET  /stream
    WS   /ws/dashboard

The /api/* aliases are also provided for frontend applications that use an
/api prefix.
"""
import asyncio
import contextlib
import json
import logging
import os
import random
from contextlib import asynccontextmanager
from typing import Literal

import asyncpg
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import AwareDatetime, BaseModel, Field

from pg_listener import listen_postgres
from seed_data import HARDCODED_ALERTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("dashalert")

DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/alerts",
)
CHANNEL = os.getenv("PG_CHANNEL", "alerts_channel")
NOTIFY_SOURCE = os.getenv("NOTIFY_SOURCE", "postgres").lower()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_CHANNEL = os.getenv("REDIS_CHANNEL", "alerts:events")

POOL_MIN = max(1, int(os.getenv("PG_POOL_MIN", "2")))
POOL_MAX = max(POOL_MIN, int(os.getenv("PG_POOL_MAX", "10")))

WS_SEND_TIMEOUT = 5.0
SSE_QUEUE_SIZE = 100
SSE_HEARTBEAT = 15.0

Severity = Literal["critical", "high", "medium", "low", "informational"]
State = Literal["new", "acknowledged", "investigating", "resolved", "false_positive"]


class AlertIn(BaseModel):
    alert_id: str = Field(min_length=1, max_length=255)
    fingerprint: str = Field(min_length=1, max_length=255)
    severity: Severity
    confidence: float = Field(default=0.5, ge=0, le=1)
    state: State = "new"
    count: int = Field(default=1, ge=1)
    source_id: str | None = None
    watchlist_id: str | None = None
    source: str | None = None
    summary: str | None = None
    first_seen: AwareDatetime | None = None
    last_seen: AwareDatetime | None = None


class StateUpdate(BaseModel):
    state: State


UPSERT_SQL = """
INSERT INTO alerts (
    alert_id, fingerprint, source_id, watchlist_id, source, summary,
    severity, confidence, state, first_seen, last_seen, count
)
VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8::float8, $9,
    COALESCE($10::timestamptz, now()),
    COALESCE($11::timestamptz, $10::timestamptz, now()),
    $12
)
ON CONFLICT (fingerprint) DO UPDATE SET
    count      = alerts.count + EXCLUDED.count,
    confidence = GREATEST(alerts.confidence, EXCLUDED.confidence),
    first_seen = LEAST(alerts.first_seen, EXCLUDED.first_seen),
    last_seen  = GREATEST(alerts.last_seen, EXCLUDED.last_seen),
    state      = CASE
                    WHEN alerts.state = 'resolved' THEN 'new'
                    ELSE alerts.state
                 END
RETURNING alerts.*, (xmax = 0) AS inserted
"""


class Hub:
    def __init__(self) -> None:
        self.ws_clients: set[WebSocket] = set()
        self.sse_queues: set[asyncio.Queue[str]] = set()
        self.inbox: asyncio.Queue[str] = asyncio.Queue(maxsize=10_000)

    def push(self, payload: str) -> None:
        try:
            self.inbox.put_nowait(payload)
        except asyncio.QueueFull:
            log.error("Hub inbox is full; dropping event")

    def push_resync(self) -> None:
        self.push(json.dumps({"op": "RESYNC"}))

    async def run(self) -> None:
        while True:
            payload = await self.inbox.get()
            await self._fanout(payload)

    async def _fanout(self, payload: str) -> None:
        for queue in list(self.sse_queues):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(payload)

        clients = list(self.ws_clients)
        if clients:
            results = await asyncio.gather(
                *(self._send(ws, payload) for ws in clients),
                return_exceptions=False,
            )
            for ws, ok in zip(clients, results):
                if not ok:
                    self.ws_clients.discard(ws)

    @staticmethod
    async def _send(ws: WebSocket, payload: str) -> bool:
        try:
            await asyncio.wait_for(ws.send_text(payload), timeout=WS_SEND_TIMEOUT)
            return True
        except Exception as exc:
            log.info("Dropping WebSocket client: %s", type(exc).__name__)
            with contextlib.suppress(Exception):
                await ws.close(code=1011)
            return False

    async def close_all(self) -> None:
        for ws in list(self.ws_clients):
            with contextlib.suppress(Exception):
                await ws.close(code=1001)
        self.ws_clients.clear()


async def listen_redis(hub: Hub, stop: asyncio.Event) -> None:
    import redis.asyncio as aioredis

    backoff = 1.0
    while not stop.is_set():
        client = aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            health_check_interval=15,
        )
        try:
            async with client.pubsub() as pubsub:
                await pubsub.subscribe(REDIS_CHANNEL)
                hub.push_resync()
                backoff = 1.0

                async for message in pubsub.listen():
                    if message["type"] == "message":
                        hub.push(str(message["data"]))
        except asyncio.CancelledError:
            raise
        except (aioredis.RedisError, OSError) as exc:
            log.warning("Redis subscriber error: %s", exc)
        finally:
            with contextlib.suppress(Exception):
                await client.aclose()

        if not stop.is_set():
            await asyncio.sleep(backoff + random.random())
            backoff = min(backoff * 2, 30.0)


def _log_task_result(task: asyncio.Task) -> None:
    if not task.cancelled():
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        if exc:
            log.error("Background task %r crashed", task.get_name(), exc_info=exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = asyncio.Event()
    hub = Hub()

    log.info("Connecting to PostgreSQL...")
    pool = await asyncpg.create_pool(
        DSN,
        min_size=POOL_MIN,
        max_size=POOL_MAX,
        command_timeout=10,
        max_inactive_connection_lifetime=300,
    )
    await pool.fetchval("SELECT 1")
    log.info("PostgreSQL connection pool ready")

    app.state.pool = pool
    app.state.hub = hub

    tasks = [
        asyncio.create_task(hub.run(), name="hub-dispatcher")
    ]

    if NOTIFY_SOURCE == "redis":
        tasks.append(
            asyncio.create_task(
                listen_redis(hub, stop),
                name="redis-listener",
            )
        )
        log.info("Notification source: Redis")
    else:
        tasks.append(
            asyncio.create_task(
                listen_postgres(
                    DSN,
                    CHANNEL,
                    hub.push,
                    hub.push_resync,
                    stop,
                ),
                name="postgres-listener",
            )
        )
        log.info("Notification source: PostgreSQL LISTEN/NOTIFY")

    for task in tasks:
        task.add_done_callback(_log_task_result)

    try:
        yield
    finally:
        stop.set()

        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        await hub.close_all()
        await pool.close()
        log.info("DashAlert shutdown complete")


app = FastAPI(
    title="DashAlert API",
    description="Real-time alert dashboard API backed by PostgreSQL.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize_record(record: asyncpg.Record) -> dict:
    return dict(record)


async def upsert_alert(pool: asyncpg.Pool, alert: AlertIn) -> asyncpg.Record:
    return await pool.fetchrow(
        UPSERT_SQL,
        alert.alert_id,
        alert.fingerprint,
        alert.source_id,
        alert.watchlist_id,
        alert.source,
        alert.summary,
        alert.severity,
        alert.confidence,
        alert.state,
        alert.first_seen,
        alert.last_seen,
        alert.count,
    )


@app.get("/")
async def root() -> dict:
    return {
        "status": "ok",
        "message": "DashAlert API is running",
        "docs": "/docs",
        "health": "/healthz",
        "alerts": "/alerts",
        "websocket": "/ws/dashboard",
        "stream": "/stream",
    }


@app.get("/healthz")
async def healthz(request: Request) -> dict:
    await request.app.state.pool.fetchval("SELECT 1")
    return {
        "ok": True,
        "database": "connected",
        "ws_clients": len(request.app.state.hub.ws_clients),
        "sse_clients": len(request.app.state.hub.sse_queues),
    }


@app.get("/alerts")
@app.get("/api/alerts")
async def list_alerts(request: Request) -> list[dict]:
    rows = await request.app.state.pool.fetch(
        """
        SELECT *
        FROM alerts
        ORDER BY
            array_position(
                ARRAY['critical','high','medium','low','informational'],
                severity
            ),
            last_seen DESC
        """
    )
    return [serialize_record(row) for row in rows]


@app.get("/alerts/{alert_id}")
@app.get("/api/alerts/{alert_id}")
async def get_alert(alert_id: str, request: Request) -> dict:
    row = await request.app.state.pool.fetchrow(
        "SELECT * FROM alerts WHERE alert_id = $1",
        alert_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return serialize_record(row)


@app.post("/alerts", status_code=201)
@app.post("/api/alerts", status_code=201)
async def ingest_alert(alert: AlertIn, request: Request) -> dict:
    row = await upsert_alert(request.app.state.pool, alert)
    data = serialize_record(row)
    inserted = bool(data.pop("inserted"))
    return {"inserted": inserted, "alert": data}


@app.patch("/alerts/{alert_id}/state")
@app.patch("/api/alerts/{alert_id}/state")
async def set_state(
    alert_id: str,
    body: StateUpdate,
    request: Request,
) -> dict:
    row = await request.app.state.pool.fetchrow(
        """
        UPDATE alerts
        SET state = $2
        WHERE alert_id = $1
        RETURNING alert_id, state
        """,
        alert_id,
        body.state,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    return serialize_record(row)


async def _replay(pool: asyncpg.Pool, delay: float) -> None:
    for raw in HARDCODED_ALERTS:
        await upsert_alert(pool, AlertIn(**raw))
        await asyncio.sleep(delay)


@app.post("/demo/replay", status_code=202)
@app.post("/api/demo/replay", status_code=202)
async def demo_replay(
    request: Request,
    background: BackgroundTasks,
    delay: float = 2.0,
    reset: bool = False,
) -> dict:
    if delay < 0:
        raise HTTPException(status_code=400, detail="delay must be >= 0")

    pool = request.app.state.pool

    if reset:
        await pool.execute("TRUNCATE alerts")

    background.add_task(_replay, pool, delay)

    return {
        "queued": len(HARDCODED_ALERTS),
        "delay": delay,
        "reset": reset,
    }


@app.get("/stream")
async def stream(request: Request) -> StreamingResponse:
    hub: Hub = request.app.state.hub
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=SSE_QUEUE_SIZE)
    hub.sse_queues.add(queue)

    async def event_source():
        try:
            yield "retry: 3000\n\n"

            while not await request.is_disconnected():
                try:
                    payload = await asyncio.wait_for(
                        queue.get(),
                        timeout=SSE_HEARTBEAT,
                    )
                    yield f"event: alert\ndata: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            hub.sse_queues.discard(queue)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket) -> None:
    hub: Hub = ws.app.state.hub

    await ws.accept()
    hub.ws_clients.add(ws)

    try:
        await ws.send_json({
            "op": "HELLO",
            "clients": len(hub.ws_clients),
        })

        while True:
            message = await ws.receive_text()

            if message.strip().lower() == "ping":
                await ws.send_json({"op": "PONG"})

    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("WebSocket error")
    finally:
        hub.ws_clients.discard(ws)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
