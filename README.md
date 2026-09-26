# CyArt DarkTrace — User Alerting / Webhook POD

## Status

**In Progress — Development / Integration**

The User Alerting / Webhook POD is under active development.

The current implementation provides automatic alert processing and webhook delivery using a temporary SQLite database, Celery, Redis, HMAC-SHA256 signing, retry handling, and delivery tracking.

---

## Purpose

The User Alerting / Webhook POD is responsible for webhook-based alert delivery within the CyArt DarkTrace platform.

The current implementation focuses on:

* Fetching alerts from the temporary alert database
* Deduplicating alerts by fingerprint
* Merging duplicate alerts
* Updating duplicate alert counts and confidence
* Sorting alerts by severity
* Sending only High and Critical alerts to webhook endpoints
* Asynchronous webhook delivery through Celery
* HMAC-SHA256 request signing
* Idempotent delivery using alert IDs
* Redis-based delivery deduplication
* Retry handling
* Delivery attempt tracking through the audit record

---

## Current Implementation

The following components are implemented:

### Webhook Processing

* FastAPI webhook API
* Webhook endpoint registration
* Temporary SQLite endpoint registry
* Temporary SQLite alerts table
* Automatic alert scanning using Celery Beat
* Alert processing every 10 seconds
* Fingerprint-based alert deduplication
* Duplicate alert merging
* Duplicate `count` aggregation
* Confidence update using the higher confidence value
* Latest `last_seen` value retained
* Severity-based alert ordering:

  * Critical
  * High
  * Medium
  * Low
  * Informational
* High/Critical webhook filtering



### Development / Testing

* Local webhook test receiver
* Development alert test data
* SQLite database for temporary development use
* Alembic migration for the alerts table
* Automatic end-to-end alert delivery testing

---

## Current Alert Processing Flow

```text
                    SQLite Alerts
                         |
                         v
                 Celery Beat
                Every 10 Seconds
                         |
                         v
                  Fetch Alerts
                         |
                         v
             Fingerprint Deduplication
                         |
                         v
                Merge Duplicates
                         |
              +----------+----------+
              |                     |
              v                     v
        Increase count       Update confidence
              |                     |
              +----------+----------+
                         |
                         v
                 Sort by Severity
                         |
              Critical → High → Medium
                    → Low → Informational
                         |
                         v
                Check Redis Delivery
                         |
              +----------+----------+
              |                     |
          Already sent          Not sent
              |                     |
              v                     v
            Skip              Check Severity
                                  |
                         +--------+--------+
                         |                 |
                    High/Critical      Other
                         |                 |
                         v                 v
                   Celery Task           Skip
                         |
                         v
                  HMAC-SHA256
                    Signing
                         |
                         v
                 HTTP Webhook
                    Delivery
                         |
                         v
                Delivery Result
                         |
                  +------+------+
                  |             |
                Success       Failure
                  |             |
                  v             v
               Redis        Celery Retry
               Dedup        + Audit Record
                  |
                  v
             Audit Record
```

---

#


## Project Structure

```text
darktrace_user_alerts/
│
├── app/
│   ├── api/
│   │   └── webhooks.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── alert.py
│   │   └── webhook_endpoint.py
│   │
│   └── database.py
│
├── alembic/
│   ├── env.py
│   └── versions/
│
├── celery_app.py
├── delivery.py
├── signer.py
├── test_server.py
├── requirements.txt
└── README.md
```

---

## Current End-to-End Flow

A new alert can be inserted into the temporary SQLite alerts table.

The system automatically detects it during the next Celery Beat scan.

For example:

```text
New Critical Alert
        ↓
SQLite
        ↓
Celery Beat
        ↓
Fingerprint Deduplication
        ↓
Severity Check
        ↓
Celery Delivery Task
        ↓
HMAC-SHA256
        ↓
Webhook Endpoint
        ↓
HTTP 200
        ↓
Redis Delivery Record
        ↓
Audit Event
```

For Medium, Low, or Informational alerts:

```text
New Alert
   ↓
SQLite
   ↓
Celery Beat
   ↓
Alert Processing
   ↓
Severity Check
   ↓
Skipped
```

---

## Future Integration

The following items are planned for later team integration:

* Integration with the main PostgreSQL 16 environment
* Integration with the project's shared Redis/Celery configuration
* Integration with the main alerting engine
* Production secret/vault configuration
* Final endpoint routing/integration with the complete alerting system
* Production deployment configuration

---

## Development Notes

The current SQLite, Redis, Celery, and local webhook receiver configuration is intended for development and integration testing.

Production configuration will follow the final CyArt DarkTrace deployment architecture.



