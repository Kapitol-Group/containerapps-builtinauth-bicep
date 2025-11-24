import os
import re
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from datetime import datetime

# Cosmos DB connection details

COSMOSDB_ACCOUNT = "cosmos-ilzg75heuh4wm"
COSMOS_ENDPOINT = f"https://{COSMOSDB_ACCOUNT}.documents.azure.com:443/"
DATABASE_NAME = "chat-database"
CONTAINER_NAME = "chat-history-kapcoach"
PARTITION_KEY_PATHS = ["entra_oid", "session_id"]  # Hierarchical partition key

DATE_FIELD = "date"  # Change this if your field is named differently

# Use Azure AD authentication
credential = DefaultAzureCredential()
client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)


def is_yyyy_mm_dd(date_str):
    return re.match(r"^\d{4}-\d{2}-\d{2}$", date_str)

def is_dd_mm_yyyy(date_str):
    return re.match(r"^\d{2}/\d{2}/\d{4}$", date_str)

def convert_dd_mm_yyyy_to_yyyy_mm_dd(date_str):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str

items = list(container.read_all_items())
updated_count = 0

for item in items:
    date_val = item.get(DATE_FIELD)
    if date_val:
        if is_yyyy_mm_dd(date_val):
            continue  # Already correct format
        elif is_dd_mm_yyyy(date_val):
            new_date = convert_dd_mm_yyyy_to_yyyy_mm_dd(date_val)
            if new_date != date_val:
                item[DATE_FIELD] = new_date
                partition_key = tuple(item[field] for field in PARTITION_KEY_PATHS)
                container.replace_item(item["id"], item, partition_key)
                updated_count += 1

print(f"Updated {updated_count} items with date format yyyy-mm-dd.")
