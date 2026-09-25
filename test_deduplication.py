from siem.event_mapper import create_siem_event


def test_same_alert_same_fingerprint():
    event1 = create_siem_event(
        alert_type="Credential Exposure",
        severity="High",
        ioc_type="email-addr",
        ioc_value="test@example.com",
        source="example-darkweb-source.test",
        affected_asset="example.com",
    )

    event2 = create_siem_event(
        alert_type="Credential Exposure",
        severity="High",
        ioc_type="email-addr",
        ioc_value="test@example.com",
        source="example-darkweb-source.test",
        affected_asset="example.com",
    )

    assert event1["labels"]["dedup_fingerprint"] == \
           event2["labels"]["dedup_fingerprint"]

    print("Same alert fingerprint test passed")


def test_different_ioc_different_fingerprint():
    event1 = create_siem_event(
        alert_type="Credential Exposure",
        severity="High",
        ioc_type="email-addr",
        ioc_value="test1@example.com",
        source="example-darkweb-source.test",
        affected_asset="example.com",
    )

    event2 = create_siem_event(
        alert_type="Credential Exposure",
        severity="High",
        ioc_type="email-addr",
        ioc_value="test2@example.com",
        source="example-darkweb-source.test",
        affected_asset="example.com",
    )

    assert event1["labels"]["dedup_fingerprint"] != \
           event2["labels"]["dedup_fingerprint"]

    print("Different IOC fingerprint test passed")


def test_different_source_different_fingerprint():
    event1 = create_siem_event(
        alert_type="Credential Exposure",
        severity="High",
        ioc_type="email-addr",
        ioc_value="test@example.com",
        source="source-one.test",
        affected_asset="example.com",
    )

    event2 = create_siem_event(
        alert_type="Credential Exposure",
        severity="High",
        ioc_type="email-addr",
        ioc_value="test@example.com",
        source="source-two.test",
        affected_asset="example.com",
    )

    assert event1["labels"]["dedup_fingerprint"] != \
           event2["labels"]["dedup_fingerprint"]

    print("Different source fingerprint test passed")


def test_different_asset_different_fingerprint():
    event1 = create_siem_event(
        alert_type="Credential Exposure",
        severity="High",
        ioc_type="email-addr",
        ioc_value="test@example.com",
        source="example-darkweb-source.test",
        affected_asset="example-one.com",
    )

    event2 = create_siem_event(
        alert_type="Credential Exposure",
        severity="High",
        ioc_type="email-addr",
        ioc_value="test@example.com",
        source="example-darkweb-source.test",
        affected_asset="example-two.com",
    )

    assert event1["labels"]["dedup_fingerprint"] != \
           event2["labels"]["dedup_fingerprint"]

    print("Different asset fingerprint test passed")


if __name__ == "__main__":
    test_same_alert_same_fingerprint()
    test_different_ioc_different_fingerprint()
    test_different_source_different_fingerprint()
    test_different_asset_different_fingerprint()

    print("\nDEDUPLICATION TESTS PASSED")
