"""
Export data from Application Insights and import into Cosmos DB.
Uses Azure Monitor Query API to fetch data and writes to Cosmos DB.
"""
import os
from datetime import datetime, timedelta
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient
from azure.cosmos import CosmosClient
import json

# Configuration
APP_INSIGHTS_WORKSPACE_ID = "YOUR_WORKSPACE_ID"  # Get from Application Insights > API Access
COSMOSDB_ACCOUNT = "cosmos-ilzg75heuh4wm"
COSMOSDB_ENDPOINT = f"https://{COSMOSDB_ACCOUNT}.documents.azure.com:443/"
DATABASE_NAME = "chat-database"
CONTAINER_NAME = "chat-history-kapcoach"  # Target container

# KQL Query - Customize this based on what you want to extract
# Example: Extract custom events, traces, or requests
KQL_QUERY = """
requests
| where timestamp > ago(7d)
| project 
    timestamp,
    name,
    url,
    success,
    resultCode,
    duration,
    performanceBucket,
    customDimensions
| limit 1000
"""

# Alternative queries you might want:
# For custom events:
# customEvents | where timestamp > ago(7d) | project timestamp, name, customDimensions
# 
# For traces/logs:
# traces | where timestamp > ago(7d) | project timestamp, message, severityLevel, customDimensions
#
# For exceptions:
# exceptions | where timestamp > ago(7d) | project timestamp, type, outerMessage, problemId, customDimensions


def fetch_appinsights_data(workspace_id, query, timespan=None):
    """
    Fetch data from Application Insights using KQL query.
    
    Args:
        workspace_id: Application Insights workspace ID
        query: KQL query string
        timespan: Optional timespan (e.g., timedelta(days=7))
        
    Returns:
        List of rows from the query result
    """
    print(f"🔍 Querying Application Insights...")
    print(f"Query: {query[:100]}...")
    
    credential = DefaultAzureCredential()
    client = LogsQueryClient(credential)
    
    # Default to last 7 days if no timespan specified
    if timespan is None:
        timespan = timedelta(days=7)
    
    response = client.query_workspace(
        workspace_id=workspace_id,
        query=query,
        timespan=timespan
    )
    
    # Convert to list of dictionaries
    rows = []
    if response.tables:
        table = response.tables[0]
        for row in table.rows:
            row_dict = {}
            for i, column in enumerate(table.columns):
                value = row[i]
                # Convert datetime to ISO string
                if isinstance(value, datetime):
                    value = value.isoformat()
                row_dict[column.name] = value
            rows.append(row_dict)
    
    print(f"✅ Retrieved {len(rows)} records from Application Insights")
    return rows


def upload_to_cosmos(data, database_name, container_name):
    """
    Upload data to Cosmos DB container.
    
    Args:
        data: List of dictionaries to upload
        database_name: Cosmos DB database name
        container_name: Cosmos DB container name
    """
    print(f"\n📤 Uploading to Cosmos DB...")
    print(f"Database: {database_name}")
    print(f"Container: {container_name}")
    
    credential = DefaultAzureCredential()
    client = CosmosClient(COSMOSDB_ENDPOINT, credential=credential)
    
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)
    
    success_count = 0
    error_count = 0
    
    for i, item in enumerate(data, 1):
        try:
            # Add an id field if not present (required by Cosmos DB)
            if 'id' not in item:
                # Generate ID from timestamp and index
                timestamp_str = item.get('timestamp', datetime.now().isoformat())
                item['id'] = f"appinsights-{timestamp_str}-{i}"
            
            # Add partition key if needed (adjust based on your container's partition key)
            # If your container uses a specific partition key, ensure it's in the item
            
            container.upsert_item(item)
            success_count += 1
            
            if i % 100 == 0:
                print(f"  Uploaded {i}/{len(data)} records...")
                
        except Exception as e:
            error_count += 1
            print(f"  ❌ Error uploading record {i}: {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"📊 Upload Summary:")
    print(f"   Success: {success_count}")
    print(f"   Errors: {error_count}")
    print(f"   Total: {len(data)}")
    print(f"{'='*60}")


def save_to_json(data, filename=None):
    """
    Save data to JSON file as backup.
    
    Args:
        data: List of dictionaries to save
        filename: Optional filename (auto-generated if not provided)
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"appinsights_export_{timestamp}.json"
    
    filepath = os.path.join("data", filename)
    os.makedirs("data", exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved backup to: {filepath}")


def main():
    """Main execution function."""
    
    print("="*60)
    print("Application Insights to Cosmos DB Exporter")
    print("="*60)
    print()
    
    # Validate configuration
    if APP_INSIGHTS_WORKSPACE_ID == "YOUR_WORKSPACE_ID":
        print("⚠️  Please update APP_INSIGHTS_WORKSPACE_ID in the script")
        print("   Get it from: Azure Portal > Application Insights > API Access")
        return
    
    try:
        # Step 1: Fetch data from Application Insights
        data = fetch_appinsights_data(
            workspace_id=APP_INSIGHTS_WORKSPACE_ID,
            query=KQL_QUERY
        )
        
        if not data:
            print("⚠️  No data returned from query")
            return
        
        # Step 2: Save to JSON as backup
        save_to_json(data)
        
        # Step 3: Upload to Cosmos DB
        upload_to_cosmos(data, DATABASE_NAME, CONTAINER_NAME)
        
        print("\n✅ Export complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
