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
from domain.voice.voice_config import OPENAI_REALTIME_CLIENT_SECRETS_URL, VOICE_TOOLS
from domain.voice.social_context import SocialContextService
from domain.voice.voice_memory import VoiceMemoryService
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
        session_config = voice_config.to_session_config(instructions, tools=VOICE_TOOLS)
        
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
            
            # Increment knowledge gap conversation counter (for pacing calibration questions)
            try:
                from domain.avatar.personality.knowledge_gaps import KnowledgeGapTracker
                gap_tracker = KnowledgeGapTracker(db)
                await gap_tracker.increment_conversation_count(user_id)
            except Exception as gap_err:
                logger.debug(f"Knowledge gap counter update skipped: {gap_err}")
            
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


class ContextRequest(BaseModel):
    """Request for social context during voice session"""
    avatar_id: str = Field(..., description="The avatar's ID")
    context_type: str = Field(..., description="Type of context to fetch")
    friend_name: Optional[str] = Field(None, description="Friend name for specific queries")
    time_range: Optional[str] = Field("recent", description="Time range for context")


class ContextResponse(BaseModel):
    """Response with social context"""
    success: bool
    summary: str
    data: Optional[Dict[str, Any]] = None
    fetch_time_ms: Optional[int] = None


@router.post("/context", response_model=ContextResponse)
async def get_voice_context(
    req: ContextRequest,
    request: Request
):
    """
    Get social context during active voice session.
    
    This endpoint is called when the AI uses the recall_social_context function
    to get more specific information than what was provided at session start.
    
    The AI decides when to call this - it should NOT be called for:
    - Casual greetings
    - Emotional conversations
    - Questions answerable from existing context
    """
    import time
    start_time = time.time()
    
    try:
        # Authenticate user
        user = await require_auth(request)
        
        # Initialize social context service
        social_service = SocialContextService(db)
        
        # Fetch the requested context
        result = await social_service.get_specific_context(
            avatar_id=req.avatar_id,
            context_type=req.context_type,
            friend_name=req.friend_name,
            time_range=req.time_range or "recent"
        )
        
        fetch_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Voice context fetched: type={req.context_type}, time={fetch_time_ms}ms")
        
        return ContextResponse(
            success=True,
            summary=result.get("summary", ""),
            data=result.get("data"),
            fetch_time_ms=fetch_time_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching voice context: {e}")
        return ContextResponse(
            success=False,
            summary="I'm having trouble remembering right now.",
            data=None
        )


@router.get("/context/tier1/{avatar_id}")
async def get_tier1_context(
    avatar_id: str,
    request: Request
):
    """
    Pre-fetch Tier 1 social context.
    
    This can be called when the user hovers over the voice orb to
    pre-warm the context cache, reducing latency when session starts.
    """
    import time
    start_time = time.time()
    
    try:
        user = await require_auth(request)
        
        social_service = SocialContextService(db)
        context = await social_service.get_tier1_context(avatar_id, user.id)
        
        fetch_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "context": context.get("formatted_context", ""),
            "fetch_time_ms": fetch_time_ms
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Tier 1 context: {e}")
        return {
            "success": False,
            "context": "",
            "error": str(e)
        }


# =============================================================================
# CONVERSATION RECALL (MCP Tool: recall_past_conversations)
# =============================================================================

class RecallRequest(BaseModel):
    """Request to search past conversations"""
    avatar_id: str = Field(..., description="Avatar ID")
    query: str = Field(..., description="What to search for in past conversations")
    include_full_transcript: bool = Field(default=False, description="Whether to fetch full S3 transcript")


class RecallResponse(BaseModel):
    """Response with recalled conversation memories"""
    success: bool
    summary: str
    results: List[Dict[str, Any]] = []
    total_found: int = 0


@router.post("/recall", response_model=RecallResponse)
async def recall_past_conversations(
    req: RecallRequest,
    request: Request
):
    """
    Search past voice conversations.

    Called by the `recall_past_conversations` MCP tool during active voice
    sessions. Uses a multi-layer search strategy:
    1. conversation_index (summaries + S3 keys)
    2. episodic_memory (deeper context)
    3. S3 full transcripts (when include_full_transcript=True)
    """
    import time
    start_time = time.time()

    try:
        user = await require_auth(request)
        user_id = user.id

        from domain.voice.conversation_recall import ConversationRecallService
        recall_service = ConversationRecallService(db)

        result = await recall_service.recall(
            user_id=user_id,
            query=req.query,
            avatar_id=req.avatar_id,
            limit=5,
            include_full_transcript=req.include_full_transcript,
        )

        # Build a human-friendly summary for the voice agent
        results_list = result.get("results", [])

        # Serialize datetime objects in results for JSON compatibility
        from datetime import datetime as _dt
        for r in results_list:
            for k, v in list(r.items()):
                if isinstance(v, _dt):
                    r[k] = v.isoformat()

        if results_list:
            summaries = []
            for r in results_list[:3]:
                s = r.get("summary", "")
                if s:
                    summaries.append(s)
                # Include relevant snippets from full transcript if available
                snippets = r.get("relevant_snippets", [])
                for snip in snippets[:2]:
                    summaries.append(f"From that conversation: {snip[:300]}")

            summary = " | ".join(summaries)
        else:
            summary = "I couldn't find a specific conversation about that, but it might have been a while ago."

        fetch_time = int((time.time() - start_time) * 1000)
        logger.info(f"Conversation recall: query='{req.query}', found={len(results_list)}, time={fetch_time}ms")

        return RecallResponse(
            success=True,
            summary=summary,
            results=results_list,
            total_found=len(results_list),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in conversation recall: {e}")
        return RecallResponse(
            success=False,
            summary="I'm having trouble searching my memory right now.",
            results=[],
            total_found=0,
        )


# =============================================================================
# WORKFLOW TRIGGER
# =============================================================================

class WorkflowTriggerRequest(BaseModel):
    """Request to trigger a workflow from voice"""
    avatar_id: str = Field(..., description="Avatar ID")
    mission_type: str = Field(..., description="Type of workflow to run")
    mission_name: str = Field(..., description="Name for the mission")
    description: Optional[str] = Field(None, description="Mission description")
    interests: Optional[List[str]] = Field(default_factory=list, description="Interests to filter by")
    keywords: Optional[List[str]] = Field(default_factory=list, description="Keywords to search for")
    approach: Optional[str] = Field(default="friendly", description="Approach style")
    max_targets: Optional[int] = Field(default=10, description="Max targets to find")


class WorkflowTriggerResponse(BaseModel):
    """Response after triggering a workflow"""
    success: bool
    message: str
    mission_id: Optional[str] = None
    mission_name: Optional[str] = None
    mission_type: Optional[str] = None


@router.post("/workflow", response_model=WorkflowTriggerResponse)
async def trigger_workflow_from_voice(
    req: WorkflowTriggerRequest,
    request: Request
):
    """
    Trigger a workflow mission from voice command.
    
    This endpoint is called when the AI uses the trigger_workflow function
    to start a mission based on user's voice request.
    
    The mission will appear in the user's Missions page and start automatically.
    """
    import time
    start_time = time.time()
    
    try:
        # Authenticate user
        user = await require_auth(request)
        
        logger.info(f"Voice workflow trigger: type={req.mission_type}, name={req.mission_name}")
        
        # Import workflow services
        from domain.workflow.services.mission_service import MissionService
        from domain.workflow.models.enums import MissionType, ApproachStyle
        
        # Map string to enum
        mission_type_map = {
            "matchmaking": MissionType.MATCHMAKING,
            "networking": MissionType.NETWORKING,
            "sales_leads": MissionType.SALES_LEADS,
            "marketing_campaign": MissionType.MARKETING_CAMPAIGN,
            "bonding": MissionType.BONDING,
            "job_finder": MissionType.JOB_FINDER
        }
        
        approach_map = {
            "casual": ApproachStyle.CASUAL,
            "professional": ApproachStyle.PROFESSIONAL,
            "friendly": ApproachStyle.CASUAL,  # Map friendly to casual
            "direct": ApproachStyle.PROFESSIONAL,  # Map direct to professional
            "curious": ApproachStyle.CURIOUS,
            "enthusiastic": ApproachStyle.ENTHUSIASTIC,
            "thoughtful": ApproachStyle.THOUGHTFUL
        }
        
        mission_type = mission_type_map.get(req.mission_type.lower(), MissionType.MATCHMAKING)
        approach = approach_map.get((req.approach or "casual").lower(), ApproachStyle.CASUAL)
        
        # Get required services
        from app.globals import intelligent_avatar
        from openai import AsyncOpenAI
        
        openai_key = get_openai_api_key()
        openai_client = AsyncOpenAI(api_key=openai_key) if openai_key else None
        
        # Create mission service
        mission_service = MissionService(
            db=db,
            mcp_server=None,  # Will use default
            openai_client=openai_client,
            intelligent_avatar=intelligent_avatar
        )
        
        # Build criteria
        criteria = {
            "interests": req.interests or [],
            "keywords": req.keywords or [],
            "min_compatibility_score": 60
        }
        
        # Build strategy - pass enum directly for Pydantic validation
        strategy = {
            "approach": approach,  # Pass enum directly, not string
            "max_targets": req.max_targets or 10,
            "talking_points": []
        }
        
        # Create the mission (don't auto_start here - the MCP server isn't available in main Lambda)
        mission = await mission_service.create_mission(
            user_id=user.id,
            avatar_id=req.avatar_id,
            mission_type=mission_type,
            name=req.mission_name,
            description=req.description or f"Mission created via voice: {req.mission_name}",
            criteria=criteria,
            strategy=strategy,
            source_chat_id=None,  # From voice, not chat
            auto_start=False  # Don't auto-start here - we'll call the workflow Lambda
        )
        
        # Call the Workflow Lambda to start the mission (it has the MCP server)
        try:
            import httpx
            workflow_api = f"https://api.2ness.com/api/workflow/missions/detail/{mission.id}/start"
            
            # Get the auth token from the request to forward it
            auth_header = request.headers.get("Authorization") or request.headers.get("Cookie")
            headers = {}
            if "Authorization" in request.headers:
                headers["Authorization"] = request.headers["Authorization"]
            if "Cookie" in request.headers:
                headers["Cookie"] = request.headers["Cookie"]
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                start_response = await client.post(workflow_api, headers=headers)
                if start_response.status_code == 200:
                    logger.info(f"✅ Mission {mission.id} started via workflow Lambda")
                else:
                    logger.warning(f"⚠️ Failed to start mission via workflow Lambda: {start_response.status_code}")
        except Exception as start_error:
            logger.warning(f"⚠️ Could not call workflow Lambda to start mission: {start_error}")
            # Mission is still created, user can start it manually from Missions page
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Voice workflow created: mission_id={mission.id}, elapsed={elapsed_ms}ms")
        
        return WorkflowTriggerResponse(
            success=True,
            message=f"Mission '{req.mission_name}' has been created and started! You can check the Missions page to see the progress.",
            mission_id=mission.id,
            mission_name=mission.name,
            mission_type=mission.type.value if hasattr(mission.type, 'value') else str(mission.type)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering workflow from voice: {e}")
        import traceback
        traceback.print_exc()
        return WorkflowTriggerResponse(
            success=False,
            message=f"I wasn't able to start that mission right now. Could you try again or check the Missions page?",
            mission_id=None
        )


# =============================================================================
# TRANSCRIPT STORAGE AND MEMORY
# =============================================================================

class TranscriptMessage(BaseModel):
    """A single message in a transcript"""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")


class TranscriptRequest(BaseModel):
    """Request to save a voice transcript"""
    session_id: str = Field(..., description="Voice session ID")
    avatar_id: str = Field(..., description="Avatar ID")
    messages: List[TranscriptMessage] = Field(..., description="Conversation messages")
    started_at: str = Field(..., description="Session start time (ISO)")
    ended_at: str = Field(..., description="Session end time (ISO)")
    duration_seconds: int = Field(..., description="Session duration in seconds")


@router.post("/transcript")
async def save_transcript(
    req: TranscriptRequest,
    request: Request
):
    """
    Save voice transcript to S3 and trigger background memory extraction.
    
    This endpoint is called by frontend when a voice session ends.
    It's fire-and-forget from the frontend perspective - returns immediately.
    
    Flow:
    1. Save transcript to S3 (user-isolated path)
    2. Track in MongoDB for processing
    3. Trigger background Lambda for memory extraction (async)
    """
    try:
        user = await require_auth(request)
        user_id = user.id
        
        # Initialize memory service
        memory_service = VoiceMemoryService(db)
        
        # Save transcript (fast - just S3 put + MongoDB insert)
        result = await memory_service.save_transcript(
            session_id=req.session_id,
            user_id=user_id,
            avatar_id=req.avatar_id,
            messages=[m.dict() for m in req.messages],
            started_at=req.started_at,
            ended_at=req.ended_at,
            duration_seconds=req.duration_seconds
        )
        
        if result.get("success"):
            # Trigger background memory extraction (fire-and-forget)
            # This invokes Lambda asynchronously - no waiting
            _trigger_memory_extraction_async(req.session_id)
        
        # Return immediately - 202 Accepted
        return {
            "success": True,
            "status": "accepted",
            "session_id": req.session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving transcript: {e}")
        # Still return success - we don't want to block the user
        return {
            "success": True,
            "status": "accepted_with_error",
            "error": str(e)
        }


def _trigger_memory_extraction_async(session_id: str):
    """
    Trigger background Lambda for memory extraction.
    
    This is fire-and-forget - we don't wait for the result.
    If the Lambda isn't available (local dev), we just log and continue.
    """
    try:
        import boto3
        
        # Get Lambda function name - AWS_LAMBDA_FUNCTION_NAME is set automatically in Lambda
        lambda_function = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
        
        # Get region from environment (AWS_REGION is set automatically in Lambda)
        region = os.environ.get('AWS_REGION', 'us-west-1')
        
        if not lambda_function:
            # Local development - skip Lambda invocation
            logger.info(f"Not in Lambda environment, skipping background extraction for {session_id}")
            return
        
        lambda_client = boto3.client('lambda', region_name=region)
        
        # Invoke asynchronously (Event invocation type) - self-invocation
        lambda_client.invoke(
            FunctionName=lambda_function,
            InvocationType='Event',  # Async - returns immediately
            Payload=json.dumps({
                "action": "extract_memories",
                "session_id": session_id
            })
        )
        
        logger.info(f"Triggered memory extraction Lambda for session {session_id} (region: {region})")
        
    except Exception as e:
        # Don't fail - this is best-effort background processing
        logger.warning(f"Could not trigger memory extraction Lambda: {e}")


@router.get("/memory/{avatar_id}")
async def get_voice_memory(
    avatar_id: str,
    request: Request
):
    """
    Get user's memory for voice session (connections, interests, facts, recent conversations).
    
    This is called at session start (in parallel with other fetches).
    Returns quickly - if slow, voice session starts without it.
    """
    import time
    start_time = time.time()
    
    try:
        user = await require_auth(request)
        
        memory_service = VoiceMemoryService(db)
        memory = await memory_service.get_user_memory(user.id, avatar_id)
        
        # Also check for unprocessed transcripts and trigger processing
        unprocessed = await memory_service.get_unprocessed_transcripts(user.id)
        if unprocessed:
            logger.info(f"Found {len(unprocessed)} unprocessed transcripts, triggering background processing")
            for transcript in unprocessed[:3]:  # Limit to 3 at a time
                _trigger_memory_extraction_async(transcript.get("session_id"))
        
        fetch_time_ms = int((time.time() - start_time) * 1000)
        
        # Get user's REAL name (not avatar name) for formatting
        user_doc = await db.users.find_one({"id": user.id}, {"name": 1, "email": 1})
        if user_doc:
            real_name = user_doc.get("name", "")
            if real_name:
                user_name = real_name.split()[0].capitalize()  # First name
            else:
                # Fallback to email prefix
                email = user_doc.get("email", "")
                user_name = email.split("@")[0].split(".")[0].capitalize() if email else "them"
        else:
            user_name = "them"
        
        return {
            "success": True,
            "memory": memory,
            "formatted": memory_service.format_memory_for_prompt(memory, user_name),
            "fetch_time_ms": fetch_time_ms,
            "unprocessed_count": len(unprocessed)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching voice memory: {e}")
        return {
            "success": False,
            "memory": {},
            "formatted": "",
            "error": str(e)
        }
