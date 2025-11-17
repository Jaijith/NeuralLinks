"""
Avatar Routes - Avatar generation, activity, and configuration
"""

from fastapi import APIRouter, Request, HTTPException, Query
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
import logging

from core.auth import require_auth
from core.database import get_database

db = get_database()
router = APIRouter(prefix="/api", tags=["avatar"])
logger = logging.getLogger(__name__)


def get_intelligent_avatar():
    """Get IntelligentAvatar instance"""
    from app.globals import intelligent_avatar
    return intelligent_avatar


@router.get("/avatar/activity-feed/{user_id}")
async def get_avatar_activity_feed(user_id: str, request: Request):
    """Get avatar's activity feed"""
    _ = await require_auth(request)
    
    # Get avatar's conversations
    conversations = await db.agent_conversations.find({
        "$or": [
            {"agent1_user_id": user_id},
            {"agent2_user_id": user_id}
        ]
    }, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    
    # Enrich with user data
    activities = []
    for conv in conversations:
        other_user_id = conv['agent2_user_id'] if conv['agent1_user_id'] == user_id else conv['agent1_user_id']
        other_user = await db.users.find_one({"id": other_user_id}, {"_id": 0})
        
        if other_user:
            activities.append({
                "type": "conversation",
                "timestamp": conv.get('created_at'),
                "other_user": {
                    "id": other_user['id'],
                    "name": other_user['name'],
                    "picture": other_user.get('picture')
                },
                "score": conv.get('overall_score', conv.get('compatibility_score', 0)),
                "status": conv.get('status'),
                "message_count": len(conv.get('messages', []))
            })
    
    return activities


@router.get("/avatar/conversations")
async def get_avatar_conversations(request: Request):
    """Get all avatar conversations for current user"""
    user = await require_auth(request)
    
    conversations = await db.agent_conversations.find({
        "$or": [
            {"agent1_user_id": user.id},
            {"agent2_user_id": user.id}
        ]
    }, {"_id": 0}).sort("updated_at", -1).to_list(100)
    
    # Enrich with user data
    for conv in conversations:
        other_user_id = conv['agent2_user_id'] if conv['agent1_user_id'] == user.id else conv['agent1_user_id']
        other_user = await db.users.find_one({"id": other_user_id}, {"_id": 0})
        
        if other_user:
            conv['other_user'] = {
                "id": other_user['id'],
                "name": other_user['name'],
                "picture": other_user.get('picture'),
                "bio": other_user.get('bio')
            }
    
    return conversations


@router.post("/avatar/generate-post")
async def generate_avatar_post(request: Request, post_type: str = "general"):
    """Generate intelligent avatar post using Graph RAG"""
    user = await require_auth(request)
    
    intelligent_avatar = get_intelligent_avatar()
    result = await intelligent_avatar.generate_avatar_post(user.id, post_type)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.post("/avatar/chat-response")
async def generate_avatar_chat_response(request: Request, data: Dict[str, Any]):
    """Generate intelligent avatar chat response"""
    user = await require_auth(request)
    
    other_user_id = data.get("other_user_id")
    conversation_history = data.get("conversation_history", [])
    last_message = data.get("last_message", "")
    
    if not other_user_id or not last_message:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    intelligent_avatar = get_intelligent_avatar()
    result = await intelligent_avatar.generate_chat_response(
        user.id, other_user_id, conversation_history, last_message
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.post("/avatar/generate-bio")
async def generate_avatar_bio(request: Request):
    """Generate avatar bio from graph data"""
    user = await require_auth(request)
    
    intelligent_avatar = get_intelligent_avatar()
    result = await intelligent_avatar.generate_avatar_profile_bio(user.id)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/avatar/conversation-starters/{other_user_id}")
async def get_conversation_starters(other_user_id: str, request: Request):
    """Get AI-generated conversation starters"""
    user = await require_auth(request)
    
    intelligent_avatar = get_intelligent_avatar()
    starters = await intelligent_avatar.suggest_conversation_starters(user.id, other_user_id, count=3)
    
    return {"starters": starters}


@router.get("/avatar/match-explanation/{match_user_id}")
async def get_match_explanation(match_user_id: str, request: Request):
    """Get explanation for match compatibility"""
    user = await require_auth(request)
    
    intelligent_avatar = get_intelligent_avatar()
    explanation = await intelligent_avatar.generate_match_explanation(user.id, match_user_id)
    
    return {"explanation": explanation}


@router.get("/avatar/config")
async def get_avatar_config(request: Request):
    """Get current user's avatar autonomy configuration"""
    current_user = await require_auth(request)
    
    from domain.avatar.config import ARCHETYPES
    
    # Get full user document from database
    user_doc = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return current config
    config = {
        "user_id": user_doc.get('id'),
        "avatar_name": user_doc.get('avatar_name'),
        "avatar_picture": user_doc.get('avatar_picture'),
        
        # Autonomy settings
        "avatar_autonomous": user_doc.get('avatar_autonomous', False),
        "avatar_activity_level": user_doc.get('avatar_activity_level', 'medium'),
        "archetype": user_doc.get('archetype', 'casual_observer'),
        "archetype_config": user_doc.get('archetype_config', {}),
        
        # Status
        "last_activity": user_doc.get('last_activity'),
        "autonomous_enabled_at": user_doc.get('autonomous_enabled_at'),
        
        # Available options
        "available_archetypes": list(ARCHETYPES.keys()),
        "activity_levels": ["hypo", "low", "medium", "high"]
    }
    
    return config


@router.put("/avatar/config")
async def update_avatar_config(
    request: Request,
    avatar_autonomous: bool = None,
    avatar_activity_level: str = None,
    archetype: str = None
):
    """Update avatar autonomy configuration"""
    current_user = await require_auth(request)
    
    from domain.avatar.config import get_archetype_config
    
    update_fields = {}
    
    # Update autonomy flag
    if avatar_autonomous is not None:
        update_fields['avatar_autonomous'] = avatar_autonomous
        if avatar_autonomous:
            update_fields['autonomous_enabled_at'] = datetime.now(timezone.utc).isoformat()
    
    # Update activity level
    if avatar_activity_level:
        if avatar_activity_level not in ['hypo', 'low', 'medium', 'high']:
            raise HTTPException(status_code=400, detail="Invalid activity level")
        update_fields['avatar_activity_level'] = avatar_activity_level
    
    # Update archetype
    if archetype:
        try:
            config = get_archetype_config(archetype)
            update_fields['archetype'] = archetype
            update_fields['archetype_config'] = config
        except KeyError:
            raise HTTPException(status_code=400, detail="Invalid archetype")
    
    # Perform update
    if update_fields:
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": update_fields}
        )
    
    # Return updated config
    updated_user = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    
    return {
        "message": "Avatar configuration updated",
        "config": {
            "avatar_autonomous": updated_user.get('avatar_autonomous'),
            "avatar_activity_level": updated_user.get('avatar_activity_level'),
            "archetype": updated_user.get('archetype')
        }
    }


@router.get("/avatar/activity")
async def get_avatar_activity(request: Request, limit: int = 20):
    """Get recent activity for current user's avatar"""
    current_user = await require_auth(request)
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Fetching activities for user: {current_user.id}")
    
    # Get recent activities from autonomous_activities collection
    activities_raw = await db.autonomous_activities.find({
        "$or": [
            {"bot_id": current_user.id},
            {"user_id": current_user.id}
        ]
    }, {"_id": 0}).sort([("timestamp", -1)]).limit(limit).to_list(limit)
    
    logger.info(f"Found {len(activities_raw)} activities for user {current_user.id}")
    
    # Format activities for frontend
    activities = []
    for act in activities_raw:
        # Map activity_type to action_type for frontend
        action_type = act.get("action_type") or act.get("activity_type", "unknown")
        # Map post_created -> post, post_comment -> comment, post_like -> like
        if action_type == "post_created":
            action_type = "post"
        elif action_type == "post_comment":
            action_type = "comment"
        elif action_type == "post_like":
            action_type = "like"
        
        activities.append({
            "action_type": action_type,
            "description": act.get("description", "Activity"),
            "timestamp": act.get("timestamp", "")
        })
    
    logger.info(f"Returning {len(activities)} formatted activities")
    
    # Get post counts
    real_posts = await db.posts.count_documents({
        "user_id": current_user.id,
        "post_type": "real"
    })
    
    avatar_posts = await db.posts.count_documents({
        "user_id": current_user.id,
        "post_type": "avatar"
    })
    
    return {
        "activities": activities,
        "statistics": {
            "real_posts": real_posts,
            "avatar_posts": avatar_posts,
            "recent_actions": len(activities)
        }
    }


@router.get("/avatar/status")
async def get_avatar_status(request: Request):
    """Get current status of avatar (active, last seen, etc.)"""
    current_user = await require_auth(request)
    
    # Get full user document from database
    user_doc = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if avatar is configured
    has_avatar = bool(
        user_doc.get('avatar_name') and 
        user_doc.get('avatar_picture')
    )
    
    # Check if autonomous
    is_autonomous = user_doc.get('avatar_autonomous', False)
    
    # Get last activity
    last_activity = user_doc.get('last_activity')
    
    # Get recent action count (last hour)
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    
    recent_actions = await db.autonomous_activities.count_documents({
        "bot_id": current_user.id,
        "timestamp": {"$gte": one_hour_ago}
    })
    
    return {
        "has_avatar": has_avatar,
        "is_autonomous": is_autonomous,
        "archetype": user_doc.get('archetype', 'Not set'),
        "activity_level": user_doc.get('avatar_activity_level', 'Not set'),
        "last_activity": last_activity,
        "actions_last_hour": recent_actions,
        "status": "active" if is_autonomous else "inactive"
    }

