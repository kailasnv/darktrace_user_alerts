# DarkTrace SMS / Push Alerting

A GitHub-ready Proof of Concept (PoC) for sending DarkTrace-style threat intelligence alerts through:

- SMS using Twilio
- Push notifications using Firebase Cloud Messaging (FCM)
- Celery + Redis for background delivery
- FastAPI for a simple REST API
- Audit logging for notification events
- Hardcoded alerts for an easy demo

> This project is intended for authorized security monitoring and defensive alerting. Use only phone numbers, devices, accounts, and data that you are authorized to use.

---

## Architecture

```text
             Dark Web Finding
                    |
                    v
               Risk Score
                    |
                    v
              Alert Rule
                 Engine
                    |
                    v
           FastAPI /alerts/send
                    |
                    v
              Celery Task
                    |
             +------+------+
             |             |
             v             v
           Twilio         FCM
             |             |
             v             v
            SMS           Push
             \             /
              \           /
               v         v
                  User
```

---

## Project Structure

```text
darktrace_sms_push_alerting/
│
├── main.py
├── sms_sender.py
├── push_sender.py
├── notification_service.py
├── tasks.py
├── celery_app.py
├── hardcoded_alerts.py
├── audit_log.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd darktrace_sms_push_alerting
```

---

## 2. Create a virtual environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux / Kali

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure environment variables

Copy:

```text
.env.example
```

to:

```text
.env
```

Then fill in your real credentials.

Never commit `.env` to GitHub.

---

# SMS Setup — Twilio

Create a Twilio account and obtain:

- Account SID
- Auth Token
- Twilio phone number

Put them in `.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
ALERT_TO_NUMBER=+91xxxxxxxxxx
```

For a Twilio trial account, follow Twilio's verification requirements for destination numbers.

---

# Push Setup — Firebase Cloud Messaging

Create a Firebase project and configure Cloud Messaging.

Create a service account key for your authorized test project.

Store the JSON somewhere outside the repository, for example:

```text
secrets/firebase-service-account.json
```

Set:

```env
FIREBASE_CREDENTIALS_PATH=./secrets/firebase-service-account.json
FCM_DEVICE_TOKEN=your_test_device_token
```

The service-account JSON is intentionally ignored by Git.

---

# Redis Setup

Celery uses Redis as its broker/backend.

### Linux

Install and start Redis using your distribution's package manager.

Check:

```bash
redis-cli ping
```

Expected:

```text
PONG
```

### Windows

Use a supported Redis-compatible server or run Redis through WSL/Docker.

Then set:

```env
REDIS_URL=redis://localhost:6379/0
```

---

# Start the API

```bash
uvicorn main:app --reload
```

The API will normally be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Start the Celery worker

Open another terminal in the project directory.

### Linux / macOS

```bash
celery -A celery_app.celery_app worker --loglevel=info
```

### Windows

For local development:

```powershell
celery -A celery_app.celery_app worker --loglevel=info --pool=solo
```

---

# API Endpoints

## Health

```http
GET /health
```

Example:

```bash
curl http://127.0.0.1:8000/health
```

Response:

```json
{
  "status": "healthy"
}
```

---

## List demo alerts

```http
GET /alerts
```

```bash
curl http://127.0.0.1:8000/alerts
```

---

## Send a demo alert

```http
POST /alerts/demo/alr_001?channel=sms
```

or:

```http
POST /alerts/demo/alr_001?channel=push
```

or:

```http
POST /alerts/demo/alr_001?channel=both
```

The endpoint queues a Celery task.

Example response:

```json
{
  "status": "queued",
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "alert_id": "alr_001",
  "channels": "both"
}
```

---

# Send a custom alert

Example JSON:

```json
{
  "alert_id": "alr_100",
  "fingerprint": "fp_demo_100",
  "severity": "high",
  "confidence": 0.92,
  "source": "Authorized-Test-Feed",
  "summary": "Test threat intelligence alert",
  "channel": "both",
  "phone_number": "+91xxxxxxxxxx",
  "fcm_token": "YOUR_TEST_FCM_TOKEN"
}
```

Send with:

```bash
curl -X POST http://127.0.0.1:8000/alerts/send \
  -H "Content-Type: application/json" \
  -d @alert.json
```

---

# Severity Rule

The service supports:

```text
low
medium
high
critical
```

Configure the minimum notification level:

```env
ALERT_MIN_SEVERITY=high
```

With this configuration:

```text
LOW       -> skipped
MEDIUM    -> skipped
HIGH      -> notification
CRITICAL  -> notification
```

For a demo where every alert is delivered:

```env
ALERT_MIN_SEVERITY=low
```

---

# How the alert moves through the system

```text
1. DarkTrace-style finding is created
             |
             v
2. Finding receives severity/confidence
             |
             v
3. FastAPI receives the alert
             |
             v
4. Celery queues background task
             |
             v
5. Notification service checks severity
             |
       +-----+-----+
       |           |
       v           v
      SMS         Push
       |           |
       v           v
    Twilio        FCM
       |           |
       +-----+-----+
             |
             v
        End user
```

---

# Demo Data

`hardcoded_alerts.py` contains safe demo findings such as:

```text
Employee credentials for acmecorp.com found in a paste dump
Possible brand impersonation detected
```

Replace these with data from your authorized DarkTrace pipeline.

Do not put real leaked credentials, passwords, access tokens, or personal data into demo repositories.

---

# Audit Logging

Notification results can be written to:

```text
audit_log.jsonl
```

The file is ignored by Git by default.

For production, send audit events to a dedicated, access-controlled logging system instead of relying only on a local file.

---

# Troubleshooting

## SMS does not send

Check:

```text
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_FROM_NUMBER
ALERT_TO_NUMBER
```

Also check that the destination number is allowed by your Twilio account.

---

## Push notification does not send

Check:

```text
FIREBASE_CREDENTIALS_PATH
FCM_DEVICE_TOKEN
```

Make sure the FCM token belongs to an authorized test device/application.

---

## Celery task stays queued

Check Redis:

```bash
redis-cli ping
```

Then make sure the Celery worker is running:

```bash
celery -A celery_app.celery_app worker --loglevel=info
```

On Windows:

```powershell
celery -A celery_app.celery_app worker --loglevel=info --pool=solo
```

---

# Security Checklist

Before pushing this repository to GitHub:

- [ ] `.env` is not committed
- [ ] Firebase service-account JSON is not committed
- [ ] Twilio credentials are not committed
- [ ] No real credentials are inside demo alerts
- [ ] No real leaked personal data is stored
- [ ] Test phone numbers/devices are authorized
- [ ] Production secrets are stored in a secret manager
- [ ] HTTPS is used for production API access
- [ ] Authentication/authorization is added before exposing the API publicly
- [ ] Rate limiting is configured for production
- [ ] Audit logs are protected from unauthorized modification

---

# Production Improvements

This PoC intentionally keeps the architecture small.

For a production DarkTrace deployment, consider adding:

- Authentication and RBAC
- Database-backed alert state
- Alert deduplication using fingerprints
- Notification retry policies
- Rate limiting
- User notification preferences
- Multiple recipients
- Email/Webhook channels
- Delivery status callbacks
- Centralized audit logging
- Secret management
- Metrics and monitoring
- Dead-letter queue
- Alert acknowledgement workflow

---

## License

Add the license required by your organization/project before publishing.

## Disclaimer

Use this project only for authorized security monitoring, testing, and notification workflows.
