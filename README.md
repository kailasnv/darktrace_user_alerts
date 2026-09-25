# Alert Logic & STIX/TAXII Export

Owns the decision layer between enriched threat findings (e.g. from a DarkTrace-fed
enrichment/NLP pipeline) and every downstream notification channel, plus the
independent conversion of that intelligence into STIX 2.1 / TAXII 2.1 for external
security platforms.

```
Enriched Finding → Risk (9 signals) → Severity → Dedup → Correlation → Suppression → Lifecycle → Routing → Escalation → Alert
Alert (Medium/High → HITL approval, Critical → auto-approved) → STIX 2.1 Mapping → Bundle → TAXII 2.1 → External Security Platform
```

## Project layout

```
alert_engine/
  config.py          9-signal risk weights, severity thresholds, dedup window,
                      routing policy, escalation policy, STIX/TAXII HITL policy
  models.py           EnrichedFinding, RiskSignals, Indicator, Alert,
                       StixExportStatus, RoutingDecision, SuppressionRule
  db.py                SQLAlchemy engine/session + ORM tables
  fingerprint.py       stable alert fingerprint
  risk.py              explainable 0-100 risk scoring from the nine finalized
                        signal families, with per-signal upstream override
                        and neutral-default fallback
  severity.py          score -> severity, tenant-configurable thresholds
  dedup.py             24h (configurable) duplicate detection
  correlation.py         cross-alert correlation via shared threat actor or
                          shared indicators (IOCs), independent of dedup/tenant scope
  suppression.py        scope/reason/expiry suppression rule matching
  lifecycle.py          alert state machine
  hitl.py                 STIX/TAXII export policy gate (severity -> export status)
  routing.py             severity -> channel policy
  escalation.py           unacknowledged/high-priority escalation with time intervals
  engine.py                evaluate_alerts(enriched) orchestrator (Interface 1 + 2)
  celery_app.py            periodic escalation scan task
  api.py                   FastAPI endpoints, including STIX export approve/reject
  stix/
    mapping.py             STIX 2.1 Indicator / Observed Data / Threat Actor / Relationship mapping
    bundle.py               STIX 2.1 bundle construction
    taxii_client.py          TLS-verified, retrying TAXII 2.1 client
    export.py                mapping -> bundle -> publish -> audit orchestration,
                              gated on stix_export_status == APPROVED/EXPORTED/FAILED
  tests/                     pytest suite covering the full checklist
mock_data.py                  mock findings for standalone development
demo.py                        runnable end-to-end example
migrations/                    Alembic environment wired to the SQLAlchemy metadata
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env                # fill in TAXII + API key values
```

## Run the test suite

```bash
pytest
```

54 tests cover: risk scoring across all nine signal families (weight-sum
validation, upstream override vs. neutral-default fallback, per-signal
breakdown), severity boundaries (including tenant overrides), fingerprint
stability, deduplication (in-window and out-of-window), correlation (shared
threat actor across tenants, shared indicator, no false positives), suppression
(active and expired rules), lifecycle transitions, routing per severity, HITL
export-approval gating (auto-approve/require-approval/not-required per
severity, approve/reject transitions, illegal-transition errors), escalation
timing and repeat/limit behavior, STIX 2.1 mapping and pattern correctness,
bundle validity, TAXII publish success/failure/retry auditing, and full
mock-finding-to-TAXII-export integration tests for both the auto-approved
(critical) and HITL-gated (high) paths.

## Run the demo

```bash
python demo.py
```

Prints a standardized Alert payload (including its risk breakdown, related
alert IDs, and STIX export status) and the STIX 2.1 bundle for a mock
ransomware finding, using no network or external services.

## Interface 1 — input contract

`evaluate_alerts()` accepts either a dict or an `EnrichedFinding`. Required
fields: `finding_id`, `threat_type`, `confidence` (0-1), `source_id`, and an
`indicators` list of `{type, value}`. Optional: `watchlist_id`, `tenant_id`,
`threat_actor`, `context`, and `signals` — see "Risk scoring" below. This
module does not assume the upstream team's exact field names beyond this
contract — adjust `EnrichedFinding` in `models.py` once the real enrichment
payload is confirmed.

