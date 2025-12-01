"""
Configuration management
Handles all application configuration including Azure OpenAI
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
from openai import AsyncAzureOpenAI

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY = os.environ.get('AZURE_OPENAI_API_KEY', '')
AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT', '')
AZURE_OPENAI_DEPLOYMENT = os.environ.get('AZURE_OPENAI_DEPLOYMENT', '')
AZURE_OPENAI_API_VERSION = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-10-21')

# CORS Configuration
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:3000/auth/google/callback')

# Global Azure client (initialized on first access)
_azure_client: Optional[AsyncAzureOpenAI] = None


def get_azure_client() -> Optional[AsyncAzureOpenAI]:
    """Get or create Azure OpenAI client"""
    global _azure_client
    if _azure_client is None and AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
        _azure_client = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
    return _azure_client


# Initialize Azure client on import (for backward compatibility)
azure_client = get_azure_client()

