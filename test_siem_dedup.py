import uuid

from siem.elastic_client import ElasticSIEMClient
from siem.event_mapper import create_siem_event

def test_duplicate_event_is_skipped():
    unique_ioc = f"dedup-{uuid.uuid4().hex}@example.com"
    event = create_siem_event(
        alert_type="Credential Exposure",
        severity="High",
        ioc_type="email-addr",
        ioc_value=unique_ioc,
        source="dedup-test-source.example",
        affected_asset="dedup-test.example",
    )

    siem = ElasticSIEMClient()

    # First event should be indexed.
    first_response = siem.send_event(event)

    assert first_response["status"] == "indexed"

    print("First event indexed successfully")

    # Send exactly the same event again.
    second_response = siem.send_event(event)

    assert second_response["status"] == "duplicate"

    print("Duplicate event skipped successfully")


if __name__ == "__main__":
    test_duplicate_event_is_skipped()

    print("\nSIEM DEDUPLICATION TEST PASSED")
