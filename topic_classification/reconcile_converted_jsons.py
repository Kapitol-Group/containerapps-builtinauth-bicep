"""
Reconcile local JSON files against Cosmos DB container.
Compare entra_oid and session_id combinations.
"""
import json
import os
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient

# Configuration
COSMOS_ENDPOINT = "https://cosmos-ilzg75heuh4wm.documents.azure.com:443/"
DATABASE_NAME = "chat-database"
CONTAINER_NAME = "chat-history-kapcoach"
LOCAL_JSON_DIR = Path(__file__).parent.parent / "data" / "converted_jsons"

def get_local_combinations():
    """
    Extract all entra_oid and id combinations from local JSON files.
    Check ALL documents (both session and message_pair).
    
    Returns:
        Set of tuples (id, entra_oid, type)
    """
    print("📂 Reading local JSON files...")
    local_combinations = set()
    type_counts = {}
    
    if not LOCAL_JSON_DIR.exists():
        print(f"❌ Directory not found: {LOCAL_JSON_DIR}")
        return local_combinations
    
    for json_file in LOCAL_JSON_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            doc_id = data.get('id')
            entra_oid = data.get('entra_oid')
            doc_type = data.get('type', 'unknown')
            
            # Count by type
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
            if doc_id and entra_oid:
                local_combinations.add((doc_id, entra_oid, doc_type))
        except Exception as e:
            print(f"⚠️  Error reading {json_file.name}: {e}")
    
    print(f"✅ Found {len(local_combinations)} total documents locally")
    print(f"   Document types:")
    for doc_type, count in sorted(type_counts.items()):
        print(f"      {doc_type}: {count}")
    print()
    
    return local_combinations

def get_cosmos_combinations():
    """
    Query Cosmos DB for all entra_oid and id combinations.
    Query ALL documents, not just sessions.
    
    Returns:
        Set of tuples (id, entra_oid, type)
    """
    print("🔍 Querying Cosmos DB...")
    
    try:
        # Authenticate
        credential = DefaultAzureCredential()
        client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
        
        # Get database and container
        database = client.get_database_client(DATABASE_NAME)
        container = database.get_container_client(CONTAINER_NAME)
        
        # Query for ALL documents (no type filter)
        query = """
            SELECT c.id, c.entra_oid, c.type
            FROM c
        """
        
        cosmos_combinations = set()
        type_counts = {}
        items = container.query_items(query=query, enable_cross_partition_query=True)
        
        for item in items:
            doc_id = item.get('id')
            entra_oid = item.get('entra_oid')
            doc_type = item.get('type', 'unknown')
            
            # Count by type
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
            if doc_id and entra_oid:
                cosmos_combinations.add((doc_id, entra_oid, doc_type))
        
        print(f"✅ Found {len(cosmos_combinations)} total documents in Cosmos DB")
        print(f"   Document types:")
        for doc_type, count in sorted(type_counts.items()):
            print(f"      {doc_type}: {count}")
        print()
        
        return cosmos_combinations
        
    except Exception as e:
        print(f"❌ Error querying Cosmos DB: {e}")
        import traceback
        traceback.print_exc()
        return set()

def compare_combinations(local_combos, cosmos_combos):
    """
    Compare local and Cosmos DB combinations and report differences.
    
    Args:
        local_combos: Set of local (id, entra_oid, type) tuples
        cosmos_combos: Set of Cosmos DB (id, entra_oid, type) tuples
    """
    print("="*70)
    print("RECONCILIATION RESULTS")
    print("="*70)
    print()
    
    # Find differences
    only_local = local_combos - cosmos_combos
    only_cosmos = cosmos_combos - local_combos
    in_both = local_combos & cosmos_combos
    
    # Summary
    print(f"📊 Summary:")
    print(f"   Local documents:         {len(local_combos)}")
    print(f"   Cosmos DB documents:     {len(cosmos_combos)}")
    print(f"   Matching combinations:   {len(in_both)}")
    print(f"   Only in local files:     {len(only_local)}")
    print(f"   Only in Cosmos DB:       {len(only_cosmos)}")
    print()
    
    # Show differences
    if only_local:
        print(f"⚠️  {len(only_local)} document(s) found ONLY in local files:")
        for i, (doc_id, entra_oid, doc_type) in enumerate(sorted(only_local)[:10], 1):
            print(f"   {i}. id:        {doc_id}")
            print(f"      entra_oid: {entra_oid}")
            print(f"      type:      {doc_type}")
        if len(only_local) > 10:
            print(f"   ... and {len(only_local) - 10} more")
        print()
    
    if only_cosmos:
        print(f"⚠️  {len(only_cosmos)} document(s) found ONLY in Cosmos DB:")
        for i, (doc_id, entra_oid, doc_type) in enumerate(sorted(only_cosmos)[:10], 1):
            print(f"   {i}. id:        {doc_id}")
            print(f"      entra_oid: {entra_oid}")
            print(f"      type:      {doc_type}")
        if len(only_cosmos) > 10:
            print(f"   ... and {len(only_cosmos) - 10} more")
        print()
    
    # Status
    if len(only_local) == 0 and len(only_cosmos) == 0:
        print("✅ Perfect match! All local documents are in Cosmos DB.")
    elif len(only_local) > 0 and len(only_cosmos) == 0:
        print("⚠️  Local files contain documents not yet uploaded to Cosmos DB.")
    elif len(only_local) == 0 and len(only_cosmos) > 0:
        print("⚠️  Cosmos DB contains documents not present in local files.")
    else:
        print("⚠️  Both local and Cosmos DB have unique documents.")
    
    print()
    print("="*70)

def main():
    """Main execution function."""
    
    print("="*70)
    print("Cosmos DB Reconciliation Tool")
    print("="*70)
    print()
    print(f"Local directory:  {LOCAL_JSON_DIR}")
    print(f"Cosmos endpoint:  {COSMOS_ENDPOINT}")
    print(f"Database:         {DATABASE_NAME}")
    print(f"Container:        {CONTAINER_NAME}")
    print()
    
    try:
        # Get local combinations
        local_combos = get_local_combinations()
        
        if not local_combos:
            print("❌ No local session documents found. Exiting.")
            return
        
        # Get Cosmos DB combinations
        cosmos_combos = get_cosmos_combinations()
        
        # Compare
        compare_combinations(local_combos, cosmos_combos)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
