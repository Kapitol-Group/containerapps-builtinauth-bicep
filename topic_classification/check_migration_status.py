import os
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

COSMOSDB_ACCOUNT = "cosmos-qrzha7zt4ecfq"
DATABASE_NAME = "chat-database"
SOURCE_CONTAINER = "topic-history-kapcoach-old"
DEST_CONTAINER = "topic-history-kapcoach"

credential = DefaultAzureCredential()
endpoint = f"https://{COSMOSDB_ACCOUNT}.documents.azure.com:443/"

print(f"Connecting to Cosmos DB...")
client = CosmosClient(endpoint, credential=credential)
database = client.get_database_client(DATABASE_NAME)

# Check source container
print("\n=== SOURCE CONTAINER (topic-history-kapcoach-old) ===")
source = database.get_container_client(SOURCE_CONTAINER)
source_query = "SELECT COUNT(1) as count FROM c"
source_count = list(source.query_items(query=source_query, enable_cross_partition_query=True))[0]['count']
print(f"Total items: {source_count}")

# Check if items have entra_oid
sample_query = "SELECT TOP 3 c.id, c.session_id, c.entra_oid FROM c"
samples = list(source.query_items(query=sample_query, enable_cross_partition_query=True))
print(f"\nSample items from source:")
for item in samples:
    print(f"  id: {item.get('id')}")
    print(f"  session_id: {item.get('session_id')}")
    print(f"  entra_oid: {item.get('entra_oid')}")
    print()

# Check destination container
print("=== DESTINATION CONTAINER (topic-history-kapcoach) ===")
dest = database.get_container_client(DEST_CONTAINER)
dest_query = "SELECT COUNT(1) as count FROM c"
dest_count = list(dest.query_items(query=dest_query, enable_cross_partition_query=True))[0]['count']
print(f"Total items: {dest_count}")

# Check if any items match our user-{n} pattern
user_query = "SELECT COUNT(1) as count FROM c WHERE STARTSWITH(c.entra_oid, 'user-')"
try:
    user_count = list(dest.query_items(query=user_query, enable_cross_partition_query=True))[0]['count']
    print(f"Items with 'user-*' entra_oid pattern: {user_count}")
except Exception as e:
    print(f"Could not query for user-* pattern: {e}")

# Get sample from destination
dest_sample_query = "SELECT TOP 3 c.id, c.session_id, c.entra_oid FROM c"
dest_samples = list(dest.query_items(query=dest_sample_query, enable_cross_partition_query=True))
print(f"\nSample items from destination:")
for item in dest_samples:
    print(f"  id: {item.get('id')}")
    print(f"  session_id: {item.get('session_id')}")
    print(f"  entra_oid: {item.get('entra_oid')}")
    print()

print("\n=== SUMMARY ===")
print(f"Source has {source_count} items")
print(f"Destination has {dest_count} items")
if dest_count < source_count:
    print(f"⚠️  Missing {source_count - dest_count} items in destination!")
    print("   Migration did not complete successfully.")
else:
    print("✓ Item counts match!")
