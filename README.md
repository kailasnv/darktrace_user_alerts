# DashAlert

DashAlert is a real-time alerting and dashboard backend built with **FastAPI**, **PostgreSQL**, and optional **Redis** integration.

The application provides REST APIs for alert ingestion and management, PostgreSQL-backed persistence, real-time PostgreSQL `LISTEN/NOTIFY` events, Server-Sent Events (SSE), and WebSocket updates for dashboards.

---

## 1. Features

- FastAPI REST API
- PostgreSQL 16 database
- Alert creation and ingestion
- Alert deduplication using fingerprints
- Alert count/merge handling
- Alert severity and confidence
- Alert state management
- PostgreSQL `LISTEN/NOTIFY`
- Real-time WebSocket dashboard updates
- Server-Sent Events (SSE)
- CORS support for frontend applications
- Health-check endpoint
- Swagger/OpenAPI documentation
- Sample alert seed data
- Optional Redis event bridge
- Docker-based PostgreSQL development environment
- Windows-friendly startup commands

---

## 2. Technology Stack

| Component | Technology |
|---|---|
| Backend | Python |
| API Framework | FastAPI |
| ASGI Server | Uvicorn |
| Database | PostgreSQL 16 |
| PostgreSQL Driver | asyncpg |
| Validation | Pydantic |
| Real-time events | PostgreSQL LISTEN/NOTIFY |
| WebSocket | FastAPI WebSocket |
| SSE | FastAPI StreamingResponse |
| Optional message broker | Redis |
| Containerization | Docker |
| API documentation | Swagger/OpenAPI |

---

## 3. Architecture

```text
                     ┌──────────────────────┐
                     │      Frontend        │
                     │ Dashboard / Web App  │
                     └──────────┬───────────┘
                                │
                    REST / SSE / WebSocket
                                │
                                ▼
                     ┌──────────────────────┐
                     │      FastAPI         │
                     │      main.py         │
                     └──────────┬───────────┘
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
                 ▼                             ▼
        ┌─────────────────┐          ┌─────────────────┐
        │   PostgreSQL    │          │ Real-time Hub   │
        │     alerts      │          │ WebSocket/SSE   │
        └────────┬────────┘          └────────┬────────┘
                 │                            │
                 │ LISTEN/NOTIFY              │
                 └────────────┬───────────────┘
                              ▼
                     ┌─────────────────┐
                     │ pg_listener.py  │
                     └─────────────────┘

Optional:

PostgreSQL → pg_listener → bridge.py → Redis → FastAPI/other consumers
```

---

## 4. Project Structure

```text
DashAlert/
│
├── main.py
├── pg_listener.py
├── bridge.py
├── seed.py
├── seed_data.py
├── schema.sql
├── requirements.txt
├── .env.example
├── run_api.bat
└── README.md
```

### File descriptions

#### `main.py`

Main FastAPI application.

Contains:

- FastAPI application creation
- CORS configuration
- PostgreSQL connection pool
- REST endpoints
- WebSocket endpoint
- SSE endpoint
- PostgreSQL listener startup
- Alert insertion/update logic
- Health checks
- Demo replay

#### `pg_listener.py`

Maintains the PostgreSQL `LISTEN` connection.

It:

- Connects to PostgreSQL
- Listens for `NOTIFY` events
- Automatically reconnects after connection failures
- Uses exponential backoff
- Sends events to the application event hub

#### `bridge.py`

Optional PostgreSQL-to-Redis bridge.

It is only required if the architecture uses Redis as the notification source.

#### `seed.py`

Loads sample alerts into PostgreSQL.

#### `seed_data.py`

Contains sample alert data.

#### `schema.sql`

Creates the PostgreSQL tables, functions, and triggers.

#### `requirements.txt`

Python dependencies.

#### `.env.example`

Example environment configuration.

#### `run_api.bat`

Windows helper script for starting FastAPI.

