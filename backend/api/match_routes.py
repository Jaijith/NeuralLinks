"""
Match Routes - User matching and discovery
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone
import logging

from core.auth import require_auth
from core.database import get_database
from api.models import Match, AgentConversation

db = get_database()
router = APIRouter(prefix="/api", tags=["matches"])
logger = logging.getLogger(__name__)


def get_openai_client():
    """Get OpenAI client"""
    from app.globals import openai_client
    return openai_client

def get_azure_client():
    """Get OpenAI client (alias for backwards compatibility)"""
    return get_openai_client()

def get_openai_model():
    """Get OpenAI model name"""
    from app.globals import OPENAI_MODEL
    return OPENAI_MODEL  # Has default in config.py

def get_azure_deployment():
    """Get OpenAI model name (alias for backwards compatibility)"""
    return get_openai_model()


@router.get("/matches")
async def get_matches(request: Request):
    """Get user's matches"""
    user = await require_auth(request)
    
    matches = await db.matches.find({"user_id": user.id}, {"_id": 0}).to_list(100)
    
    # Enrich with user data
    for match in matches:
        matched_user = await db.users.find_one({"id": match['matched_user_id']}, {"_id": 0})
        if matched_user:
            match['matched_user'] = {
                "name": matched_user['name'],
                "picture": matched_user.get('picture'),
                "age": matched_user.get('age'),
                "bio": matched_user.get('bio')
            }
    
    return matches


@router.post("/matches/discover")
async def discover_matches(request: Request):
    """Discover potential matches using AI agents"""
    user = await require_auth(request)
    
    # Get other users with completed profiles
    other_users = await db.users.find({
        "id": {"$ne": user.id},
        "profile_completed": True
    }, {"_id": 0}).to_list(50)
    
    matches = []
    
    for other_user in other_users[:5]:  # Limit to 5 for demo
        # Check if already matched
        existing = await db.matches.find_one({
            "user_id": user.id,
            "matched_user_id": other_user['id']
        })
        
        if existing:
            continue
        
        # Start agent conversation
        try:
            # Simplified matching logic
            shared_interests = list(set(user.interests) & set(other_user.get('interests', [])))
            compatibility = min(len(shared_interests) * 20, 100)
            
            if compatibility > 30:  # Threshold
                match = Match(
                    user_id=user.id,
                    matched_user_id=other_user['id'],
                    compatibility_score=compatibility,
                    shared_interests=shared_interests,
                    personality_compatibility=compatibility * 0.8,
                    conversation_quality=compatibility * 0.9,
                    agent_conversation_id=""
                )
                
                match_dict = match.model_dump()
                match_dict['created_at'] = match_dict['created_at'].isoformat()
                await db.matches.insert_one(match_dict)
                
                matches.append(match)
        except Exception as e:
            logger.error(f"Error creating match: {str(e)}")
    
    return matches


@router.get("/matches/{match_id}/conversation")
async def get_agent_conversation(match_id: str, request: Request):
    """Get AI agent conversation for a match"""
    user = await require_auth(request)
    
    match = await db.matches.find_one({"id": match_id, "user_id": user.id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if match.get('agent_conversation_id'):
        conversation = await db.agent_conversations.find_one(
            {"id": match['agent_conversation_id']},
            {"_id": 0}
        )
        return conversation
    
    return {"messages": [], "summary": "No conversation yet"}

