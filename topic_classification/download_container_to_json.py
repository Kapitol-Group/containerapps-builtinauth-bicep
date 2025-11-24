import os
import json
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Cosmos DB configuration - MODIFY THESE AS NEEDED
COSMOSDB_ACCOUNT = "cosmos-qrzha7zt4ecfq"
DATABASE_NAME = "chat-database"
CONTAINER_NAME = "topic-history-kapcoach-old"  # Change this to your target container

# Output directory
OUTPUT_DIR = "../data"  # Relative to topic_classification folder (points to /data in root)

def download_container_to_json():
    """
    Download all documents from a Cosmos DB container to individual JSON files.
    Each document is saved as a separate file in the data folder.
    """
    
    # Create data directory if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, OUTPUT_DIR)
    os.makedirs(output_path, exist_ok=True)
    
    print(f"Output directory: {output_path}")
    
    # Create credential using Managed Identity / Azure CLI auth
    credential = DefaultAzureCredential()
    
    # Build endpoint URL
    endpoint = f"https://{COSMOSDB_ACCOUNT}.documents.azure.com:443/"
    
    # Create Cosmos client
    print(f"Connecting to Cosmos DB ({COSMOSDB_ACCOUNT})...")
    client = CosmosClient(endpoint, credential=credential)
    database = client.get_database_client(DATABASE_NAME)
    container = database.get_container_client(CONTAINER_NAME)
    
    # Query all items from container
    print(f"Reading items from container '{CONTAINER_NAME}'...")
    query = "SELECT * FROM c"
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    
    print(f"Found {len(items)} documents to download")
    
    # Download each item as a separate JSON file
    successful = 0
    failed = 0
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for idx, item in enumerate(items):
        try:
            # Create filename from document id (sanitize for filesystem)
            doc_id = item.get('id', f'document_{idx}')
            safe_filename = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in doc_id)
            filename = f"{safe_filename}.json"
            filepath = os.path.join(output_path, filename)
            
            # Handle duplicate filenames
            counter = 1
            while os.path.exists(filepath):
                filename = f"{safe_filename}_{counter}.json"
                filepath = os.path.join(output_path, filename)
                counter += 1
            
            # Write document to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(item, f, indent=2, ensure_ascii=False)
            
            successful += 1
            
            if (idx + 1) % 100 == 0:
                print(f"Progress: {idx + 1}/{len(items)} documents downloaded")
                
        except Exception as e:
            failed += 1
            print(f"Error downloading document {item.get('id', 'unknown')}: {str(e)}")
    
    # Also create a single consolidated file with all documents
    consolidated_filename = f"all_documents_{CONTAINER_NAME}_{timestamp}.json"
    consolidated_filepath = os.path.join(output_path, consolidated_filename)
    
    try:
        with open(consolidated_filepath, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Created consolidated file: {consolidated_filename}")
    except Exception as e:
        print(f"\n✗ Failed to create consolidated file: {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"Download complete!")
    print(f"{'='*60}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total documents: {len(items)}")
    print(f"Output directory: {output_path}")
    print(f"Individual files: {successful}")
    print(f"Consolidated file: {consolidated_filename}")
    print(f"{'='*60}")

if __name__ == "__main__":
    download_container_to_json()
