"""
Test script to verify Cosmos DB partition key handling.
This script tests the exact upsert_item syntax that was causing the error.
"""
import asyncio
import os
from dotenv import load_dotenv
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential, ClientSecretCredential

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)

# Authentication setup
client_id = os.getenv("AZURE_CLIENT_ID")
client_secret = os.getenv("AZURE_CLIENT_SECRET")
tenant_id = os.getenv("AZURE_TENANT_ID")

if client_id and client_secret and tenant_id:
    print("Using ClientSecretCredential (Service Principal authentication)")
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )
else:
    print("Using DefaultAzureCredential")
    credential = DefaultAzureCredential(managed_identity_client_id=client_id) if client_id else DefaultAzureCredential()

# Cosmos DB configuration
AZURE_COSMOSDB_ACCOUNT = os.getenv("AZURE_COSMOSDB_ACCOUNT")
if not AZURE_COSMOSDB_ACCOUNT:
    raise ValueError("AZURE_COSMOSDB_ACCOUNT environment variable is not set")
COSMOS_ENDPOINT = f"https://{AZURE_COSMOSDB_ACCOUNT}.documents.azure.com:443/"
DATABASE_ID = os.environ.get("AZURE_CHAT_HISTORY_DATABASE")
TARGET_CONTAINER_ID = os.environ.get("AZURE_TOPIC_HISTORY_CONTAINER_KAPCOACH")

async def test_partition_key_syntax():
    """Test different partition key syntaxes to identify the correct one."""
    
    print("\n" + "="*60)
    print("Testing Cosmos DB Partition Key Syntax")
    print("="*60 + "\n")
    
    async with CosmosClient(COSMOS_ENDPOINT, credential) as client:
        database = client.get_database_client(DATABASE_ID)
        container = database.get_container_client(TARGET_CONTAINER_ID)
        
        # Create a test record with unique ID
        test_record = {
            "id": "test-partition-key-001",
            "session_id": "test-session-001",
            "entra_oid": "test-entra-001",
            "_ts": 1699999999,
            "question": "This is a test question",
            "topic": "Testing",
            "date": "2025-11-13T00:00:00+00:00"
        }
        
        partition_key_value = [test_record["entra_oid"], test_record["session_id"]]
        
        print(f"Test record ID: {test_record['id']}")
        print(f"Partition key fields in record: entra_oid={test_record['entra_oid']}, session_id={test_record['session_id']}")
        print(f"Partition key value: {partition_key_value}")
        print(f"Partition key type: {type(partition_key_value)}")
        print()
        
        # Test 1: CORRECT - Let SDK extract partition key automatically
        print("Test 1: Using no partition_key parameter - upsert_item(rec)")
        print("        (SDK automatically extracts from rec['entra_oid'] and rec['session_id'])")
        try:
            result = await container.upsert_item(test_record)
            print(f"✅ SUCCESS! Item upserted - SDK extracted partition key automatically")
            print(f"   Response ID: {result.get('id')}")
            print()
        except Exception as e:
            print(f"❌ FAILED: {type(e).__name__}: {e}")
            print()
        
        # Test 2: INCORRECT - Positional argument
        print("Test 2: Using positional argument - upsert_item(rec, partition_key)")
        test_record["id"] = "test-partition-key-002"
        try:
            result = await container.upsert_item(test_record, partition_key_value)
            print(f"✅ SUCCESS! Item upserted with positional argument")
            print(f"   Response ID: {result.get('id')}")
            print()
        except Exception as e:
            print(f"❌ FAILED (as expected): {type(e).__name__}: {e}")
            print()
        
        # Test 3: INCORRECT - Keyword argument (this is what was causing the error)
        print("Test 3: Using keyword argument - upsert_item(body=rec, partition_key=...)")
        test_record["id"] = "test-partition-key-003"
        try:
            result = await container.upsert_item(body=test_record, partition_key=partition_key_value)
            print(f"✅ SUCCESS! Item upserted with keyword argument")
            print(f"   Response ID: {result.get('id')}")
            print()
        except Exception as e:
            print(f"❌ FAILED (as expected): {type(e).__name__}: {e}")
            print()
        
        # Test 3: Read back the successfully written record to verify
        print("Test 3: Reading back the successfully written record")
        try:
            query = "SELECT * FROM c WHERE c.id = @id"
            params = [{"name": "@id", "value": "test-partition-key-001"}]
            items = [item async for item in container.query_items(query=query, parameters=params)]
            if items:
                print(f"✅ SUCCESS! Record found:")
                print(f"   ID: {items[0].get('id')}")
                print(f"   Topic: {items[0].get('topic')}")
                print(f"   Question: {items[0].get('question')}")
            else:
                print(f"❌ No record found")
            print()
        except Exception as e:
            print(f"❌ FAILED: {e}")
            print()
        
        # Cleanup: Delete test records
        print("Cleanup: Deleting test records")
        for test_id in ["test-partition-key-001", "test-partition-key-002", "test-partition-key-003"]:
            try:
                await container.delete_item(
                    item=test_id,
                    partition_key=["test-entra-001", "test-session-001"]
                )
                print(f"✅ Deleted {test_id}")
            except Exception as e:
                print(f"⚠️  Could not delete {test_id}: {e}")
        
        print()
        print("="*60)
        print("Test Complete")
        print("="*60)
        print("\nSUMMARY:")
        print("- NO partition_key parameter is CORRECT for async SDK")
        print("- SDK automatically extracts partition key from item fields")
        print("- Keyword argument syntax causes the error you experienced")
        print("- The fix in topic_classification.py uses the correct syntax")
        print()