---

# 5. Prerequisites

Install the following:

- Python 3.10+
- Docker Desktop
- Git (optional)
- A modern web browser

PostgreSQL can be installed directly on Windows, but this project is configured to work with PostgreSQL running inside Docker.

---

# 6. PostgreSQL with Docker

Start Docker Desktop first.

Create the PostgreSQL container:

```powershell
docker run -d --name alerts-postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=alerts `
  -p 5432:5432 `
  postgres:16
```

Verify:

```powershell
docker ps
```

Expected port mapping:

```text
127.0.0.1:5432->5432/tcp
```

Test the Windows port:

```powershell
Test-NetConnection localhost -Port 5432
```

Expected:

```text
TcpTestSucceeded : True
```

---

# 7. Database Configuration

The default connection string is:

```text
postgresql://postgres:postgres@localhost:5432/alerts
```

In Windows PowerShell:

```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/alerts"
```

Verify:

```powershell
echo $env:DATABASE_URL
```

Expected:

```text
postgresql://postgres:postgres@localhost:5432/alerts
```

The application also supports these optional variables:

```text
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/alerts
PG_CHANNEL=alerts_channel
PG_POOL_MIN=2
PG_POOL_MAX=10
NOTIFY_SOURCE=postgres
REDIS_URL=redis://localhost:6379/0
REDIS_CHANNEL=alerts:events
```

For a normal local installation, use:

```text
NOTIFY_SOURCE=postgres
```

Redis is not required for the normal setup.

---

# 8. Python Environment

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

---

# 9. Initialize the Database

After PostgreSQL is running, load the schema.

From the project directory:

```powershell
Get-Content .\schema.sql | docker exec -i alerts-postgres psql -U postgres -d alerts
```

Successful output contains statements such as:

```text
CREATE TABLE
CREATE FUNCTION
CREATE TRIGGER
```

The trigger `NOTICE` messages about a trigger not existing during the initial setup are normal.

Verify the tables:

```powershell
docker exec -it alerts-postgres psql -U postgres -d alerts -c "\dt"
```

Inspect the alerts table:

```powershell
docker exec -it alerts-postgres psql -U postgres -d alerts -c "\d alerts"
```

---

# 10. Load Sample Alerts

Set the database URL:

```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/alerts"
```

Run:

```powershell
python seed.py
```

A successful run looks similar to:

```text
Connecting to PostgreSQL...
Connected to PostgreSQL.
Loading 15 alerts...
inserted alr_001 -> alr_001
merged   alr_002 -> alr_001
...
Seed completed successfully.
Database connection closed.
```

The seed process demonstrates alert deduplication/merging based on the configured fingerprint.

---

# 11. Start FastAPI

Start the application with:

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Or use the Windows helper:

```powershell
.\run_api.bat
```

The API will be available at:

```text
http://127.0.0.1:8000
```

---

# 12. Root Endpoint

Open:

```text
http://127.0.0.1:8000/
```

Expected response:

```json
{
  "status": "ok",
  "message": "DashAlert API is running",
  "docs": "/docs",
  "health": "/healthz",
  "alerts": "/alerts",
  "websocket": "/ws/dashboard",
  "stream": "/stream"
}
```

This route is intentionally provided as a simple backend health/entry endpoint.

---

# 13. Swagger API Documentation

FastAPI automatically provides interactive documentation.

Open:

```text
http://127.0.0.1:8000/docs
```

Alternative OpenAPI schema:

```text
http://127.0.0.1:8000/openapi.json
```

Swagger can be used to test the REST endpoints without a separate API client.

---

# 14. Health Check

Request:

```http
GET /healthz
```

Example:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

Expected response:

```json
{
  "ok": true,
  "database": "connected",
  "ws_clients": 0,
  "sse_clients": 0
}
```

---

# 15. Alert APIs

## Get all alerts

```http
GET /alerts
```

