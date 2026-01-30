"""
Voice Routes - API endpoints for real-time voice communication
Handles session creation, ephemeral token generation, and voice events
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import httpx
import logging
import os
import json

from core.auth import require_auth, get_current_user
from core.database import get_database
from domain.voice import VoicePromptGenerator, VoiceConfig, VOICE_SETTINGS
from domain.voice.voice_config import OPENAI_REALTIME_CLIENT_SECRETS_URL
from domain.avatar.state import StateManager
from domain.workflow.models.bonding_state import BondingState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from environment or AWS Secrets Manager"""
    # First try environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key
    
    # Try AWS Secrets Manager
    try:
        import boto3
        secrets_client = boto3.client('secretsmanager', region_name='us-west-2')
        secret_name = os.environ.get('OPENAI_SECRET_NAME', '2n1/openai/api-key')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_value = response['SecretString']
        
        # Try to parse as JSON in case it's a JSON object
        try:
            secret_dict = json.loads(secret_value)
            api_key = secret_dict.get('api_key') or secret_dict.get('OPENAI_API_KEY') or secret_value
        except json.JSONDecodeError:
            api_key = secret_value
        
        logger.info(f"Retrieved OpenAI API key from Secrets Manager: {secret_name}")
        return api_key
    except Exception as e:
        logger.warning(f"Could not retrieve OpenAI API key from Secrets Manager: {e}")
        return None


# OpenAI API key - lazy loaded
_openai_api_key_cache = None

def _get_cached_openai_key() -> Optional[str]:
    """Get cached OpenAI API key or fetch it"""
    global _openai_api_key_cache
    if _openai_api_key_cache is None:
        _openai_api_key_cache = get_openai_api_key()
    return _openai_api_key_cache

# Get database
db = get_database()


class VoiceSessionRequest(BaseModel):
    """Request to create a voice session"""
    avatar_id: Optional[str] = None  # Uses user's default avatar if not specified
    setting_preset: str = Field(default="default", description="Voice setting preset: default, low_latency, quiet_environment, noisy_environment, push_to_talk")
    user_preferences: Optional[Dict[str, Any]] = Field(default=None, description="User voice preferences")


class VoiceSessionResponse(BaseModel):
    """Response containing voice session configuration"""
    success: bool
    ephemeral_token: Optional[str] = None
    session_config: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class VoiceEventRequest(BaseModel):
    """Voice interaction event"""
    event_type: str = Field(..., description="Event type: session_started, user_spoke, avatar_spoke, session_ended, emotional_moment")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Event context data")


class VoiceSettingsRequest(BaseModel):
    """User voice settings update"""
    setting_preset: Optional[str] = None
    custom_settings: Optional[Dict[str, Any]] = None


class VoiceSettingsResponse(BaseModel):
    """Voice settings response"""
    success: bool
    settings: Optional[Dict[str, Any]] = None
    presets: List[str] = Field(default_factory=lambda: list(VOICE_SETTINGS.keys()))


