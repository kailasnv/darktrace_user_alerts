import uuid

from siem.elastic_client import ElasticSIEMClient
from siem.event_mapper import create_siem_event


def main():
    # Use a unique IOC so every test run creates a new event
    unique_ioc = f"pipeline-{uuid.uuid4().hex}@example.com"

    event = create_siem_event(
        alert_type="Credential Exposure",
        severity="High",
        ioc_type="email-addr",
        ioc_value=unique_ioc,
        source="pipeline-test.example",
        affected_asset="example.com",
    )

    siem = ElasticSIEMClient()

    response = siem.send_event(event)

    if response["status"] == "indexed":
        print("SIEM EVENT SENT SUCCESSFULLY")
        print("Index:", response["index"])
        print("Document ID:", response["id"])

    elif response["status"] == "duplicate":
        print("DUPLICATE SIEM EVENT SKIPPED")
        print(response["message"])

    else:
        print("SIEM EVENT FAILED")
        print(response)


if __name__ == "__main__":
    main()