Alternative frontend-compatible route:

```http
GET /api/alerts
```

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/alerts
```

---

## Get one alert

```http
GET /alerts/{alert_id}
```

Example:

```text
GET /alerts/alr_001
```

---

## Create or merge an alert

```http
POST /alerts
```

Example request:

```json
{
  "alert_id": "alr_demo_001",
  "fingerprint": "demo-fingerprint-001",
  "severity": "high",
  "confidence": 0.92,
  "state": "new",
  "count": 1,
  "source_id": "sensor-01",
  "source": "network-monitor",
  "summary": "Suspicious network activity detected"
}
```

The same endpoint can be called through:

```text
POST /api/alerts
```

If an existing alert has the same fingerprint, the application merges the event instead of creating an unrelated duplicate.

---

# 16. Update Alert State

Endpoint:

```http
PATCH /alerts/{alert_id}/state
```

Example:

```text
PATCH /alerts/alr_001/state
```

Body:

```json
{
  "state": "acknowledged"
}
```

Supported states:

```text
new
acknowledged
investigating
resolved
false_positive
```

---

# 17. Alert Severity

Supported severity values:

```text
critical
high
medium
low
informational
```

The alerts endpoint orders results by severity and then most recent activity.

---

# 18. Demo Replay

The backend can replay the sample alerts.

Endpoint:

```http
POST /demo/replay
```

Example:

```text
POST /demo/replay?delay=2
```

To reset the alert table before replaying:

```text
POST /demo/replay?delay=2&reset=true
```

The replay is processed in the background.

---

# 19. WebSocket Dashboard

WebSocket endpoint:

```text
ws://127.0.0.1:8000/ws/dashboard
```

The connection sends a `HELLO` message after connection.

Example:

```json
{
  "op": "HELLO",
  "clients": 1
}
```

Clients can send:

```text
ping
```

and receive:

```json
{
  "op": "PONG"
}
```

Database alert notifications are broadcast to connected dashboard clients.

---

# 20. Server-Sent Events

SSE endpoint:

```text
http://127.0.0.1:8000/stream
```

A browser frontend can consume it with:

```javascript
const events = new EventSource(
  "http://127.0.0.1:8000/stream"
);

events.addEventListener("alert", (event) => {
  const data = JSON.parse(event.data);
  console.log("Alert event:", data);
});
```

The server sends periodic keep-alive comments so long-running connections remain active.

---

# 21. PostgreSQL LISTEN/NOTIFY

DashAlert uses PostgreSQL's native notification mechanism.

The database notification channel is:

```text
alerts_channel
```

The listener:

```text
pg_listener.py
```

connects to PostgreSQL and waits for notification events.

The flow is:

```text
Database trigger
      ↓
NOTIFY alerts_channel
      ↓
pg_listener.py
      ↓
FastAPI event hub
      ↓
WebSocket / SSE clients
      ↓
Dashboard updates
```

---

# 22. Optional Redis Architecture

Redis is optional.

Use Redis when the application needs a message broker or multiple services need to consume alert events.

Architecture:

```text
PostgreSQL
    │
    │ LISTEN
    ▼
bridge.py
    │
    │ PUBLISH
    ▼
Redis
    │
    │ SUBSCRIBE
    ▼
FastAPI
    │
    ├── WebSocket
    └── SSE
