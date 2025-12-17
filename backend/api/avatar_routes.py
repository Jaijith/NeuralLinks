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
    from app.globals import get_agent_runner
    
    update_fields = {}
    autonomy_changed = False
    new_autonomy_state = None
    
    # Update autonomy flag
    if avatar_autonomous is not None:
        update_fields['avatar_autonomous'] = avatar_autonomous
        autonomy_changed = True
        new_autonomy_state = avatar_autonomous
        if avatar_autonomous:
            update_fields['autonomous_enabled_at'] = datetime.now(timezone.utc).isoformat()
        else:
            update_fields['autonomous_disabled_at'] = datetime.now(timezone.utc).isoformat()
    
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
    
    # Start or stop autonomous agent based on autonomy toggle
    agent_status = None
    if autonomy_changed:
        agent_runner = get_agent_runner()
        if agent_runner:
            if new_autonomy_state:
                # Autonomy enabled - start the agent
                logger.info(f"🚀 Starting autonomous agent for user {current_user.id}")
                success = await agent_runner.start_agent(current_user.id)
                agent_status = "started" if success else "failed_to_start"
                if success:
                    logger.info(f"✅ Autonomous agent started for user {current_user.id}")
                else:
                    logger.warning(f"⚠️ Failed to start autonomous agent for user {current_user.id}")
            else:
                # Autonomy disabled - stop the agent
                logger.info(f"⏹️ Stopping autonomous agent for user {current_user.id}")
                success = await agent_runner.stop_agent(current_user.id)
                agent_status = "stopped" if success else "was_not_running"
                if success:
                    logger.info(f"✅ Autonomous agent stopped for user {current_user.id}")
        else:
            logger.warning("⚠️ Agent runner not available - autonomous mode won't work")
            agent_status = "runner_not_available"
    
    # Return updated config
    updated_user = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    
    response = {
        "message": "Avatar configuration updated",
        "config": {
            "avatar_autonomous": updated_user.get('avatar_autonomous'),
            "avatar_activity_level": updated_user.get('avatar_activity_level'),
            "archetype": updated_user.get('archetype')
        }
    }
    
    # Include agent status if autonomy was toggled
    if agent_status:
        response["agent_status"] = agent_status
    
    return response


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
    from app.globals import get_agent_runner
    
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
    
    # Check if agent is actually running
    agent_runner = get_agent_runner()
    is_agent_running = False
    agent_details = None
    if agent_runner:
        is_agent_running = agent_runner.is_agent_running(current_user.id)
        if is_agent_running:
            agent_details = await agent_runner.get_agent_status(current_user.id)
    
    # Get last activity
    last_activity = user_doc.get('last_activity')
    
    # Get recent action count (last hour)
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    
    recent_actions = await db.autonomous_activities.count_documents({
        "bot_id": current_user.id,
        "timestamp": {"$gte": one_hour_ago}
    })
    
    # Determine actual status
    if is_autonomous and is_agent_running:
        status = "running"  # Autonomy enabled AND agent is actively running
    elif is_autonomous and not is_agent_running:
        status = "enabled_not_running"  # Autonomy enabled but agent not running (needs restart)
    else:
        status = "inactive"  # Autonomy disabled
    
    return {
        "has_avatar": has_avatar,
        "is_autonomous": is_autonomous,
        "is_agent_running": is_agent_running,
        "archetype": user_doc.get('archetype', 'Not set'),
        "activity_level": user_doc.get('avatar_activity_level', 'Not set'),
        "last_activity": last_activity,
        "actions_last_hour": recent_actions,
        "status": status,
        "agent_details": agent_details
    }


