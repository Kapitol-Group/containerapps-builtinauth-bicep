from datetime import datetime, timezone
import re
import os
import asyncio
from dotenv import load_dotenv
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential, ClientSecretCredential
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np
from datetime import datetime, timezone



script_dir = os.path.dirname(os.path.abspath(__file__))
# Dynamically set dotenv path based on AZURE_ENV_NAME
az_env = os.getenv("AZURE_ENV_NAME", "kap-scheduler-prod")
dotenv_path = os.path.abspath(os.path.join(script_dir, f"../.azure/{az_env}/.env"))
print(f"Loading .env file from: {dotenv_path}")
load_dotenv(dotenv_path)


# Print all available environment variables for debugging
print("\n=== Available Environment Variables ===")
for k, v in os.environ.items():
    print(f"{k}={v}")
print("=== End Environment Variables ===\n")

# Authentication setup
# Priority: Service Principal (explicit credentials) > Managed Identity > DefaultAzureCredential
client_id = os.getenv("AZURE_CLIENT_ID")
client_secret = os.getenv("AZURE_CLIENT_SECRET")
tenant_id = os.getenv("AZURE_TENANT_ID")

if client_id and client_secret and tenant_id:
    # Use service principal authentication (works without IMDS endpoint)
    print("Using ClientSecretCredential (Service Principal authentication)")
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )
elif client_id:
    # Use managed identity with explicit client ID
    print("Using DefaultAzureCredential with managed identity client ID")
    credential = DefaultAzureCredential(managed_identity_client_id=client_id)
else:
    # Fall back to default credential chain
    print("Using DefaultAzureCredential")
    credential = DefaultAzureCredential()

AZURE_COSMOSDB_ACCOUNT = os.getenv("AZURE_COSMOSDB_ACCOUNT")
if not AZURE_COSMOSDB_ACCOUNT:
    raise ValueError("AZURE_COSMOSDB_ACCOUNT environment variable is not set")
COSMOS_ENDPOINT = f"https://{AZURE_COSMOSDB_ACCOUNT}.documents.azure.com:443/"
DATABASE_ID = os.environ.get("AZURE_CHAT_HISTORY_DATABASE")
CONTAINER_ID = os.environ.get("AZURE_CHAT_HISTORY_CONTAINER_KAPCOACH")
FIELD_NAME = "question"

async def fetch_field_values():
    """Fetch chat history items from Cosmos DB."""
    async with CosmosClient(COSMOS_ENDPOINT, credential) as client:
        database = client.get_database_client(DATABASE_ID)
        container = database.get_container_client(CONTAINER_ID)
        # Fetch id, session_id, entra_oid, _ts, FIELD_NAME and date (so we can preserve source date when present)
        # Include items that have either the FIELD_NAME (question) or a date field present
        query = f"SELECT c.id, c.session_id, c.entra_oid, c._ts, c.{FIELD_NAME}, c.date FROM c WHERE (IS_DEFINED(c.{FIELD_NAME}) OR IS_DEFINED(c.date)) AND IS_DEFINED(c.entra_oid) AND NOT IS_NULL(c.entra_oid)"
        items = container.query_items(query=query)
        result = [item async for item in items if (FIELD_NAME in item or 'date' in item) and 'entra_oid' in item and item['entra_oid']]
        print(f"Fetched {len(result)} items from {CONTAINER_ID}")
        return result

def classify_texts(texts):
    """Classify texts into predefined categories using semantic similarity."""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    categories = {
        "Habits & Styles": "Leadership style, building effective habits, breaking bad habits, routines, lifestyle changes, consistency, discipline, prioritise, first things first, .",
        "Giving Feedback": "Providing constructive feedback, delivering criticism, positive feedback, improvement suggestions.",
        "Difficult Conversations": "Handling conflict, addressing issues, managing emotions, resolving disagreements, tough talks.",
        "Productivity": "Improving focus, time management, meeting deadlines, working efficiently, Prioritise, optimise performance, effectiveness, personal efficiency.",
        "Personal & Career Growth": "Getting promoted, goals, mission, improving skills, mentorship, advancing in your career.",
        "Wellbeing": "Managing stress, work-life balance, mental health, self-care, relaxation techniques, mindfulness.",
        "Other": "General topics not covered by other categories. For example: PMO requests, new business, finance, estimation"
    }
    category_names = list(categories.keys())
    category_embeddings = model.encode(list(categories.values()))

    def classify(text):
        text_embedding = model.encode([text])
        similarities = cosine_similarity(text_embedding, category_embeddings)[0]
        return category_names[np.argmax(similarities)]

    df = pd.DataFrame(texts)
    # Ensure FIELD_NAME exists on all rows; fill missing with empty string
    if FIELD_NAME not in df.columns:
        df[FIELD_NAME] = ""
    df[FIELD_NAME] = df[FIELD_NAME].fillna("")

    # Classify only non-empty texts; for empty texts set topic to None
    def classify_safe(text):
        if not text:
            return None
        return classify(text)

    df['topic'] = df[FIELD_NAME].apply(classify_safe)
    # Set date field: use source date if present, else convert _ts
    def get_date(row):
        date_val = row.get('date')
        # Use date field only if it exists and is not blank/null
        if date_val is not None and str(date_val).strip() not in ('', 'None', 'null'):
            # Always convert to yyyy-mm-dd format
            dt = None
            try:
                dt = datetime.strptime(str(date_val), "%Y-%m-%d")
            except Exception:
                try:
                    dt = datetime.strptime(str(date_val), "%d/%m/%Y")
                except Exception:
                    # Use pandas to coerce a wide range of formats; returns NaT on failure
                    try:
                        dt = pd.to_datetime(str(date_val), utc=True)
                    except Exception:
                        dt = None
            # If pandas returned NaT or dt is None, fall back to using _ts below
            if dt is not None and not pd.isna(dt):
                # Normalize pandas Timestamp to python datetime if necessary
                if isinstance(dt, pd.Timestamp):
                    try:
                        # convert to UTC then to python datetime
                        if dt.tzinfo is not None or getattr(dt, 'tz', None) is not None:
                            dt = dt.tz_convert('UTC').to_pydatetime()
                        else:
                            dt = dt.to_pydatetime()
                    except Exception:
                        dt = dt.to_pydatetime()
                return dt.strftime('%Y-%m-%d')
        # Otherwise, use _ts
        dt = datetime.fromtimestamp(row['_ts'], tz=timezone.utc)
        return dt.strftime('%Y-%m-%d')
    df['date'] = df.apply(get_date, axis=1)
    # Debug: print all dates being processed
    print("\n=== Dates being processed ===")
    print(df['date'].value_counts().sort_index())
    print("=== End Dates ===\n")
    return df


