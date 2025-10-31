from datetime import datetime, timezone
import os
import asyncio
from dotenv import load_dotenv
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

credential = DefaultAzureCredential()
AZURE_COSMOSDB_ACCOUNT = os.getenv("AZURE_COSMOSDB_ACCOUNT")
COSMOS_ENDPOINT = f"https://{AZURE_COSMOSDB_ACCOUNT}.documents.azure.com:443/"
DATABASE_ID = os.environ.get("AZURE_CHAT_HISTORY_DATABASE")
CONTAINER_ID = os.environ.get("AZURE_CHAT_HISTORY_CONTAINER_KAPCOACH")
FIELD_NAME = "question"

async def fetch_field_values():
    async with CosmosClient(COSMOS_ENDPOINT, credential) as client:
        database = client.get_database_client(DATABASE_ID)
        container = database.get_container_client(CONTAINER_ID)
        # Fetch id, session_id, and FIELD_NAME
        query = f"SELECT c.id, c.session_id, c._ts, c.{FIELD_NAME} FROM c WHERE IS_DEFINED(c.{FIELD_NAME}) AND NOT IS_NULL(c.{FIELD_NAME})"
        items = container.query_items(query=query)
        result = [item async for item in items if FIELD_NAME in item]
        return result

def classify_texts(texts):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    categories = {
        "Habits & Styles": "Leadership style, building effective habits, breaking bad habits, routines, lifestyle changes, consistency, discipline, prioritise, first things first, .",
        "Giving Feedback": "Providing constructive feedback, delivering criticism, positive feedback, improvement suggestions.",
        "Difficult Conversations": "Handling conflict, addressing issues, managing emotions, resolving disagreements, tough talks.",
        "Productivity": "Improving focus, time management, meeting deadlines, working efficiently, Prioritise, optimise performance, effectiveness, personal efficiency.",
        "Personal & Career Growth": "Getting promoted, goals, mission, improving skills, mentorship, advancing in your career.",
        "Wellbeing": "Managing stress, work-life balance, mental health, self-care, relaxation techniques, mindfulness.",
    }
    category_names = list(categories.keys())
    category_embeddings = model.encode(list(categories.values()))

    def classify(text):
        text_embedding = model.encode([text])
        similarities = cosine_similarity(text_embedding, category_embeddings)[0]
        return category_names[np.argmax(similarities)]

    df = pd.DataFrame(texts)
    df['topic'] = df[FIELD_NAME].apply(classify)
    df['date'] = df.apply(lambda x: datetime.fromtimestamp(x['_ts'], tz=timezone.utc), axis=1)
    df['date'] = df['date'].astype('str')
    return df


# Function to write DataFrame to a different Cosmos DB container

async def write_df_to_cosmos(df, database_id, container_id):
    async with CosmosClient(COSMOS_ENDPOINT, credential) as client:
        database = client.get_database_client(database_id)
        container = database.get_container_client(container_id)
        for rec in df.to_dict(orient="records"):
            # Ensure required fields exist
            if not all([rec.get("id"), rec.get("session_id"), rec.get("_ts")]):
                print(f"Skipping record due to missing id, session_id, or _ts: {rec}")
                continue
            # Check if a document with the same combination exists
            query = (
                "SELECT TOP 1 c.id FROM c WHERE c.id = @id AND c.session_id = @session_id "
                "AND c._ts = @ts"
            )
            params = [
                {"name": "@id", "value": rec["id"]},
                {"name": "@session_id", "value": rec["session_id"]},
                {"name": "@ts", "value": rec["_ts"]},
                {"name": "@date", "value": rec["date"]},
            ]
            existing = [item async for item in container.query_items(query=query, parameters=params)]

            print(existing)

            if existing:
                print(f"Skipping existing item: id={rec['id']}, session_id={rec['session_id']}, _ts={rec['_ts']}")
                continue
            try:
                await container.upsert_item(rec)
                print(f"Upserted item {rec['id']} into {container_id}")
            except Exception as e:
                print(f"Failed to upsert item {rec.get('id', 'unknown')}: {e}")

async def main():
    texts = await fetch_field_values()
    if texts:
        df = classify_texts(texts)
        print(df)
        print(df.columns)
        # Write to a different container (e.g., "classified_items")
        target_container = os.getenv("AZURE_TOPIC_HISTORY_CONTAINER_KAPCOACH")
        await write_df_to_cosmos(df, DATABASE_ID, target_container)
    else:
        print(f"No data found for field '{FIELD_NAME}' in collection '{CONTAINER_ID}'.")
    await credential.close()

if __name__ == "__main__":
    asyncio.run(main())