```

For the normal local installation, Redis does not need to be running.

If Redis is used, configure:

```text
NOTIFY_SOURCE=redis
REDIS_URL=redis://localhost:6379/0
REDIS_CHANNEL=alerts:events
```

Then run the bridge separately:

```powershell
python bridge.py
```

Only run one active bridge for a given PostgreSQL notification channel unless the deployment is deliberately designed for multiple bridge instances.

---

# 23. Windows PowerShell Commands

### Start PostgreSQL

```powershell
docker start alerts-postgres
```

### Check PostgreSQL

```powershell
docker ps
```

### Check logs

```powershell
docker logs alerts-postgres --tail 50
```

### Check port

```powershell
Test-NetConnection localhost -Port 5432
```

### Set database URL

```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/alerts"
```

### Start FastAPI

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Seed data

```powershell
python seed.py
```

---

# 24. Common Errors

## `{"detail":"Not Found"}`

If the root URL previously returned:

```json
{
  "detail": "Not Found"
}
```

the server was reachable but no `/` route existed.

The corrected `main.py` now provides:

```http
GET /
```

Open:

```text
http://127.0.0.1:8000/
```

---

## Docker API error

If you see:

```text
failed to connect to the Docker API
```

start Docker Desktop.

Then run:

```powershell
docker ps
```

---

## PostgreSQL connection refused

Check:

```powershell
docker ps
```

The PostgreSQL container should show:

```text
127.0.0.1:5432->5432/tcp
```

Then:

```powershell
Test-NetConnection localhost -Port 5432
```

---

## `relation "alerts" does not exist`

Load the schema:

```powershell
Get-Content .\schema.sql | docker exec -i alerts-postgres psql -U postgres -d alerts
```

Then verify:

```powershell
docker exec -it alerts-postgres psql -U postgres -d alerts -c "\dt"
```

---

## `ModuleNotFoundError`

Activate the virtual environment and reinstall:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

# 25. Security Notes

The default credentials are intended for local development only:

```text
username: postgres
password: postgres
```

For production:

- Use a strong database password.
- Store secrets outside source code.
- Restrict CORS origins.
- Use HTTPS.
- Put FastAPI behind a production reverse proxy.
- Use authentication and authorization for alert-management endpoints.
- Do not expose PostgreSQL port `5432` publicly.
- Use a managed secret/environment configuration.
- Restrict WebSocket access.
- Add rate limiting where appropriate.
- Add structured audit logging.

---

# 26. Production Considerations

For production deployment, consider:

```text
                    Internet
                       │
                       ▼
                 Reverse Proxy
                       │
                       ▼
                 FastAPI/Uvicorn
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     PostgreSQL      Redis       Workers
          │
          ▼
       Alerts
```

Recommended production improvements include:

- Authentication
- Role-based access control
- HTTPS
- Database migrations
- Connection pooling
- Structured logging
- Metrics
- Distributed tracing
- Rate limiting
- Background workers
- Redis for distributed event delivery
- PostgreSQL backups
- Monitoring and alerting
- Container orchestration where appropriate

---

# 27. Development Workflow

Typical development sequence:

```text
1. Start Docker Desktop
        ↓
2. Start PostgreSQL container
        ↓
3. Verify port 5432
        ↓
4. Set DATABASE_URL
        ↓
5. Install Python dependencies
        ↓
6. Initialize schema
        ↓
7. Run seed.py
        ↓
8. Start FastAPI
        ↓
9. Open /docs
        ↓
10. Connect dashboard through REST/WebSocket/SSE
```

---

# 28. Quick Start

For an already configured machine:

```powershell
docker start alerts-postgres

$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/alerts"

python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Then open:

```text
http://127.0.0.1:8000/
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Alerts:

```text
http://127.0.0.1:8000/alerts
```

Health:

```text
http://127.0.0.1:8000/healthz
```

---

# 29. Project Status

Current local development stack:

```text
FastAPI              ✓
Uvicorn              ✓
PostgreSQL 16        ✓
Docker               ✓
asyncpg              ✓
REST API             ✓
Alert seeding        ✓
Alert merge logic    ✓
PostgreSQL events    ✓
WebSocket            ✓
SSE                  ✓
Swagger              ✓
Health check         ✓
Optional Redis       ✓
```

---

## License

Add your organization's or project's license here before public distribution.

---

## Author

Create By Ohm Dubey

DashAlert Project

A real-time alert monitoring and dashboard backend for security/event alert workflows.