# Function to write DataFrame to a different Cosmos DB container

async def write_df_to_cosmos(df, database_id, container_id):
    """
    Write DataFrame to Cosmos DB container with robust error handling.
    Uses hierarchical partition key: [entra_oid, session_id]
    """
    if df.empty:
        print("DataFrame is empty, nothing to write.")
        return
    
    async with CosmosClient(COSMOS_ENDPOINT, credential) as client:
        database = client.get_database_client(database_id)
        container = database.get_container_client(container_id)
        
        successful_upserts = 0
        skipped_existing = 0
        failed_upserts = 0
        
        for rec in df.to_dict(orient="records"):
            # Ensure required fields exist
            if not all([rec.get("id"), rec.get("session_id"), rec.get("_ts"), rec.get("entra_oid")]):
                print(f"Skipping record due to missing required fields: {rec}")
                failed_upserts += 1
                continue
            
            # Validate partition key values are not empty
            if not rec.get("entra_oid") or not rec.get("session_id"):
                print(f"Skipping record with empty partition key values: id={rec.get('id')}")
                failed_upserts += 1
                continue
                
            # Check if a document with the same combination exists
            query = (
                "SELECT TOP 1 c.id FROM c WHERE c.id = @id AND c.session_id = @session_id "
                "AND c._ts = @ts AND c.entra_oid = @entra_oid"
            )
            params = [
                {"name": "@id", "value": rec["id"]},
                {"name": "@session_id", "value": rec["session_id"]},
                {"name": "@ts", "value": rec["_ts"]},
                {"name": "@entra_oid", "value": rec["entra_oid"]},
            ]
            
            existing = [item async for item in container.query_items(query=query, parameters=params)]

            if existing:
                print(f"Skipping existing item: id={rec['id']}, session_id={rec['session_id']}, entra_oid={rec['entra_oid']}, _ts={rec['_ts']}")
                skipped_existing += 1
                continue
                
            try:
                # The async SDK automatically extracts the partition key from the item
                # based on the container's partition key definition ([entra_oid, session_id])
                # Just pass the item - no partition_key parameter needed!
                await container.upsert_item(rec)
                print(f"Successfully upserted item {rec['id']} into {container_id}")
                successful_upserts += 1
            except Exception as e:
                print(f"Failed to upsert item {rec.get('id', 'unknown')}: {e}")
                print(f"Record details: entra_oid={rec.get('entra_oid')}, session_id={rec.get('session_id')}")
                failed_upserts += 1
        
        # Print summary
        print(f"\n=== Write Summary ===")
        print(f"Total records processed: {len(df)}")
        print(f"Successful upserts: {successful_upserts}")
        print(f"Skipped (already exist): {skipped_existing}")
        print(f"Failed: {failed_upserts}")
        print(f"====================\n")

async def main():
    """Main function to fetch, classify, and write topic classifications."""
    print(f"\n{'='*60}")
    print(f"Topic Classification Job Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")
    
    try:
        # Fetch data
        texts = await fetch_field_values()
        
        if not texts:
            print(f"No data found for field '{FIELD_NAME}' in collection '{CONTAINER_ID}'.")
            print("Job completed with no data to process.\n")
            return
        
        # Classify texts
        print(f"Classifying {len(texts)} text items...")
        df = classify_texts(texts)
        print(f"Classification complete. Sample data:")
        print(df.head())
        print(f"\nColumns: {df.columns.tolist()}\n")
        
        # Write to target container
        target_container = os.getenv("AZURE_TOPIC_HISTORY_CONTAINER_KAPCOACH")
        if not target_container:
            raise ValueError("AZURE_TOPIC_HISTORY_CONTAINER_KAPCOACH environment variable is not set")
        
        print(f"Writing classified data to container: {target_container}")
        await write_df_to_cosmos(df, DATABASE_ID, target_container)
        
        print(f"\n{'='*60}")
        print(f"Topic Classification Job Completed: {datetime.now(timezone.utc).isoformat()}")
        print(f"{'='*60}\n")
        
    finally:
        # Ensure credential is properly closed
        await credential.close()

if __name__ == "__main__":
    asyncio.run(main())