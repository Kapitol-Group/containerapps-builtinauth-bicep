import os
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Source Cosmos DB configuration
SOURCE_COSMOSDB_ACCOUNT = "cosmos-ilzg75heuh4wm"
SOURCE_DATABASE_NAME = "chat-database"
SOURCE_CONTAINER_NAME = "topic-history-kapcoach"

# Destination Cosmos DB configuration
DEST_COSMOSDB_ACCOUNT = "cosmos-ilzg75heuh4wm"
DEST_DATABASE_NAME = "chat-database"
DEST_CONTAINER_NAME = "topic-history-kapcoach-old"

# Partition key path (must be the same in both containers)
PARTITION_KEY_PATH = "/session_id"  # Adjust to your actual partition key

def migrate_partition_data():
    """
    Migrate all data from source Cosmos DB container to destination container.
    Performs upsert to handle duplicates.
    Uses Managed Identity for authentication.
    """
    
    # Create credential using Managed Identity
    credential = DefaultAzureCredential()
    
    # Build endpoint URLs from account names
    source_endpoint = f"https://{SOURCE_COSMOSDB_ACCOUNT}.documents.azure.com:443/"
    dest_endpoint = f"https://{DEST_COSMOSDB_ACCOUNT}.documents.azure.com:443/"
    
    # Create source client
    print(f"Connecting to source Cosmos DB ({SOURCE_COSMOSDB_ACCOUNT})...")
    source_client = CosmosClient(source_endpoint, credential=credential)
    source_database = source_client.get_database_client(SOURCE_DATABASE_NAME)
    source_container = source_database.get_container_client(SOURCE_CONTAINER_NAME)
    
    # Create destination client
    print(f"Connecting to destination Cosmos DB ({DEST_COSMOSDB_ACCOUNT})...")
    dest_client = CosmosClient(dest_endpoint, credential=credential)
    dest_database = dest_client.get_database_client(DEST_DATABASE_NAME)
    dest_container = dest_database.get_container_client(DEST_CONTAINER_NAME)
    
    # Query all items from source
    print("Reading items from source container...")
    query = "SELECT * FROM c"
    items = list(source_container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    
    print(f"Found {len(items)} items to migrate")
    
    # Upsert items to destination
    successful = 0
    failed = 0
    
    for idx, item in enumerate(items):
        try:
            # Upsert item (insert or update if exists)
            dest_container.upsert_item(item)
            successful += 1
            
            if (idx + 1) % 100 == 0:
                print(f"Progress: {idx + 1}/{len(items)} items processed")
                
        except Exception as e:
            failed += 1
            print(f"Error upserting item {item.get('id', 'unknown')}: {str(e)}")
    
    print(f"\nMigration complete!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {len(items)}")

if __name__ == "__main__":
    migrate_partition_data()