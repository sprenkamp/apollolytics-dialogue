import boto3
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

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
ANALYSIS_TABLE = os.environ.get('ANALYSIS_TABLE', 'apollolytics_analysis')

def initialize_db():
    """
    Initialize the DynamoDB table for analysis data if it doesn't exist.
    This function is idempotent and can be called on application startup.
    """
    try:
        # Check if table exists
        existing_tables = [table.name for table in dynamodb.tables.all()]
        
        if ANALYSIS_TABLE not in existing_tables:
            logger.info(f"Creating DynamoDB table: {ANALYSIS_TABLE}")
            
            # Create the table
            table = dynamodb.create_table(
                TableName=ANALYSIS_TABLE,
                KeySchema=[
                    {'AttributeName': 'analysis_id', 'KeyType': 'HASH'},  # Partition key
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}   # Sort key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'analysis_id', 'AttributeType': 'S'},
                    {'AttributeName': 'timestamp', 'AttributeType': 'N'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Wait for table to be created
            table.meta.client.get_waiter('table_exists').wait(TableName=ANALYSIS_TABLE)
            logger.info(f"DynamoDB table created: {ANALYSIS_TABLE}")
        else:
            logger.info(f"DynamoDB table already exists: {ANALYSIS_TABLE}")
            
    except Exception as e:
        logger.error(f"Error initializing DynamoDB: {str(e)}")

def save_analysis(
    analysis_id: str,
    analysis_type: str,
    data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Save analysis results to the database.
    
    Args:
        analysis_id: Unique identifier for the analysis
        analysis_type: Type of analysis (e.g., 'sentiment', 'topic', 'bias')
        data: The analysis results
        metadata: Additional metadata about the analysis
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        table = dynamodb.Table(ANALYSIS_TABLE)
        timestamp = int(time.time())
        
        # Convert any non-serializable objects to strings
        serialized_data = json.loads(json.dumps(data, default=str))
        serialized_metadata = json.loads(json.dumps(metadata or {}, default=str))
        
        item = {
            'analysis_id': analysis_id,
            'timestamp': timestamp,
            'analysis_type': analysis_type,
            'data': serialized_data,
            'metadata': serialized_metadata,
            'created_at': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=item)
        logger.info(f"Saved analysis {analysis_id} of type {analysis_type}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving analysis to DynamoDB: {str(e)}")
        return False

def get_analysis(analysis_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all analysis data for a specific analysis ID.
    
    Args:
        analysis_id: Unique identifier for the analysis
        
    Returns:
        List of analysis items associated with the ID
    """
    try:
        table = dynamodb.Table(ANALYSIS_TABLE)
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('analysis_id').eq(analysis_id)
        )
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Error retrieving analysis data from DynamoDB: {str(e)}")
        return []

def get_analysis_by_type(analysis_type: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve recent analysis data of a specific type.
    
    Args:
        analysis_type: Type of analysis to retrieve
        limit: Maximum number of results to return
        
    Returns:
        List of analysis items of the specified type
    """
    try:
        table = dynamodb.Table(ANALYSIS_TABLE)
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('analysis_type').eq(analysis_type),
            Limit=limit
        )
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Error retrieving analysis data by type from DynamoDB: {str(e)}")
        return [] 