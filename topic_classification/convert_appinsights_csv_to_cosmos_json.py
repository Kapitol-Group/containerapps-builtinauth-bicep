"""
Convert Application Insights CSV export to Cosmos DB JSON format.
Transforms chat logs into session and message_pair documents.
"""
import csv
import json
import os
import uuid
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# Configuration
CSV_FILE = Path(__file__).parent.parent / "data" / "query_data.csv"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "converted_jsons"

def parse_custom_dimensions(custom_dimensions_str):
    """
    Parse the customDimensions JSON string.
    
    Args:
        custom_dimensions_str: JSON string from CSV
        
    Returns:
        Dictionary of custom dimensions
    """
    try:
        return json.loads(custom_dimensions_str)
    except:
        return {}

def extract_question_from_prompts(custom_dims):
    """
    Extract ALL user questions from the prompt chain.
    Returns a list of all user questions found in the conversation.
    
    Args:
        custom_dims: Dictionary of custom dimensions
        
    Returns:
        List of user question strings (can be multiple in multi-turn conversations)
    """
    questions = []
    
    # Check up to 20 prompts for multi-turn conversations
    for i in range(20):
        role_key = f"gen_ai.prompt.{i}.role"
        content_key = f"gen_ai.prompt.{i}.content"
        
        if role_key in custom_dims and custom_dims[role_key] == "user":
            question = custom_dims.get(content_key, "").strip()
            
            # Skip system instructions or empty content
            if question and not question.startswith("Generate search query"):
                # Remove "User memory:" and "Sources:" sections if present
                if "\n\nUser memory:" in question:
                    question = question.split("\n\nUser memory:")[0].strip()
                if "\n\nSources:" in question:
                    question = question.split("\n\nSources:")[0].strip()
                
                if question:  # Only add if not empty after cleaning
                    questions.append(question)
    
    return questions

def extract_response(custom_dims):
    """
    Extract the AI's response from completion data.
    
    Args:
        custom_dims: Dictionary of custom dimensions
        
    Returns:
        The assistant's response string
    """
    return custom_dims.get("gen_ai.completion.0.content", "")

def parse_timestamp(timestamp_str):
    """
    Convert CSV timestamp to Unix timestamp (milliseconds).
    Format: "11/11/2025, 20:48:43.814" (dd/mm/yyyy)
    
    Args:
        timestamp_str: Timestamp string from CSV
        
    Returns:
        Unix timestamp in milliseconds
    """
    try:
        # Parse the timestamp (day/month/year format)
        dt = datetime.strptime(timestamp_str, "%d/%m/%Y, %H:%M:%S.%f")
        # Convert to Unix timestamp in milliseconds
        return int(dt.timestamp() * 1000)
    except Exception as e:
        print(f"⚠️  Warning: Failed to parse timestamp '{timestamp_str}': {e}")
        # Fallback to current time
        return int(datetime.now().timestamp() * 1000)

def format_session_id(operation_id):
    """
    Format operation_Id to UUID format with hyphens.
    Converts: 23c230e84f0d6dfb7345138d9c333d67
    To: 23c230e8-4f0d-6dfb-7345-138d9c333d67
    
    Args:
        operation_id: The operation ID from Application Insights
        
    Returns:
        Formatted UUID string
    """
    # Remove any existing hyphens and spaces
    clean_id = operation_id.replace('-', '').replace(' ', '').lower()
    
    # Check if it's 32 characters (valid for UUID conversion)
    if len(clean_id) == 32:
        # Format as UUID: 8-4-4-4-12
        return f"{clean_id[0:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:32]}"
    else:
        # If not standard length, generate a new UUID
        return str(uuid.uuid4())

def generate_session_title(first_question):
    """
    Generate a session title from the first question (first 50 chars).
    
    Args:
        first_question: The first question in the session
        
    Returns:
        A title string
    """
    if not first_question:
        return "Untitled Session"
    
    # Take first 50 characters, clean up
    title = first_question[:50].strip()
    if len(first_question) > 50:
        title += "..."
    
    return title

def create_session_document(session_id, first_question, timestamp, entra_oid):
    """
    Create a session document (type: session).
    
    Args:
        session_id: The session ID
        first_question: First question to generate title
        timestamp: Unix timestamp in milliseconds
        entra_oid: Unique Entra OID for this session
        
    Returns:
        Session document dictionary
    """
    # Convert timestamp to date string (yyyy-mm-dd format)
    dt = datetime.fromtimestamp(timestamp / 1000)
    date_str = dt.strftime("%Y-%m-%d")
    
    return {
        "id": session_id,
        "version": "cosmosdb-v2",
        "session_id": session_id,
        "entra_oid": entra_oid,
        "type": "session",
        "title": generate_session_title(first_question),
        "timestamp": timestamp,
        "date": date_str,
        "_rid": "",  # Cosmos DB will generate this
        "_self": "",  # Cosmos DB will generate this
        "_etag": "",  # Cosmos DB will generate this
        "_attachments": "attachments/",
        "_ts": int(timestamp / 1000)  # Convert to seconds (Unix timestamp)
    }

