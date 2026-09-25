from siem.event_mapper import create_siem_event

def test_email_mapping():
    event = create_siem_event(
        alert_type="Credential Exposure",
        severity="High",
        ioc_type="email-addr",
        ioc_value="test-user@example.com",
        source="example-darkweb-source.test",
        affected_asset="example.com",
    )

    indicator = event["threat"]["indicator"]

    assert indicator["type"] == "email-addr"
    assert indicator["name"] == "test-user@example.com"

    print("Email IOC test passed")


def test_domain_mapping():
    event = create_siem_event(
        alert_type="Malicious Domain",
        severity="Medium",
        ioc_type="domain-name",
        ioc_value="malicious.example",
        source="example-darkweb-source.test",
        affected_asset="example.com",
    )

    indicator = event["threat"]["indicator"]

    assert indicator["type"] == "domain-name"
    assert indicator["name"] == "malicious.example"

    print("Domain IOC test passed")


def test_ip_mapping():
    event = create_siem_event(
        alert_type="Suspicious IP",
        severity="High",
        ioc_type="ipv4-addr",
        ioc_value="192.0.2.10",
        source="example-darkweb-source.test",
        affected_asset="example.com",
    )

    indicator = event["threat"]["indicator"]

    assert indicator["type"] == "ipv4-addr"
    assert indicator["name"] == "192.0.2.10"

    print("IP IOC test passed")


def test_url_mapping():
    event = create_siem_event(
        alert_type="Malicious URL",
        severity="Critical",
        ioc_type="url",
        ioc_value="https://malicious.example/login",
        source="example-darkweb-source.test",
        affected_asset="example.com",
    )

    indicator = event["threat"]["indicator"]

    assert indicator["type"] == "url"
    assert indicator["name"] == "https://malicious.example/login"

    print("URL IOC test passed")


def test_hash_mapping():
    sha256_hash = (
        "0123456789abcdef0123456789abcdef"
        "0123456789abcdef0123456789abcdef"
    )

    event = create_siem_event(
        alert_type="Leaked File Hash",
        severity="Medium",
        ioc_type="file",
        ioc_value=sha256_hash,
        source="example-darkweb-source.test",
        affected_asset="example.com",
    )

    indicator = event["threat"]["indicator"]

    assert indicator["type"] == "file"
    assert indicator["name"] == sha256_hash

    # ECS SHA-256 mapping
    assert indicator["file"]["hash"]["sha256"] == sha256_hash

    print("File SHA-256 IOC test passed")


if __name__ == "__main__":
    test_email_mapping()
    test_domain_mapping()
    test_ip_mapping()
    test_url_mapping()
    test_hash_mapping()

    print("\nIOC MAPPING TESTS PASSED")
