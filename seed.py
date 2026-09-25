"""Seed PostgreSQL with the sample alerts.

Run:
    python seed.py

The script truncates the alerts table first and then inserts the sample data.
Duplicate fingerprints are merged by the same upsert logic used by the API.
"""
import asyncio
import os

import asyncpg

from main import AlertIn, upsert_alert
from seed_data import ALERTS

DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/alerts",
)


async def main() -> None:
    print("Connecting to PostgreSQL...")

    pool = await asyncpg.create_pool(
        DSN,
        min_size=1,
        max_size=2,
        command_timeout=10,
    )

    try:
        await pool.fetchval("SELECT 1")
        print("Connected to PostgreSQL.")

        await pool.execute("TRUNCATE TABLE alerts")
        print(f"Loading {len(ALERTS)} alerts...")

        for raw in ALERTS:
            row = await upsert_alert(pool, AlertIn(**raw))

            print(
                f"{'inserted' if row['inserted'] else 'merged  '} "
                f"{raw['alert_id']} -> {row['alert_id']} "
                f"(count={row['count']})"
            )

        print("Seed completed successfully.")

    except asyncpg.PostgresError as exc:
        print(f"PostgreSQL error: {exc}")
        raise

    finally:
        await pool.close()
        print("Database connection closed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Seed failed: {exc}")
