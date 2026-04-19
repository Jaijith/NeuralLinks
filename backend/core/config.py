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
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-5-nano-2025-08-07')

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

# ---------------------------------------------------------------------------
# Smart client wrapper — transparently routes gpt-5 calls to Responses API
# ---------------------------------------------------------------------------

class _FakeChoice:
    """Mimics openai.types.chat.ChatCompletionChoice so callers see .message.content."""
    def __init__(self, text: str):
        self.message = type("_Msg", (), {"content": text})()


class _FakeCompletion:
    """Mimics openai.types.chat.ChatCompletion with .choices list."""
    def __init__(self, text: str):
        self.choices = [_FakeChoice(text)]


class _CompletionsProxy:
    """Intercepts chat.completions.create and reroutes for gpt-5 models."""

    def __init__(self, real_client: AsyncOpenAI):
        self._client = real_client

    async def create(self, **kwargs):
        model = kwargs.get("model", OPENAI_MODEL)
        if is_responses_api_model(model):
            messages = kwargs.get("messages", [])
            parts = []
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                if role == "system":
                    parts.append(f"System Instructions:\n{content}")
                else:
                    parts.append(content)
            combined = "\n\n".join(parts)
            rf = kwargs.get("response_format")
            if rf and rf.get("type") == "json_object":
                combined += "\n\nIMPORTANT: You MUST respond with valid JSON only, no markdown fences."
            resp = await self._client.responses.create(model=model, input=combined)
            text = resp.output_text.strip() if resp.output_text else ""
            return _FakeCompletion(text)
        else:
            # Strip unsupported params for non-responses models if needed
            return await self._client.chat.completions.create(**kwargs)

    async def acreate(self, **kwargs):
        """Alias for create (some libraries use acreate)."""
        return await self.create(**kwargs)


class _ChatProxy:
    """Provides .completions attribute that returns a _CompletionsProxy."""
    def __init__(self, real_client: AsyncOpenAI):
        self.completions = _CompletionsProxy(real_client)


class SmartOpenAIClient:
    """
    Wraps AsyncOpenAI so that `client.chat.completions.create(model='gpt-5-*')`
    is automatically routed through the Responses API.  All other attributes
    and methods are forwarded to the underlying client.
    """

    def __init__(self, real_client: AsyncOpenAI):
        self._client = real_client
        self.chat = _ChatProxy(real_client)
        self.responses = real_client.responses

    def __getattr__(self, name):
        return getattr(self._client, name)


# Global OpenAI client (initialized on first access)
_openai_client: Optional[SmartOpenAIClient] = None


def get_openai_client() -> Optional[SmartOpenAIClient]:
    """Get or create OpenAI client (wrapped with gpt-5 Responses API adapter)."""
    global _openai_client
    
    api_key = OPENAI_API_KEY
    
    if not api_key and os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
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
        raw = AsyncOpenAI(api_key=api_key)
        _openai_client = SmartOpenAIClient(raw)
        logger.info("OpenAI client initialized successfully (SmartOpenAIClient)")
    
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


async def call_openai_chat(
    client: Optional[AsyncOpenAI] = None,
    model: Optional[str] = None,
    messages: Optional[list] = None,
    response_format: Optional[dict] = None,
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> str:
    """
    Universal drop-in replacement for client.chat.completions.create().
    Automatically routes to the Responses API for gpt-5 models.
    Returns the raw text content from the response.
    """
    if client is None:
        client = get_openai_client()
    if model is None:
        model = OPENAI_MODEL
    if client is None:
        raise ValueError("OpenAI client not configured")
    if not messages:
        raise ValueError("messages is required")

    if is_responses_api_model(model):
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"System Instructions:\n{content}")
            else:
                parts.append(content)
        combined = "\n\n".join(parts)
        if response_format and response_format.get("type") == "json_object":
            combined += "\n\nIMPORTANT: You MUST respond with valid JSON only, no markdown."

        response = await client.responses.create(model=model, input=combined)
        return response.output_text.strip() if response.output_text else ""
    else:
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip() if response.choices[0].message.content else ""


async def call_openai_json(
    system_prompt: str,
    user_message: str,
    client: Optional[AsyncOpenAI] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 4000,
) -> str:
    """
    Call OpenAI expecting a JSON response. Works with both gpt-5 (Responses API)
    and legacy models (Chat Completions with response_format=json_object).
    """
    if client is None:
        client = get_openai_client()
    if model is None:
        model = OPENAI_MODEL
    if client is None:
        raise ValueError("OpenAI client not configured")

    combined = f"System Instructions:\n{system_prompt}\n\nUser Message:\n{user_message}"

    if is_responses_api_model(model):
        response = await client.responses.create(
            model=model,
            input=combined,
        )
        return response.output_text.strip() if response.output_text else ""
    else:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip() if response.choices[0].message.content else ""


# Initialize client on import
openai_client = get_openai_client()
azure_client = openai_client  # Alias for backwards compatibility