@router.get("/avatar/state")
async def get_avatar_state(request: Request):
    """Get current avatar state (mood, state machine state, etc.) for memory orb visualization"""
    current_user = await require_auth(request)
    
    try:
        from domain.avatar.state import StateManager
        from domain.avatar.state_machine import AvatarStateMachine
        
        state_manager = StateManager(db)
        state_machine = AvatarStateMachine(db, state_manager=state_manager)
        
        # Get current state
        current_state, sub_states = await state_machine.get_current_state(current_user.id)
        
        # Get state summary (includes mood, energy, etc.)
        state_summary = await state_machine.get_state_summary(current_user.id)
        
        return {
            "success": True,
            "current_state": current_state.value if current_state else "passive",
            "sub_states": sub_states,
            "mood": state_summary.get("internal_state", {}).get("mood", "neutral"),
            "energy_level": state_summary.get("internal_state", {}).get("energy_level", 0.5),
            "social_desire": state_summary.get("internal_state", {}).get("social_desire", 0.5),
            "creative_urge": state_summary.get("internal_state", {}).get("creative_urge", 0.5),
            "state_summary": state_summary
        }
    except Exception as e:
        logger.error(f"Error getting avatar state: {e}")
        # Return default state if error
        return {
            "success": False,
            "current_state": "passive",
            "mood": "neutral",
            "energy_level": 0.5,
            "social_desire": 0.5,
            "creative_urge": 0.5,
            "error": str(e)
        }


@router.get("/avatar/memory-nodes")
async def get_avatar_memory_nodes(request: Request, limit: int = 100):
    """Get knowledge graph nodes for avatar memory visualization"""
    current_user = await require_auth(request)
    
    try:
        # Get graph nodes for this user
        nodes = await db.graph_nodes.find(
            {"user_id": current_user.id},
            {"_id": 0}
        ).limit(limit).to_list(limit)
        
        # Get edges for these nodes
        node_ids = [n["id"] for n in nodes]
        edges = await db.graph_edges.find(
            {"$or": [
                {"from_node_id": {"$in": node_ids}},
                {"to_node_id": {"$in": node_ids}}
            ]},
            {"_id": 0}
        ).limit(500).to_list(500)
        
        return {
            "success": True,
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }
    except Exception as e:
        logger.error(f"Error getting memory nodes: {e}")
        return {
            "success": False,
            "nodes": [],
            "edges": [],
            "error": str(e)
        }


