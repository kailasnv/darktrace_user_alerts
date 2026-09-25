from dotenv import load_dotenv
import os
from elasticsearch import Elasticsearch

load_dotenv()

elastic_url = os.getenv("ELASTIC_URL")
api_key = os.getenv("ELASTIC_API_KEY")

print("1. ELASTIC_URL loaded:", bool(elastic_url))
print("2. ELASTIC_API_KEY loaded:", bool(api_key))

try:
    print("3. Creating Elasticsearch client...")

    client = Elasticsearch(
        hosts=[elastic_url],
        api_key=api_key,
        request_timeout=10
    )

    print("4. Client created.")
    print("5. Testing connection...")

    info = client.info()

    print("6. CONNECTED SUCCESSFULLY!")
    print("Cluster:", info.get("cluster_name"))
    print("Version:", info["version"]["number"])

except Exception as e:
    print("7. CONNECTION FAILED")
    print("Error type:", type(e).__name__)
    print("Error:", str(e))
