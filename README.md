# CyArt DarkTrace — User Alerting / Webhook POD

## Status

🚧 **In Progress — Development / Integration**

The User Alerting Webhook POD is currently under active development.

This repository contains the current webhook delivery implementation and supporting development infrastructure.

---

## Purpose

The User Alerting / Webhook POD is responsible for webhook-based alert delivery within the CyArt DarkTrace platform.

The current implementation focuses on securely sending alert data to webhook endpoints using asynchronous delivery, HMAC-SHA256 signing, retry handling, and delivery tracking.

---

## Current Implementation

The following components have been implemented:

- FastAPI application
- Webhook delivery API
- Celery asynchronous task processing
- Redis as the Celery broker
- Redis-based delivery deduplication
- HMAC-SHA256 webhook signing
- Alert ID based idempotency
- High/Critical alert filtering
- Webhook delivery using HTTP
- Celery retry handling
- PostgreSQL 16 database
- SQLAlchemy database model
- Alembic database migrations
- Webhook delivery attempt records
- Local webhook test receiver
- Development alert test data

---

## Current Architecture

```text
                  FastAPI
                     |
                     v
              Celery + Redis
                     |
                     v
             HMAC-SHA256 Signer
                     |
                     v
             HTTP Webhook Delivery
                     |
                     v
             PostgreSQL Database
                     |
                     v
            Delivery Attempt Records
