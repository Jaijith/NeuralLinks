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
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-5-nano-2025-08-07')  # Default to gpt-5-nano-2025-08-07

# Legacy Azure OpenAI Configuration - DEPRECATED: Use OPENAI_API_KEY and OPENAI_MODEL instead
# These are kept as aliases for backwards compatibility only
AZURE_OPENAI_DEPLOYMENT = OPENAI_MODEL  # Alias for backwards compatibility

# CORS Configuration - explicitly list allowed origins for credentials
_default_origins = "https://2ness.com,https://www.2ness.com,https://api.2ness.com,http://localhost:3000,http://localhost:3001"
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', _default_origins).split(',')

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


def is_responses_api_model(model: str) -> bool:
    """Check if model uses the new Responses API (gpt-5 models)"""
    model_lower = model.lower()
    return "gpt-5" in model_lower or "gpt-5-nano" in model_lower


async def call_openai(prompt: str, client: Optional[AsyncOpenAI] = None, model: Optional[str] = None) -> str:
    """
    Call OpenAI with the appropriate API based on model type.
    - For gpt-5 models: uses responses.create() API
    - For other models: uses chat.completions.create() API
    
    Args:
        prompt: The prompt to send to the model
        client: Optional OpenAI client (uses global if not provided)
        model: Optional model name (uses OPENAI_MODEL if not provided)
    
    Returns:
        The generated text response
    """
    if client is None:
        client = get_openai_client()
    if model is None:
        model = OPENAI_MODEL
    
    if client is None:
        raise ValueError("OpenAI client not configured")
    
    if is_responses_api_model(model):
        # Use new Responses API for gpt-5 models
        response = await client.responses.create(
            model=model,
            input=prompt
        )
        return response.output_text.strip() if response.output_text else ""
    else:
        # Use traditional Chat Completions API for legacy models
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip() if response.choices[0].message.content else ""


async def call_openai_with_system(system_prompt: str, user_message: str, client: Optional[AsyncOpenAI] = None, model: Optional[str] = None) -> str:
    """
    Call OpenAI with a system prompt and user message.
    For gpt-5 models, combines system and user into single input.
    
    Args:
        system_prompt: The system context/instructions
        user_message: The user's message
        client: Optional OpenAI client (uses global if not provided)
        model: Optional model name (uses OPENAI_MODEL if not provided)
    
    Returns:
        The generated text response
    """
    if client is None:
        client = get_openai_client()
    if model is None:
        model = OPENAI_MODEL
    
    if client is None:
        raise ValueError("OpenAI client not configured")
    
    if is_responses_api_model(model):
        # For gpt-5 models, combine system and user into single input
        combined_prompt = f"""System Instructions:
{system_prompt}

User Message:
{user_message}"""
        response = await client.responses.create(
            model=model,
            input=combined_prompt
        )
        return response.output_text.strip() if response.output_text else ""
    else:
        # Use traditional Chat Completions API with separate messages
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip() if response.choices[0].message.content else ""


# Initialize client on import
openai_client = get_openai_client()
azure_client = openai_client  # Alias for backwards compatibility