@router.get("/avatar/full-memory")
async def get_avatar_full_memory(request: Request):
    """
    Get comprehensive memory context for enhanced Memory Spirit visualization
    
    Returns:
    - Semantic memory (interests, traits, values from knowledge graph)
    - Procedural memory (action patterns, success rates)
    - Episodic memory (experiences, emotional history)
    - Recent activities
    """
    current_user = await require_auth(request)
    
    try:
        from domain.avatar.memory import MemoryManager
        
        memory_manager = MemoryManager(db)
        
        # Get full memory context
        memory_context = await memory_manager.get_full_memory_context(current_user.id)
        
        # Get recent activities for visualization
        recent_activities = await db.autonomous_activities.find(
            {"$or": [{"bot_id": current_user.id}, {"user_id": current_user.id}]},
            {"_id": 0}
        ).sort("timestamp", -1).limit(10).to_list(10)
        
        # Get action memory stats
        action_patterns = memory_context.get("procedural_memory", {}).get("action_patterns", {})
        
        # Get recent experiences
        episodic = memory_context.get("episodic_memory", {})
        emotional_state = episodic.get("emotional_state", {})
        
        return {
            "success": True,
            
            # Semantic Memory (Knowledge Graph)
            "semantic_memory": memory_context.get("semantic_memory", {}),
            
            # Procedural Memory (Action History)
            "procedural_memory": {
                "total_actions": action_patterns.get("total_actions", 0),
                "action_counts": action_patterns.get("action_counts", {}),
                "success_rates": action_patterns.get("success_rates", {}),
                "best_performing": action_patterns.get("best_performing"),
                "worst_performing": action_patterns.get("worst_performing"),
                "recent_actions": memory_context.get("procedural_memory", {}).get("recent_actions", [])
            },
            
            # Episodic Memory (Experiences)
            "episodic_memory": {
                "total_experiences": emotional_state.get("total_experiences", 0),
                "emotional_trend": emotional_state.get("emotional_trend", "stable"),
                "avg_emotional_valence": emotional_state.get("avg_emotional_valence", 0),
                "recent_highlights": emotional_state.get("recent_highlights", []),
                "experience_breakdown": emotional_state.get("experience_breakdown", {})
            },
            
            # Recent Activities
            "recent_activities": [
                {
                    "action_type": a.get("action_type", a.get("activity_type", "unknown")),
                    "description": a.get("description", ""),
                    "timestamp": a.get("timestamp", "")
                }
                for a in recent_activities
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting full memory: {e}")
        return {
            "success": False,
            "error": str(e),
            "semantic_memory": {"interests": [], "traits": [], "values": []},
            "procedural_memory": {"total_actions": 0, "action_counts": {}, "success_rates": {}},
            "episodic_memory": {"total_experiences": 0, "emotional_trend": "stable"},
            "recent_activities": []
        }


@router.post("/avatar/run-autonomous-cycle")
async def run_autonomous_cycle(request: Request, api_key: str = None):
    """
    Run one autonomous cycle for all enabled avatars.
    This endpoint is called by AWS EventBridge on a schedule.
    
    Security: Requires either valid auth or a secret API key for EventBridge.
    """
    import os
    
    # Check for EventBridge secret key (for scheduled invocations)
    eventbridge_key = os.environ.get('EVENTBRIDGE_API_KEY', 'neurallinks-autonomous-trigger-2024')
    
    # Allow either authenticated user or EventBridge API key
    is_eventbridge = api_key == eventbridge_key
    
    if not is_eventbridge:
        try:
            # Try to authenticate as a user (for manual testing)
            await require_auth(request)
        except:
            logger.warning("Unauthorized autonomous cycle attempt")
            raise HTTPException(status_code=401, detail="Unauthorized")
    
    logger.info("🤖 Starting autonomous cycle triggered by EventBridge")
    
    try:
        from domain.avatar.state_aware_agent import StateAwareAgent
        from domain.avatar.intelligent import IntelligentAvatar
        from domain.graph.rag import GraphRAG
        from app.globals import openai_client, OPENAI_MODEL, graph_rag, intelligent_avatar
        
        # Find all users with autonomy enabled
        query = {
            "avatar_autonomous": True,
            "avatar_name": {"$exists": True, "$ne": None},
            "avatar_picture": {"$exists": True, "$ne": None},
            "is_bot": {"$ne": True}  # Only real users, not bots
        }
        
        users = await db.users.find(query, {"_id": 0}).to_list(100)
        
        if not users:
            logger.info("ℹ️ No users with autonomy enabled")
            return {
                "success": True,
                "message": "No users with autonomy enabled",
                "processed": 0
            }
        
        logger.info(f"📊 Found {len(users)} user(s) with autonomy enabled")
        
        # Process each avatar
        results = []
        processed = 0
        errors = 0
        
        for user in users:
            user_id = user.get('id')
            avatar_name = user.get('avatar_name', 'Unknown')
            
            try:
                # Create agent for this user
                agent = StateAwareAgent(
                    bot=user,
                    db=db,
                    intelligent_avatar=intelligent_avatar
                )
                
                # Initialize the agent
                await agent.initialize()
                
                # Run ONE cycle (not continuous)
                await agent._run_single_cycle()
                
                results.append({
                    "user_id": user_id,
                    "avatar_name": avatar_name,
                    "status": "success"
                })
                processed += 1
                logger.info(f"✅ Processed {avatar_name}")
                
            except Exception as e:
                logger.error(f"❌ Error processing {avatar_name}: {e}")
                results.append({
                    "user_id": user_id,
                    "avatar_name": avatar_name,
                    "status": "error",
                    "error": str(e)
                })
                errors += 1
        
        logger.info(f"✅ Autonomous cycle complete: {processed} processed, {errors} errors")
        
        return {
            "success": True,
            "message": f"Processed {processed} avatars",
            "processed": processed,
            "errors": errors,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"❌ Autonomous cycle failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

