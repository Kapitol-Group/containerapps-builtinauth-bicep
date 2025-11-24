import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential, ClientSecretCredential

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '../.azure/kap-scheduler-prod/.env')
load_dotenv(dotenv_path)

client_id = os.getenv("SERVICE_PRINCIPAL_CLIENT_ID")
client_secret = os.getenv("SERVICE_PRINCIPAL_CLIENT_SECRET")
tenant_id = os.getenv("AZURE_TENANT_ID")

if client_id and client_secret and tenant_id:
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )
else:
    credential = DefaultAzureCredential()

AZURE_COSMOSDB_ACCOUNT = os.getenv("AZURE_COSMOSDB_ACCOUNT")
COSMOS_ENDPOINT = f"https://{AZURE_COSMOSDB_ACCOUNT}.documents.azure.com:443/"
DATABASE_ID = os.environ.get("AZURE_CHAT_HISTORY_DATABASE")
CONTAINERS = [
    os.environ.get("AZURE_CHAT_HISTORY_CONTAINER_KAPCOACH"),
    os.environ.get("AZURE_TOPIC_HISTORY_CONTAINER_KAPCOACH")
]

def convert_date_format(date_str):
    try:
        dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"⚠️  Could not parse date '{date_str}': {e}")
        return None

async def preview_update_dates_in_container(container_name):
    if not container_name:
        print("⚠️  Skipping undefined container")
        return
    print(f"\n--- Previewing container: {container_name} ---\n")
    async with CosmosClient(COSMOS_ENDPOINT, credential) as client:
        database = client.get_database_client(DATABASE_ID)
        container = database.get_container_client(container_name)
        # Minimal test upsert
        print("\n--- Minimal test upsert ---")
        test_item = {
            "id": "test-id",
            "entra_oid": "test-entra-oid",
            "date": "22/10/2025"
        }
        try:
            await container.upsert_item(test_item, partition_key="test-entra-oid")
            print("✅ Minimal test upsert succeeded.")
        except Exception as e:
            print(f"❌ Minimal test upsert failed: {e}")
        print("--- End minimal test upsert ---\n")

        query = "SELECT * FROM c WHERE IS_DEFINED(c.date) AND NOT IS_NULL(c.date)"
        async for item in container.query_items(query=query):
            date_value = item.get('date')
            entra_oid = item.get('entra_oid')
            print(f"entra_oid in doc: {entra_oid}, id: {item.get('id')}, partition_key arg: {entra_oid.strip() if isinstance(entra_oid, str) else entra_oid}")
            if not entra_oid or not isinstance(entra_oid, str) or not entra_oid.strip():
                print(f"❌ Skipping id={item.get('id')} due to missing or empty entra_oid")
                continue
            if isinstance(date_value, str) and '/' in date_value:
                new_date = convert_date_format(date_value)
                if new_date and new_date != date_value:
                    print(f"Would update id={item.get('id')} : '{date_value}' → '{new_date}'")
                    item['date'] = new_date
                    try:
                        await container.upsert_item(item, partition_key=entra_oid.strip())
                        print(f"✅ Upsert succeeded for id={item.get('id')}")
                    except Exception as e:
                        print(f"❌ Upsert failed for id={item.get('id')}: {e}")
                else:
                    print(f"Skipping id={item.get('id')} : '{date_value}' (no change or invalid)")

async def main():
    for container_name in CONTAINERS:
        await preview_update_dates_in_container(container_name)
    await credential.close()

if __name__ == "__main__":
    asyncio.run(main())