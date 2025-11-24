import os
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Target Cosmos DB configuration
COSMOSDB_ACCOUNT = "cosmos-ilzg75heuh4wm"
DATABASE_NAME = "chat-database"
CONTAINER_NAME = "topic-history-kapcoach"
PARTITION_KEY_PATHS = ["/entra_oid", "/session_id"]  # Hierarchical partition key



def delete_all_items():
    credential = DefaultAzureCredential()
    endpoint = f"https://{COSMOSDB_ACCOUNT}.documents.azure.com:443/"
    client = CosmosClient(endpoint, credential=credential)
    database = client.get_database_client(DATABASE_NAME)
    container = database.get_container_client(CONTAINER_NAME)

    print("Querying all items for deletion...")
    query = "SELECT * FROM c"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))

    print(f"Found {len(items)} items to delete")
    deleted = 0
    failed = 0

    for item in items:
        try:
            # Build partition key value list for hierarchical partition key
            partition_key_values = []
            missing_pk = False
            for pk_path in PARTITION_KEY_PATHS:
                path = pk_path.lstrip('/')
                if path in item:
                    partition_key_values.append(item[path])
                else:
                    print(f"Error: Item {item.get('id', 'unknown')} missing partition key part '{path}'")
                    missing_pk = True
                    break
            if missing_pk:
                failed += 1
                continue
            container.delete_item(item['id'], partition_key=partition_key_values)
            deleted += 1
        except Exception as e:
            failed += 1
            print(f"Error deleting item {item.get('id', 'unknown')}: {str(e)}")

    print(f"Deletion complete! Deleted: {deleted}, Failed: {failed}")

if __name__ == "__main__":
    delete_all_items()