def create_message_pair_document(session_id, message_index, question, response, timestamp, entra_oid):
    """
    Create a message_pair document.
    
    Args:
        session_id: The session ID
        message_index: Index of message in session (0, 1, 2...)
        question: User's question
        response: AI's response
        timestamp: Unix timestamp in milliseconds
        entra_oid: Unique Entra OID for this session
        
    Returns:
        Message pair document dictionary
    """
    # Convert timestamp to date string (yyyy-mm-dd format)
    dt = datetime.fromtimestamp(timestamp / 1000)
    date_str = dt.strftime("%Y-%m-%d")
    
    return {
        "id": f"{session_id}-{message_index}",
        "version": "cosmosdb-v2",
        "session_id": session_id,
        "entra_oid": entra_oid,
        "type": "message_pair",
        "question": question,
        "date": date_str,
        "response": {
            "delta": {
                "role": "assistant"
            },
            "context": {
                "data_points": {
                    "text": []
                },
                "thoughts": [],
                "web_search_used": False,
                "web_search_info": None,
                "training_video_info": None,
                "is_training_query": False,
                "conversation_id": session_id,
                "scope_filters": {},
                "search_scopes": ["general"],
                "scoped_conversation": True
            },
            "session_state": session_id,
            "message": {
                "content": response,
                "role": "assistant"
            }
        },
        "_rid": "",  # Cosmos DB will generate this
        "_self": "",  # Cosmos DB will generate this
        "_etag": "",  # Cosmos DB will generate this
        "_attachments": "attachments/",
        "_ts": int(timestamp / 1000)  # Convert to seconds (Unix timestamp)
    }

def process_csv(csv_file):
    """
    Process the CSV file and group messages by session.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        Dictionary of sessions with their messages
    """
    print(f"📂 Reading CSV file: {csv_file}\n")
    
    sessions = defaultdict(list)
    skipped_count = 0
    processed_count = 0
    multi_turn_count = 0
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
        reader = csv.DictReader(f)
        
        for row in reader:
            # Extract session ID (operation_Id is used as session_id)
            operation_id = row.get('operation_Id', '').strip()
            
            if not operation_id:
                skipped_count += 1
                continue
            
            # Format session_id to UUID format
            session_id = format_session_id(operation_id)
            
            # Parse custom dimensions
            custom_dims = parse_custom_dimensions(row.get('customDimensions', '{}'))
            
            # Extract all questions and response
            questions = extract_question_from_prompts(custom_dims)
            response = extract_response(custom_dims)
            
            if not questions or not response:
                skipped_count += 1
                continue
            
            # Parse timestamp - try both with and without quotes
            timestamp_str = row.get('timestamp [UTC]', '') or row.get('"timestamp [UTC]"', '')
            timestamp = parse_timestamp(timestamp_str.strip())
            
            # If multiple questions found, this is a multi-turn conversation
            if len(questions) > 1:
                multi_turn_count += 1
            
            # Add each question as a separate message to the session
            # Create a message pair for each question in the conversation
            for i, question in enumerate(questions):
                # For multi-turn, only the last question gets the response
                # Earlier questions get empty response (they were part of context building)
                msg_response = response if i == len(questions) - 1 else None
                
                sessions[session_id].append({
                    'question': question,
                    'response': msg_response,
                    'timestamp': timestamp + (i * 1000),  # Add milliseconds to ensure unique timestamps
                    'question_index': i  # Track which question this is (0, 1, 2, etc.)
                })
            
            processed_count += len(questions)
    
    print(f"✅ Processed {processed_count} message pairs")
    print(f"📝 Found {multi_turn_count} multi-turn conversations")
    print(f"⏭️  Skipped {skipped_count} rows (missing data)")
    print(f"📊 Found {len(sessions)} unique sessions\n")
    
    return sessions

def save_session_documents(sessions, output_dir):
    """
    Save session and message_pair documents as JSON files.
    
    Args:
        sessions: Dictionary of sessions with messages
        output_dir: Directory to save JSON files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"💾 Saving JSON files to: {output_dir}\n")
    
    total_files = 0
    
    for session_id, messages in sessions.items():
        # Sort messages by timestamp
        messages.sort(key=lambda x: x['timestamp'])
        
        # Generate a unique entra_oid for this session
        entra_oid = str(uuid.uuid4())
        
        # Create session document
        session_doc = create_session_document(
            session_id,
            messages[0]['question'],
            messages[0]['timestamp'],
            entra_oid
        )
        
        # Save session document
        session_file = output_dir / f"{session_id}.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_doc, f, indent=2, ensure_ascii=False)
        print(f"✅ {session_id}.json (session)")
        total_files += 1
        
        # Create and save message_pair documents
        for i, message in enumerate(messages):
            message_doc = create_message_pair_document(
                session_id,
                i,
                message['question'],
                message['response'],
                message['timestamp'],
                entra_oid
            )
            
            message_file = output_dir / f"{session_id}-{i}.json"
            with open(message_file, 'w', encoding='utf-8') as f:
                json.dump(message_doc, f, indent=2, ensure_ascii=False)
            print(f"✅ {session_id}-{i}.json (message pair)")
            total_files += 1
    
    print(f"\n{'='*60}")
    print(f"📊 Summary:")
    print(f"   Sessions: {len(sessions)}")
    print(f"   Total files created: {total_files}")
    print(f"   Output directory: {output_dir}")
    print(f"{'='*60}")

def main():
    """Main execution function."""
    
    print("="*60)
    print("Application Insights CSV to Cosmos DB JSON Converter")
    print("="*60)
    print()
    
    if not CSV_FILE.exists():
        print(f"❌ CSV file not found: {CSV_FILE}")
        print(f"   Please ensure the file exists in the data folder")
        return
    
    try:
        # Process CSV
        sessions = process_csv(CSV_FILE)
        
        if not sessions:
            print("⚠️  No valid sessions found in CSV")
            return
        
        # Save documents
        save_session_documents(sessions, OUTPUT_DIR)
        
        print("\n✅ Conversion complete!")
        print(f"\n💡 Next steps:")
        print(f"   1. Review the generated JSON files in: {OUTPUT_DIR}")
        print(f"   2. Upload to Cosmos DB using the upload script")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