@router.post("/session", response_model=VoiceSessionResponse)
async def create_voice_session(
    req: VoiceSessionRequest,
    request: Request
):
    """
    Create a voice session with OpenAI Realtime API
    
    Returns an ephemeral token for direct WebRTC connection from frontend.
    The session is configured with dynamic prompts based on avatar state.
    """
    try:
        # Get authenticated user
        user = await require_auth(request)
        
        user_id = user.id
        avatar_id = req.avatar_id or user_id  # Default to user's own avatar
        
        # Initialize prompt generator
        prompt_generator = VoicePromptGenerator(db)
        
        # Get avatar's current internal state
        state_manager = StateManager(db)
        internal_state, _ = await state_manager.get_current_state(avatar_id)
        
        # Get bonding state between user and avatar
        bonding_doc = await db.bonding_states.find_one({
            "user_id": user_id,
            "avatar_id": avatar_id
        })
        bonding_state = BondingState.from_dict(bonding_doc) if bonding_doc else None
        
        # Generate dynamic prompt based on state
        instructions = await prompt_generator.generate_prompt(
            user_id=user_id,
            avatar_id=avatar_id,
            internal_state=internal_state,
            bonding_state=bonding_state,
            user_settings=req.user_preferences
        )
        
        # Get voice configuration
        voice_config = VOICE_SETTINGS.get(req.setting_preset, VOICE_SETTINGS["default"])
        session_config = voice_config.to_session_config(instructions)
        
        # Request ephemeral token from OpenAI (GA API)
        openai_key = _get_cached_openai_key()
        if not openai_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable or configure AWS Secrets Manager.")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENAI_REALTIME_CLIENT_SECRETS_URL,
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json"
                },
                json=session_config,
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI session creation failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to create voice session: {response.text}"
                )
            
            session_data = response.json()
        
        logger.info(f"Voice session created for user {user_id}, avatar {avatar_id}")
        
        # Extract session config from the nested structure
        session_info = session_config.get("session", {})
        audio_config = session_info.get("audio", {})
        
        return VoiceSessionResponse(
            success=True,
            ephemeral_token=session_data.get("value"),  # GA API returns 'value' directly
            session_config={
                "model": session_info.get("model"),
                "voice": audio_config.get("output", {}).get("voice"),
                "turn_detection": session_info.get("turn_detection")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating voice session: {e}")
        return VoiceSessionResponse(
            success=False,
            error=str(e)
        )


@router.get("/prompt/{avatar_id}")
async def get_voice_prompt(
    avatar_id: str,
    request: Request
):
    """
    Get current voice prompt for debugging/preview
    
    Returns the dynamic prompt that would be used for a voice session.
    """
    try:
        user = await require_auth(request)
        user_id = user.id
        
        # Initialize prompt generator
        prompt_generator = VoicePromptGenerator(db)
        
        # Get states
        state_manager = StateManager(db)
        internal_state, _ = await state_manager.get_current_state(avatar_id)
        
        bonding_doc = await db.bonding_states.find_one({
            "user_id": user_id,
            "avatar_id": avatar_id
        })
        bonding_state = BondingState.from_dict(bonding_doc) if bonding_doc else None
        
        # Generate prompt
        prompt = await prompt_generator.generate_prompt(
            user_id=user_id,
            avatar_id=avatar_id,
            internal_state=internal_state,
            bonding_state=bonding_state
        )
        
        return {
            "success": True,
            "prompt": prompt,
            "state_summary": {
                "mood": internal_state.mood.value if internal_state else "neutral",
                "energy_level": internal_state.energy_level if internal_state else 0.5,
                "bond_strength": bonding_state.metrics.bond_strength if bonding_state else 0.5
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/event")
async def record_voice_event(
    req: VoiceEventRequest,
    request: Request
):
    """
    Record voice interaction events
    
    Updates avatar state and bonding metrics based on voice interactions.
    """
    try:
        user = await require_auth(request)
        user_id = user.id
        context = req.context or {}
        avatar_id = context.get("avatar_id", user_id)
        
        # Handle different event types
        if req.event_type == "session_started":
            # Track session start
            await db.voice_sessions.insert_one({
                "user_id": user_id,
                "avatar_id": avatar_id,
                "started_at": context.get("timestamp"),
                "status": "active"
            })
            
        elif req.event_type == "session_ended":
            # Update session and bonding metrics
            duration = context.get("duration_seconds", 0)
            
            # Update session
            await db.voice_sessions.update_one(
                {"user_id": user_id, "avatar_id": avatar_id, "status": "active"},
                {
                    "$set": {
                        "status": "ended",
                        "ended_at": context.get("timestamp"),
                        "duration_seconds": duration
                    }
                }
            )
            
            # Update bonding state - longer conversations strengthen bond
            if duration > 60:  # More than 1 minute
                bond_delta = min(0.05, duration / 600)  # Max 0.05 per session
                await db.bonding_states.update_one(
                    {"user_id": user_id, "avatar_id": avatar_id},
                    {
                        "$inc": {
                            "metrics.bond_strength": bond_delta,
                            "total_sessions": 1
                        },
                        "$set": {
                            "last_bonding_session": context.get("timestamp")
                        }
                    },
                    upsert=True
                )
            
        elif req.event_type == "emotional_moment":
            # Record significant emotional moments
            emotion = context.get("emotion")
            intensity = context.get("intensity", 0.5)
            
            if intensity > 0.7:
                # High-intensity emotional moments strengthen bond more
                await db.bonding_states.update_one(
                    {"user_id": user_id, "avatar_id": avatar_id},
                    {
                        "$inc": {"metrics.bond_strength": 0.02},
                        "$push": {
                            "delight_history": {
                                "$each": [intensity],
                                "$slice": -10
                            }
                        }
                    },
                    upsert=True
                )
            
        elif req.event_type == "user_spoke":
            # Update avatar's social desire satisfaction
            state_manager = StateManager(db)
            internal_state, _ = await state_manager.get_current_state(avatar_id)
            if internal_state:
                # Receiving voice input satisfies social desire
                internal_state.social_desire = max(0.0, internal_state.social_desire - 0.1)
                internal_state.boost_energy(0.05)  # Interactions boost energy
                await state_manager.update_internal_state(avatar_id, internal_state)
        
        return {"success": True, "event_type": req.event_type}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording voice event: {e}")
        return {"success": False, "error": str(e)}


@router.get("/settings")
async def get_voice_settings(request: Request):
    """
    Get user's voice settings and available presets
    """
    try:
        user = await get_current_user(request)
        
        if not user:
            # Return defaults for unauthenticated users
            return VoiceSettingsResponse(
                success=True,
                settings={
                    "preset": "default",
                    "noise_threshold": 0.5,
                    "response_speed": "balanced",
                    "prefer_shorter_responses": False
                },
                presets=list(VOICE_SETTINGS.keys())
            )
        
        user_id = user.id
        
        # Get user's saved voice settings
        user_settings = await db.user_voice_settings.find_one({"user_id": user_id})
        
        return VoiceSettingsResponse(
            success=True,
            settings=user_settings.get("settings") if user_settings else {
                "preset": "default",
                "noise_threshold": 0.5,
                "response_speed": "balanced",
                "prefer_shorter_responses": False
            },
            presets=list(VOICE_SETTINGS.keys())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice settings: {e}")
        return VoiceSettingsResponse(success=False, presets=list(VOICE_SETTINGS.keys()))


@router.post("/settings")
async def update_voice_settings(
    req: VoiceSettingsRequest,
    request: Request
):
    """
    Update user's voice settings
    """
    try:
        user = await require_auth(request)
        user_id = user.id
        
        settings = {}
        
        if req.setting_preset:
            if req.setting_preset not in VOICE_SETTINGS:
                raise HTTPException(status_code=400, detail=f"Invalid preset: {req.setting_preset}")
            settings["preset"] = req.setting_preset
        
        if req.custom_settings:
            settings.update(req.custom_settings)
        
        # Save settings
        await db.user_voice_settings.update_one(
            {"user_id": user_id},
            {"$set": {"settings": settings, "user_id": user_id}},
            upsert=True
        )
        
        return {"success": True, "settings": settings}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating voice settings: {e}")
        return {"success": False, "error": str(e)}
