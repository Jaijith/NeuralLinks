"""
Workflow Lambda Handler
Separate Lambda function for the workflow engine
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize handler implementation holder
_handler_impl = [None]

def get_secret(secret_name: str) -> str:
    """Fetch a secret from AWS Secrets Manager"""
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=os.environ.get('AWS_REGION', 'us-west-1'))
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response.get('SecretString', '')
    except ClientError as e:
        logger.error(f"Failed to fetch secret {secret_name}: {e}")
        raise


def initialize_handler():
    """Initialize the workflow Lambda handler"""
    # Fetch secrets and set environment variables
    try:
        # MongoDB URI
        mongodb_secret_name = os.environ.get('MONGODB_SECRET_NAME')
        if mongodb_secret_name:
            mongodb_uri = get_secret(mongodb_secret_name)
            os.environ['MONGODB_URI'] = mongodb_uri
            logger.info("MongoDB URI set from Secrets Manager")
        
        # OpenAI API Key
        openai_secret_name = os.environ.get('OPENAI_SECRET_NAME')
        if openai_secret_name:
            openai_key = get_secret(openai_secret_name)
            os.environ['OPENAI_API_KEY'] = openai_key
            logger.info("OpenAI API Key set from Secrets Manager")
    except Exception as e:
        logger.error(f"Failed to initialize secrets: {e}")
        raise
    
    # Now import and create the FastAPI app
    from workflow_app import create_workflow_app
    app = create_workflow_app()
    
    # Create Mangum adapter for AWS Lambda
    from mangum import Mangum
    mangum_adapter = Mangum(app, lifespan="off")
    
    logger.info("Workflow Lambda handler initialized successfully")
    return mangum_adapter


def handler(event, context):
    """Main Lambda handler for workflow requests"""
    if _handler_impl[0] is None:
        _handler_impl[0] = initialize_handler()
    
    return _handler_impl[0](event, context)

