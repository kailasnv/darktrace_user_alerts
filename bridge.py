"""Optional PostgreSQL LISTEN -> Redis PUBLISH bridge.

This file is NOT required for the normal single-node FastAPI setup.

Run it only when:
    1. Redis is running.
    2. NOTIFY_SOURCE=redis is used by the API.
    3. Exactly one active bridge is running.

On Windows, signal handling uses signal.signal instead of
asyncio.AbstractEventLoop.add_signal_handler.
"""
import asyncio
import contextlib
import json
import logging
import os
import signal

import redis.asyncio as aioredis

from pg_listener import listen_postgres

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("bridge")

DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/alerts",
)
CHANNEL = os.getenv("PG_CHANNEL", "alerts_channel")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_CHANNEL = os.getenv("REDIS_CHANNEL", "alerts:events")


async def publisher(
    queue: asyncio.Queue[str],
    redis_client: aioredis.Redis,
) -> None:
    while True:
        payload = await queue.get()

        while True:
            try:
                await redis_client.publish(REDIS_CHANNEL, payload)
                break
            except (aioredis.RedisError, OSError) as exc:
                log.warning("Redis publish failed: %s; retrying", exc)
                await asyncio.sleep(1)


async def main() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        loop.call_soon_threadsafe(stop.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, lambda _signum, _frame: request_stop())
        except (ValueError, OSError):
            pass

    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=10_000)

    def enqueue(payload: str) -> None:
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            log.error("Bridge queue full; dropping event")

    redis_client = aioredis.from_url(
        REDIS_URL,
        decode_responses=True,
        health_check_interval=15,
    )

    publisher_task = asyncio.create_task(
        publisher(queue, redis_client),
        name="redis-publisher",
    )

    listener_task = asyncio.create_task(
        listen_postgres(
            DSN,
            CHANNEL,
            enqueue,
            lambda: enqueue(json.dumps({"op": "RESYNC"})),
            stop,
        ),
        name="postgres-listener",
    )

    try:
        await stop.wait()
    finally:
        for task in (listener_task, publisher_task):
            task.cancel()

        await asyncio.gather(
            listener_task,
            publisher_task,
            return_exceptions=True,
        )

        with contextlib.suppress(Exception):
            await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