## Risk scoring — nine finalized signal families

`risk.py` scores every finding against the finalized signal catalogue and
weights:

| Signal | Weight | Upstream field | Fallback when not supplied |
|---|---|---|---|
| keyword | 0.22 | `signals.keyword` | neutral 0.5 |
| classification | 0.24 | `signals.classification` | derived from `threat_type` via `THREAT_TYPE_WEIGHTS` |
| entities | 0.10 | `signals.entities` | derived from indicator type/volume |
| history | 0.10 | `signals.history` | neutral 0.5 |
| source_reputation | 0.10 | `signals.source_reputation` | looked up from `SOURCE_REPUTATION_SCORES` by `source_id` |
| behavior | 0.08 | `signals.behavior` | neutral 0.5 |
| temporal | 0.04 | `signals.temporal` | simple off-hours heuristic on `observed_at` |
| feedback | 0.08 | `signals.feedback` | neutral 0.5 |
| confidence | 0.04 | `finding.confidence` (required, not part of `signals`) | — |

This means the engine does **not** require every upstream feature (keyword
matching, behavioral analytics, analyst-feedback loop, etc.) to exist yet —
any signal the enrichment pipeline hasn't implemented simply falls back to a
neutral 0.5 contribution until it's wired up. `compute_risk_breakdown()`
returns the per-signal contribution alongside the total score for
explainability, and is carried on `Alert.risk_breakdown` for audit/analyst
review.

## Correlation

`correlation.py` links alerts that share a **threat actor** or **overlapping
indicators (IOCs)**, independent of tenant and dedup scoping — the same actor
targeting two different companies still correlates:

```
Finding A → Actor X → Company A
Finding B → Actor X → Company B
        ↓
same actor/entity → related alerts
```

`evaluate_alerts()` populates `Alert.related_alert_ids` on every call. This
is intentionally a simple relational lookup (matching `threat_actor_name` and
indicator-value overlap against recent `AlertRecord`s), not a full graph
engine — see "Extending" if a heavier correlation/graph layer is wanted later.

## STIX/TAXII export — HITL policy gate

STIX/TAXII export is no longer "export for every unsuppressed alert." It is a
policy decision driven by severity, via `Alert.stix_export_status`
(`hitl.py`):

```
Alert
 ↓
Informational / Low   → NOT_REQUIRED        (never exported)
Medium / High          → PENDING_APPROVAL   (waits for analyst sign-off)
Critical                → APPROVED           (auto-approved, exported immediately)
```

`export_alert_to_taxii()` itself enforces this — it raises `StixExportError`
unless `stix_export_status` is `APPROVED`, `EXPORTED`, or `FAILED` (the last
two allow retrying an already-approved export without re-approval; `PENDING_APPROVAL`,
`REJECTED`, and `NOT_REQUIRED` are all blocked). An analyst approves or
rejects a pending export via:

```
POST /v1/alerts/{alert_id}/stix-export/approve
POST /v1/alerts/{alert_id}/stix-export/reject
```

Approval immediately attempts the export and updates the status to
`EXPORTED`/`FAILED`; rejection just records the decision. `GET
/v1/alerts/{alert_id}` returns the current alert, including its export status,
for a dashboard/analyst UI to poll.

## Interface 2 — output contract

`Alert.to_channel_payload()` returns the documented backend fields
(`alert_id`, `fingerprint`, `source_id`, `watchlist_id`, `severity`,
`confidence`, `state`, `first_seen`, `last_seen`, `count`) plus `channels`
for the routing decision, `risk_breakdown`, `related_alert_ids`, and
`stix_export_status`. Email/webhook/dashboard/SMS-push/SIEM teammates
consume this payload; this module does not perform delivery.

