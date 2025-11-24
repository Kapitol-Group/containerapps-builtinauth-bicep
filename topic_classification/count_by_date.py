import os
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from datetime import datetime, timezone
from collections import Counter

# Load environment variables
load_dotenv()

# Cosmos DB configuration


COSMOSDB_ACCOUNT = "cosmos-ilzg75heuh4wm"
DATABASE_NAME = "chat-database"
CONTAINER_NAME = "chat-history-kapcoach"


def count_by_date():
    # Create credential using Managed Identity
    credential = DefaultAzureCredential()
    endpoint = f"https://{COSMOSDB_ACCOUNT}.documents.azure.com:443/"
    client = CosmosClient(endpoint, credential=credential)
    database = client.get_database_client(DATABASE_NAME)
    container = database.get_container_client(CONTAINER_NAME)

    # Query all items
    print("Reading items from container...")
    items = list(container.query_items(
        query="SELECT c._ts FROM c",
        enable_cross_partition_query=True
    ))

    # Group by date
    date_counts = Counter()
    for item in items:
        ts = item.get('_ts')
        if ts is not None:
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            date_str = dt.strftime("%Y-%m-%d")
            date_counts[date_str] += 1

    # Print results sorted by date
    for date in sorted(date_counts):
        print(f"{date}: {date_counts[date]}")

if __name__ == "__main__":
    count_by_date()