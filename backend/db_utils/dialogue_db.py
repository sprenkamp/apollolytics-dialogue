import boto3
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal

# Configure logging
logger = logging.getLogger(__name__)

# Initialize DynamoDB client with required configuration
aws_region = os.environ.get('AWS_REGION', 'eu-north-1')
endpoint_url = os.environ.get('AWS_ENDPOINT_URL')
logger.info(f"Using AWS region: {aws_region}")

if endpoint_url:
    logger.info(f"Using custom DynamoDB endpoint: {endpoint_url}")
    dynamodb = boto3.resource('dynamodb', region_name=aws_region, endpoint_url=endpoint_url)
else:
    dynamodb = boto3.resource('dynamodb', region_name=aws_region)

# Table name can be configured via environment variable
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'apollolytics_dialogues')

def initialize_db():
    """
    Initialize the DynamoDB table if it doesn't exist.
    This function is idempotent and can be called on application startup.
    """
    try:
        # Check if table exists
        existing_tables = [table.name for table in dynamodb.tables.all()]
        logger.info(f"Available tables: {existing_tables}")
        
        if DYNAMODB_TABLE not in existing_tables:
            logger.info(f"Creating DynamoDB table: {DYNAMODB_TABLE}")
            
            # Create the table
            table = dynamodb.create_table(
                TableName=DYNAMODB_TABLE,
                KeySchema=[
                    {'AttributeName': 'session_id', 'KeyType': 'HASH'},  # Partition key
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}   # Sort key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'session_id', 'AttributeType': 'S'},
                    {'AttributeName': 'timestamp', 'AttributeType': 'N'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Wait for table to be created
            table.meta.client.get_waiter('table_exists').wait(TableName=DYNAMODB_TABLE)
            logger.info(f"DynamoDB table created: {DYNAMODB_TABLE}")
        else:
            logger.info(f"DynamoDB table already exists: {DYNAMODB_TABLE}")
            
    except Exception as e:
        logger.error(f"Error initializing DynamoDB: {str(e)}")
        # Don't raise exception - allow the application to continue even if DB setup fails

def save_session_init(
    session_id: str, 
    article: str, 
    dialogue_mode: str, 
    origin_url: Optional[str] = None,
    prolific_id: Optional[str] = None
) -> bool:
    """
    Save the initial session data when a conversation starts.
    
    Args:
        session_id: Unique identifier for the session
        article: The article text being analyzed
        dialogue_mode: The mode of the dialogue (e.g., "critical", "positive")
        origin_url: The URL that originated the request
        prolific_id: The Prolific ID of the participant
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        timestamp = int(time.time())
        
        item = {
            'session_id': session_id,
            'timestamp': timestamp,
            'event_type': 'session_init',
            'article': article,
            'dialogue_mode': dialogue_mode,
            'origin_url': origin_url or 'unknown',
            'prolific_id': prolific_id or 'XXX',
            'created_at': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=item)
        logger.info(f"Saved session initialization for {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving session init to DynamoDB: {str(e)}")
        return False

def save_propaganda_analysis(
    session_id: str,
    propaganda_result: Dict[str, Any]
) -> bool:
    """
    Save the propaganda analysis results for a session.
    
    Args:
        session_id: Unique identifier for the session
        propaganda_result: The result of propaganda analysis
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        timestamp = int(time.time())
        
        # Convert any non-serializable objects to strings
        serialized_result = json.loads(json.dumps(propaganda_result, default=str))
        
        item = {
            'session_id': session_id,
            'timestamp': timestamp,
            'event_type': 'propaganda_analysis',
            'propaganda_result': serialized_result,
            'created_at': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=item)
        logger.info(f"Saved propaganda analysis for {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving propaganda analysis to DynamoDB: {str(e)}")
        return False

def save_message(session_id: str, role: str, content: Any, message_id: str, timing_info: Dict[str, float] = None) -> None:
    """
    Save a message to DynamoDB with timing information.
    
    Args:
        session_id: The session ID
        role: The role of the message sender ('user' or 'assistant')
        content: The message content (transcript text)
        message_id: Unique ID for the message
        timing_info: Dictionary containing timing information
            For assistant:
            - model_generation_time: Time taken for model to generate response
            - model_audio_duration: Duration of the model's audio response
            For user:
            - thinking_time: Time from assistant response to starting recording
            - recording_duration: Duration of recording
            - total_response_time: Total time from assistant response to end of recording
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        timestamp = int(time.time())  # Use Unix timestamp as number
        
        # Convert timing_info float values to Decimal, handling None values
        timing_info_decimal = None
        if timing_info:
            timing_info_decimal = {}
            for k, v in timing_info.items():
                if v is not None:
                    try:
                        timing_info_decimal[k] = Decimal(str(v))
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert timing value {k}: {v} to Decimal")
        
        # For user messages, handle different content types and filter out audio
        if role == "user":
            if isinstance(content, list):
                # Find the transcript in the content and filter out audio
                transcript = None
                for item in content:
                    if item.get("type") == "text":
                        transcript = item.get("text")
                        break
                content = transcript or ""  # Use transcript if found, otherwise empty string
            elif isinstance(content, str):
                content = content  # Keep string content as is
        
        # Only save text content, not audio
        message_data = {
            'session_id': session_id,
            'message_id': message_id,
            'role': role,
            'content': content,  # This will be the transcript text only
            'timestamp': timestamp,
            'timing_info': timing_info_decimal or {},
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Log the data being pushed to DynamoDB (excluding audio)
        logger.info(f"Pushing to DynamoDB - Session: {session_id}, Role: {role}")
        logger.info(f"Message content: {content}")
        logger.info(f"Timing info: {timing_info_decimal}")
        
        table.put_item(Item=message_data)
        logger.info(f"Successfully saved {role} message to DynamoDB: {message_id}")
    except Exception as e:
        logger.error(f"Error saving message to DynamoDB: {e}")
        logger.error(f"Failed message data: {json.dumps(message_data, default=str) if 'message_data' in locals() else 'No message data'}")
        raise

def save_session_end(
    session_id: str,
    reason: str = "normal"
) -> bool:
    """
    Mark a session as ended.
    
    Args:
        session_id: Unique identifier for the session
        reason: The reason the session ended (e.g., "normal", "error", "timeout")
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        timestamp = int(time.time())
        
        item = {
            'session_id': session_id,
            'timestamp': timestamp,
            'event_type': 'session_end',
            'reason': reason,
            'created_at': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=item)
        logger.info(f"Saved session end for {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving session end to DynamoDB: {str(e)}")
        return False

def get_session_data(session_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all data for a specific session.
    
    Args:
        session_id: Unique identifier for the session
        
    Returns:
        List of items associated with the session
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id)
        )
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Error retrieving session data from DynamoDB: {str(e)}")
        return []

def list_sessions() -> List[str]:
    """
    List all session IDs.
    
    Returns:
        List of session IDs
    """
    # This is a scan operation, which can be expensive for large tables
    # In production, you might want to use a secondary index or other approach
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.scan(
            ProjectionExpression="session_id",
            Select="SPECIFIC_ATTRIBUTES"
        )
        
        # Extract unique session IDs
        session_ids = set()
        for item in response.get('Items', []):
            session_ids.add(item['session_id'])
            
        # Handle pagination if there are more results
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ProjectionExpression="session_id",
                Select="SPECIFIC_ATTRIBUTES",
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            for item in response.get('Items', []):
                session_ids.add(item['session_id'])
                
        return list(session_ids)
    except Exception as e:
        logger.error(f"Error listing sessions from DynamoDB: {str(e)}")
        return []