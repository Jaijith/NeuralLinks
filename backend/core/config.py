"""
Configuration management
Handles all application configuration including OpenAI
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# OpenAI Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')  # Default to gpt-4o-mini

# Legacy Azure OpenAI Configuration (for backwards compatibility)
AZURE_OPENAI_API_KEY = os.environ.get('AZURE_OPENAI_API_KEY', '')
AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT', '')
AZURE_OPENAI_DEPLOYMENT = os.environ.get('AZURE_OPENAI_DEPLOYMENT', OPENAI_MODEL)
AZURE_OPENAI_API_VERSION = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-10-21')

# CORS Configuration
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:3000/auth/google/callback')

# Global OpenAI client (initialized on first access)
_openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> Optional[AsyncOpenAI]:
    """Get or create OpenAI client"""
    global _openai_client
    
    # Try to get API key from environment or AWS Secrets Manager
    api_key = OPENAI_API_KEY
    
    if not api_key and os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        # Running in Lambda - try to get from Secrets Manager
        try:
            import boto3
            secrets_client = boto3.client('secretsmanager', region_name=os.environ.get('AWS_REGION', 'us-west-2'))
            secret_name = os.environ.get('OPENAI_SECRET_NAME', '2n1/openai/api-key')
            response = secrets_client.get_secret_value(SecretId=secret_name)
            api_key = response['SecretString']
            logger.info(f"Retrieved OpenAI API key from Secrets Manager: {secret_name}")
        except Exception as e:
            logger.warning(f"Could not retrieve OpenAI API key from Secrets Manager: {e}")
    
    if _openai_client is None and api_key:
        _openai_client = AsyncOpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
    
    return _openai_client


# Alias for backwards compatibility
def get_azure_client() -> Optional[AsyncOpenAI]:
    """Get OpenAI client (alias for backwards compatibility)"""
    return get_openai_client()


# Initialize client on import
openai_client = get_openai_client()
azure_client = openai_client  # Alias for backwards compatibility