## Alert routing

```
Informational → batch_digest
Low           → batch_digest + dashboard
Medium        → dashboard (real-time) + email (daily digest)
High          → dashboard + email + webhook
Critical      → dashboard + email + webhook + sms_push + siem + on_call
```

STIX/TAXII is deliberately **not** in this channel list — it's governed
entirely by the HITL gate above, independent of notification routing.

## Alert lifecycle

```
new
acknowledged
investigating
escalated     (time-based escalation per ESCALATION_POLICY, not a full-alert-lifecycle terminal state)
dismissed     == the "False Positive" path
closed        == "Resolved"
```

The documented brief describes `New → Acknowledged → Investigating →
Resolved/Closed` plus an alternate `New → False Positive` path. This
implementation keeps its richer six-state machine (it also needed an explicit
`Escalated` state for the escalation requirement); `dismissed` and `closed`
are the exact equivalents of `False Positive` and `Resolved/Closed`
respectively — see `LIFECYCLE_STATE_ALIASES` in `config.py`.

## Running the API

```bash
uvicorn alert_engine.api:app --reload
```

`POST /v1/findings` with an `X-API-Key` header (if `ALERT_ENGINE_INGEST_API_KEY`
is set) and an enriched finding body. The endpoint evaluates the alert,
persists it, and — only if `stix_export_status` is already `APPROVED`
(i.e. critical severity) — immediately attempts the STIX/TAXII export.
Medium/High alerts come back with `stix_export.pending_approval: true` and
wait for the approve/reject endpoints above. The web framework binding is a
thin wrapper; swap it for the team's actual framework once `main.py` / the
dependency file confirm it, since `evaluate_alerts()` and
`export_alert_to_taxii()` have no FastAPI dependency themselves.

## Security notes

- All TAXII calls go over HTTPS with certificate verification on by default
  (`TAXII_VERIFY_TLS`), a bounded timeout, and capped retries with backoff
  only on transient status codes.
- No secrets are hardcoded; TAXII credentials, the ingestion API key, and
  database/broker URLs are all environment-driven (`.env.example`).
- All database access goes through SQLAlchemy's parameterized query builder —
  no raw string-interpolated SQL anywhere in the module.
- Input validation is enforced at the boundary via pydantic; malformed
  findings are rejected with a 422 before touching risk/severity logic.
- External threat-intelligence publication is gated behind the HITL policy
  above — a low-confidence or unreviewed finding can no longer reach an
  external TAXII collection.
- Alembic is wired up (`alembic.ini`, `migrations/`) so schema changes are
  tracked rather than relying on `create_all` in production.

## Extending

- Tune `THREAT_TYPE_WEIGHTS`, `INDICATOR_TYPE_WEIGHTS`, `RISK_SIGNAL_WEIGHTS`,
  and `SOURCE_REPUTATION_SCORES` in `config.py` once the team's actual signal
  catalogue is finalized.
- Per-tenant severity thresholds: populate `TENANT_SEVERITY_THRESHOLDS` in
  `config.py`, or move it to a database-backed lookup.
- Correlation currently does an in-process relational scan
  (`_CORRELATION_SCAN_LIMIT` in `correlation.py`) — if the entity graph grows
  large, this is the natural place to swap in a real graph store (e.g. Neo4j,
  per the wider architecture doc) without changing `engine.py`'s call site.
- STIX/TAXII: `stix/mapping.py` currently maps indicators, observed data
  (as STIX Cyber Observable Objects referenced via `object_refs`, per the
  2.1 spec), and threat actors with `based-on` / `indicates` relationships.
  Extend `_STIX_PATTERN_BUILDERS` and `_STIX_CYBER_OBSERVABLE_BUILDERS` for
  additional indicator types as the enrichment team adds them.
- HITL: `hitl.py`'s approve/reject functions are intentionally not
  actor-attributed yet (no "who approved this" field) — add an `actor_id`
  parameter and an audit row once the audit-log table exists.
