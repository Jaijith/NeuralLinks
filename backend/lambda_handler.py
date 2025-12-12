"""
Lambda Handler for FastAPI Application
Wraps FastAPI app with Mangum for AWS Lambda compatibility

CRITICAL: Handler MUST be a function at module level - DO NOT REDEFINE IT
"""

# CRITICAL: Define handler as a function FIRST before any imports
# Lambda runtime looks for 'handler' function in this module
# We'll use a closure pattern so the function is never redefined

# Use a mutable container to hold the actual handler
_handler_impl = [None]

def handler(event, context):
    """Lambda handler function - delegates to actual implementation"""
    if _handler_impl[0] is not None:
        return _handler_impl[0](event, context)
    else:
        # Fallback if handler not initialized
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': '{"error": "Handler not initialized"}'
        }

import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_secret(secret_name: str) -> str:
    """Get secret from AWS Secrets Manager"""
    try:
        import boto3
        import json
        
        client = boto3.client('secretsmanager', region_name=os.environ.get('AWS_REGION', 'us-west-2'))
        response = client.get_secret_value(SecretId=secret_name)
        secret = response['SecretString']
        # If secret is JSON, parse it
        try:
            return json.loads(secret)
        except json.JSONDecodeError:
            return secret
    except Exception as e:
        logger.error(f"Error fetching secret {secret_name}: {e}")
        return ""

# Set environment variables from secrets (only if secret names are provided)
try:
    mongodb_secret_name = os.environ.get('MONGODB_SECRET_NAME')
    if mongodb_secret_name:
        secret_value = get_secret(mongodb_secret_name)
        if secret_value:
            os.environ['MONGODB_URI'] = secret_value
            logger.info("MongoDB URI set from Secrets Manager")
        else:
            logger.warning("MongoDB secret not found or empty")

    google_client_id_secret_name = os.environ.get('GOOGLE_CLIENT_ID_SECRET_NAME')
    if google_client_id_secret_name:
        secret_value = get_secret(google_client_id_secret_name)
        if secret_value:
            os.environ['GOOGLE_CLIENT_ID'] = secret_value
            logger.info("Google Client ID set from Secrets Manager")
        else:
            logger.warning("Google Client ID secret not found or empty")

    google_client_secret_secret_name = os.environ.get('GOOGLE_CLIENT_SECRET_SECRET_NAME')
    if google_client_secret_secret_name:
        secret_value = get_secret(google_client_secret_secret_name)
        if secret_value:
            os.environ['GOOGLE_CLIENT_SECRET'] = secret_value
            logger.info("Google Client Secret set from Secrets Manager")
        else:
            logger.warning("Google Client Secret not found or empty")
except Exception as e:
    logger.error(f"Error setting up secrets: {e}")
    # Continue anyway - app might work without secrets in some cases

# Import FastAPI app after secrets are set
# Initialize the actual handler implementation
try:
    from mangum import Mangum
    from app.main import app
    
    # Wrap FastAPI app with Mangum
    # lifespan="off" disables FastAPI lifespan events (startup/shutdown)
    # This is recommended for Lambda to avoid issues with connection pooling
    mangum_adapter = Mangum(app, lifespan="off")
    
    # Store the adapter in the mutable container
    # The handler function above will use it
    _handler_impl[0] = mangum_adapter
    logger.info("Lambda handler initialized successfully")
except Exception as e:
    logger.error(f"Error initializing FastAPI app: {e}")
    import traceback
    logger.error(traceback.format_exc())
    # Create error handler
    def error_handler(event, context):
        error_msg = "FastAPI app initialization failed. Check Lambda logs."
        logger.error(error_msg)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': f'{{"error": "{error_msg}", "detail": "Please check Lambda logs"}}'
        }
    _handler_impl[0] = error_handler
    logger.warning("Using error handler - FastAPI app not initialized")

# Final verification
logger.info(f"Handler ready: {type(handler)}, callable: {callable(handler)}, impl: {type(_handler_impl[0])}")
