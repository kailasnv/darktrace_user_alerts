from alert_engine.models import Severity
from alert_engine.routing import decide_routing


def test_critical_routes_to_all_channels_plus_siem_and_on_call():
    decision = decide_routing(Severity.CRITICAL)
    assert set(decision.channels) == {"dashboard", "email", "webhook", "sms_push", "siem", "on_call"}


def test_informational_routes_to_batch_digest_only():
    decision = decide_routing(Severity.INFORMATIONAL)
    assert decision.channels == ["batch_digest"]


def test_low_routes_to_batch_digest_and_dashboard():
    decision = decide_routing(Severity.LOW)
    assert set(decision.channels) == {"batch_digest", "dashboard"}


def test_medium_routes_to_dashboard_and_email():
    decision = decide_routing(Severity.MEDIUM)
    assert set(decision.channels) == {"dashboard", "email"}


def test_high_routes_to_dashboard_email_and_webhook():
    decision = decide_routing(Severity.HIGH)
    assert set(decision.channels) == {"dashboard", "email", "webhook"}
