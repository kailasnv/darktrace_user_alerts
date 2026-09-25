-- Run once:  psql "$DATABASE_URL" -f schema.sql

CREATE TABLE IF NOT EXISTS alerts (
    alert_id     text PRIMARY KEY,
    fingerprint  text NOT NULL UNIQUE,            -- dedupe key: same fingerprint => same alert
    source_id    text,                            -- machine id (src_pastesite_x)
    watchlist_id text,
    source       text,                            -- display name (PasteSite-X)
    summary      text,
    severity     text NOT NULL
                 CHECK (severity IN ('critical','high','medium','low','informational')),
    confidence   numeric(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    state        text NOT NULL DEFAULT 'new'
                 CHECK (state IN ('new','acknowledged','investigating','resolved','false_positive')),
    first_seen   timestamptz NOT NULL DEFAULT now(),
    last_seen    timestamptz NOT NULL DEFAULT now(),
    count        integer NOT NULL DEFAULT 1 CHECK (count >= 1)
);

-- ---------------------------------------------------------------------------
-- Trigger function: serialise the row as JSON and publish on 'alerts_channel'.
--
-- NOTIFY payloads are capped at 8000 bytes. If a row ever exceeds the budget we
-- send only the primary key + a `truncated` flag so the client can refetch.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION notify_alert_change() RETURNS trigger AS $$
DECLARE
    payload jsonb;
BEGIN
    payload := jsonb_build_object(
        'op',    TG_OP,                 -- 'INSERT' | 'UPDATE'
        'table', TG_TABLE_NAME,
        'ts',    now(),
        'data',  to_jsonb(NEW)
    );

    IF octet_length(payload::text) > 7500 THEN
        payload := jsonb_build_object(
            'op',        TG_OP,
            'table',     TG_TABLE_NAME,
            'ts',        now(),
            'truncated', true,
            'data',      jsonb_build_object('alert_id', NEW.alert_id)
        );
    END IF;

    PERFORM pg_notify('alerts_channel', payload::text);
    RETURN NEW;                          -- return value is ignored for AFTER triggers
END;
$$ LANGUAGE plpgsql;

-- AFTER triggers => the notification is only delivered if the transaction commits.
DROP TRIGGER IF EXISTS alerts_notify_insert ON alerts;
CREATE TRIGGER alerts_notify_insert
    AFTER INSERT ON alerts
    FOR EACH ROW
    EXECUTE FUNCTION notify_alert_change();

-- Skip no-op updates so the dashboard isn't spammed.
DROP TRIGGER IF EXISTS alerts_notify_update ON alerts;
CREATE TRIGGER alerts_notify_update
    AFTER UPDATE ON alerts
    FOR EACH ROW
    WHEN (OLD.* IS DISTINCT FROM NEW.*)
    EXECUTE FUNCTION notify_alert_change();
