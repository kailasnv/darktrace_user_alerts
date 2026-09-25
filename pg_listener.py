"""Reliable PostgreSQL LISTEN/NOTIFY listener used by DashAlert."""
import asyncio
import logging
import random
from collections.abc import Callable

import asyncpg

log = logging.getLogger("pg_listener")


async def listen_postgres(
    dsn: str,
    channel: str,
    on_payload: Callable[[str], None],
    on_reconnect: Callable[[], None],
    stop: asyncio.Event,
    health_interval: float = 15.0,
) -> None:
    backoff = 1.0
    first_connect = True

    while not stop.is_set():
        conn: asyncpg.Connection | None = None

        try:
            conn = await asyncpg.connect(dsn, timeout=10)

            def callback(
                _connection: asyncpg.Connection,
                _pid: int,
                _channel: str,
                payload: str,
            ) -> None:
                on_payload(payload)

            await conn.add_listener(channel, callback)
            log.info("PostgreSQL LISTEN active on %r", channel)

            if not first_connect:
                on_reconnect()

            first_connect = False
            backoff = 1.0

            while not stop.is_set():
                try:
                    await asyncio.wait_for(
                        stop.wait(),
                        timeout=health_interval,
                    )
                except asyncio.TimeoutError:
                    await conn.fetchval("SELECT 1", timeout=5)

        except asyncio.CancelledError:
            raise
        except (
            OSError,
            asyncpg.PostgresError,
            asyncpg.InterfaceError,
            asyncio.TimeoutError,
        ) as exc:
            log.warning(
                "PostgreSQL listener connection lost: %s: %s",
                type(exc).__name__,
                exc,
            )
        finally:
            if conn is not None and not conn.is_closed():
                try:
                    await asyncio.wait_for(conn.close(), timeout=5)
                except Exception:
                    conn.terminate()

        if not stop.is_set():
            delay = backoff + random.random()
            log.info("PostgreSQL listener reconnecting in %.1fs", delay)
            await asyncio.sleep(delay)
            backoff = min(backoff * 2, 30.0)
