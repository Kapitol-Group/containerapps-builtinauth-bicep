import os
import json
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Source Cosmos DB configuration
SOURCE_COSMOSDB_ACCOUNT = "cosmos-qrzha7zt4ecfq"
SOURCE_DATABASE_NAME = "chat-database"
SOURCE_CONTAINER_NAME = "topic-history-kapcoach-old"

def export_with_entra_oid():
    """
    Export data from source and add entra_oid field for manual import.
    """
    
    credential = DefaultAzureCredential()
    source_endpoint = f"https://{SOURCE_COSMOSDB_ACCOUNT}.documents.azure.com:443/"
    
    print(f"Connecting to source Cosmos DB ({SOURCE_COSMOSDB_ACCOUNT})...")
    source_client = CosmosClient(source_endpoint, credential=credential)
    source_database = source_client.get_database_client(SOURCE_DATABASE_NAME)
    source_container = source_database.get_container_client(SOURCE_CONTAINER_NAME)
    
    # Query all items from source
    print("Reading items from source container...")
    query = "SELECT * FROM c"
    items = list(source_container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    
    print(f"Found {len(items)} items to migrate")
    
    # Prepare items for export
    export_items = []
    for idx, item in enumerate(items):
        # Remove Cosmos DB system fields (except id and session_id)
        clean_item = {
            'id': item['id'],
            'session_id': item['session_id'],
            'entra_oid': f"user-{idx + 1}",  # Add entra_oid
            'question': item.get('question', ''),
            'topic': item.get('topic', '')
        }
        
        # Add any other custom fields from source
        for key in item:
            if key not in ['id', 'session_id', 'question', 'topic'] and not key.startswith('_'):
                clean_item[key] = item[key]
        
        export_items.append(clean_item)
    
    # Export to NDJSON (newline-delimited JSON) format for bulk import
    output_file = "migration_data_for_bulk_import.ndjson"
    with open(output_file, 'w') as f:
        for item in export_items:
            f.write(json.dumps(item) + '\n')
    
    print(f"\n✓ Exported {len(export_items)} items to {output_file}")
    print("\n=== Manual Import Instructions ===")
    print("Since the Python SDK doesn't support hierarchical partition keys,")
    print("you'll need to use one of these methods:\n")
    print("METHOD 1: Azure Portal Bulk Import")
    print("1. Go to Azure Portal > Your Cosmos DB account")
    print("2. Navigate to Data Explorer")
    print("3. Right-click on 'topic-history-kapcoach' container")
    print("4. Select 'Upload Item' or 'Import Items'")
    print(f"5. Upload the file: {output_file}")
    print("\nMETHOD 2: Use Azure Cosmos DB Data Migration Tool")
    print("Download from: https://aka.ms/csdmtool")
    print("\nMETHOD 3: Write items individually (slow but works)")
    print("Run: python3 migrate_one_by_one.py")
    
    # Also create individual JSON files for portal upload (max 100 items per file due to portal limits)
    batch_size = 100
    for batch_num in range(0, len(export_items), batch_size):
        batch = export_items[batch_num:batch_num + batch_size]
        batch_file = f"migration_batch_{batch_num // batch_size + 1}.json"
        with open(batch_file, 'w') as f:
            json.dump(batch, f, indent=2)
        print(f"Created batch file: {batch_file} ({len(batch)} items)")
    
    return output_file

if __name__ == "__main__":
    export_file = export_with_entra_oid()
    print(f"\n✓ Export complete! Files ready for manual import.")