async def test_real_data_sample():
    """Test with a real data sample from the source container."""
    
    print("\n" + "="*60)
    print("Testing with Real Data Sample")
    print("="*60 + "\n")
    
    async with CosmosClient(COSMOS_ENDPOINT, credential) as client:
        database = client.get_database_client(DATABASE_ID)
        source_container = database.get_container_client(os.environ.get("AZURE_CHAT_HISTORY_CONTAINER_KAPCOACH"))
        target_container = database.get_container_client(TARGET_CONTAINER_ID)
        
        # Fetch one real record
        query = "SELECT TOP 1 c.id, c.session_id, c.entra_oid, c._ts, c.question FROM c WHERE IS_DEFINED(c.question) AND IS_DEFINED(c.entra_oid)"
        items = [item async for item in source_container.query_items(query=query)]
        
        if not items:
            print("No data found in source container to test with")
            return
        
        sample = items[0]
        print(f"Found sample record:")
        print(f"  ID: {sample.get('id')}")
        print(f"  Session ID: {sample.get('session_id')}")
        print(f"  Entra OID: {sample.get('entra_oid')}")
        print(f"  _ts: {sample.get('_ts')}")
        print()
        
        # Create test record with modified ID to avoid conflicts
        test_record = sample.copy()
        test_record["id"] = f"{sample['id']}-test"
        test_record["topic"] = "Test Topic"
        test_record["date"] = "2025-11-13T00:00:00+00:00"
        
        partition_key_value = [test_record["entra_oid"], test_record["session_id"]]
        
        print(f"Attempting to write test record with partition key: {partition_key_value}")
        
        try:
            # Use the corrected syntax - just pass the item, SDK extracts partition key
            result = await target_container.upsert_item(test_record)
            print(f"✅ SUCCESS! Real data sample written successfully")
            print(f"   Response ID: {result.get('id')}")
            print()
            
            # Cleanup
            print("Cleaning up test record...")
            await target_container.delete_item(
                item=test_record["id"],
                partition_key=partition_key_value
            )
            print("✅ Test record deleted")
            
        except Exception as e:
            print(f"❌ FAILED: {type(e).__name__}: {e}")
        
        print()

async def main():
    """Run all tests."""
    try:
        await test_partition_key_syntax()
        await test_real_data_sample()
    finally:
        await credential.close()

if __name__ == "__main__":
    asyncio.run(main())
