"""
Workflow Router
API endpoints for workflow operations
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field

from .models.enums import MissionType, MissionStatus, LeadStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SendMessageRequest(BaseModel):
    """Request to send a message in avatar chat"""
    content: str = Field(..., min_length=1, max_length=2000)


class SendMessageResponse(BaseModel):
    """Response from sending a message"""
    success: bool
    session_id: str
    user_message: Dict[str, Any]
    avatar_response: Optional[str]
    intent: Optional[str]
    mission_created: Optional[Dict[str, Any]]


class CreateMissionRequest(BaseModel):
    """Request to create a new mission"""
    type: str = Field(default="matchmaking")
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    criteria: Dict[str, Any] = Field(default_factory=dict)
    strategy: Dict[str, Any] = Field(default_factory=dict)
    auto_start: bool = Field(default=True)


class UpdateLeadRequest(BaseModel):
    """Request to update a lead"""
    status: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)


# ============================================================================
# Dependency Injection
# ============================================================================

def get_services():
    """Get workflow services from app globals"""
    from app.globals import (
        db, azure_client, intelligent_avatar
    )
    from .mcp.tools import WorkflowMCPServer
    from .services.chat_service import ChatService
    from .services.mission_service import MissionService
    from .services.lead_service import LeadService
    
    # Initialize MCP server
    mcp_server = WorkflowMCPServer(db, intelligent_avatar, azure_client)
    
    # Initialize services
    chat_service = ChatService(db, mcp_server, azure_client, intelligent_avatar)
    mission_service = MissionService(db, mcp_server, azure_client)
    lead_service = LeadService(db)
    
    return {
        "db": db,
        "chat_service": chat_service,
        "mission_service": mission_service,
        "lead_service": lead_service,
        "mcp_server": mcp_server
    }


# ============================================================================
# Chat Endpoints
# ============================================================================

@router.post("/chat/{user_id}/session")
async def create_chat_session(user_id: str):
    """Create or get active chat session for user with their avatar"""
    services = get_services()
    
    # Get user to find avatar_id
    user = await services["db"].users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    avatar_id = user_id  # For now, avatar_id = user_id
    
    session = await services["chat_service"].get_or_create_session(user_id, avatar_id)
    
    return {
        "success": True,
        "session_id": session.id,
        "user_id": user_id,
        "avatar_id": avatar_id,
        "is_active": session.is_active,
        "message_count": len(session.messages)
    }


@router.post("/chat/session/{session_id}/message")
async def send_chat_message(session_id: str, request: SendMessageRequest):
    """Send a message in a chat session"""
    services = get_services()
    
    result = await services["chat_service"].send_message(
        session_id=session_id,
        content=request.content
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/chat/{user_id}/history")
async def get_chat_history(
    user_id: str,
    limit: int = Query(default=50, le=100)
):
    """Get chat history for a user"""
    services = get_services()
    
    user = await services["db"].users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    avatar_id = user_id
    
    history = await services["chat_service"].get_chat_history(user_id, avatar_id, limit)
    
    return {
        "success": True,
        "user_id": user_id,
        "messages": history
    }


@router.get("/chat/session/{session_id}")
async def get_chat_session(session_id: str):
    """Get a specific chat session"""
    services = get_services()
    
    session = await services["chat_service"].get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "session": session.dict()
    }


# ============================================================================
# Mission Endpoints
# ============================================================================

@router.post("/missions/{user_id}")
async def create_mission(user_id: str, request: CreateMissionRequest):
    """Create a new mission"""
    services = get_services()
    
    # Validate user
    user = await services["db"].users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Map type string to enum
    type_map = {
        "matchmaking": MissionType.MATCHMAKING,
        "networking": MissionType.NETWORKING,
        "sales_leads": MissionType.SALES_LEADS,
        "job_finder": MissionType.JOB_FINDER,
        "market_research": MissionType.MARKET_RESEARCH,
        "content_discovery": MissionType.CONTENT_DISCOVERY
    }
    mission_type = type_map.get(request.type, MissionType.MATCHMAKING)
    
    mission = await services["mission_service"].create_mission(
        user_id=user_id,
        avatar_id=user_id,  # avatar_id = user_id for now
        mission_type=mission_type,
        name=request.name,
        description=request.description,
        criteria=request.criteria,
        strategy=request.strategy,
        auto_start=request.auto_start
    )
    
    return {
        "success": True,
        "mission_id": mission.id,
        "mission": mission.dict()
    }


@router.get("/missions/{user_id}")
async def list_missions(
    user_id: str,
    status: Optional[str] = None,
    limit: int = Query(default=20, le=50),
    skip: int = Query(default=0, ge=0)
):
    """List missions for a user"""
    services = get_services()
    
    missions = await services["mission_service"].list_missions(
        user_id=user_id,
        status=status,
        limit=limit,
        skip=skip
    )
    
    return {
        "success": True,
        "missions": missions,
        "count": len(missions)
    }


@router.get("/missions/detail/{mission_id}")
async def get_mission(mission_id: str):
    """Get mission details"""
    services = get_services()
    
    mission = await services["mission_service"].get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    return {
        "success": True,
        "mission": mission
    }


@router.get("/missions/detail/{mission_id}/status")
async def get_mission_status(mission_id: str):
    """Get detailed mission status"""
    services = get_services()
    
    status = await services["mission_service"].get_mission_status(mission_id)
    if not status.get("success"):
        raise HTTPException(status_code=404, detail=status.get("error"))
    
    return status


@router.post("/missions/detail/{mission_id}/start")
async def start_mission(mission_id: str):
    """Start a mission"""
    services = get_services()
    
    result = await services["mission_service"].start_mission(mission_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/missions/detail/{mission_id}/pause")
async def pause_mission(mission_id: str):
    """Pause a running mission"""
    services = get_services()
    
    result = await services["mission_service"].pause_mission(mission_id)
    return result


@router.post("/missions/detail/{mission_id}/resume")
async def resume_mission(mission_id: str):
    """Resume a paused mission"""
    services = get_services()
    
    result = await services["mission_service"].resume_mission(mission_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/missions/detail/{mission_id}/cancel")
async def cancel_mission(mission_id: str):
    """Cancel a mission"""
    services = get_services()
    
    result = await services["mission_service"].cancel_mission(mission_id)
    return result


@router.get("/missions/detail/{mission_id}/activities")
async def get_mission_activities(
    mission_id: str,
    limit: int = Query(default=50, le=100)
):
    """Get activities for a mission"""
    services = get_services()
    
    activities = await services["mission_service"].get_mission_activities(mission_id, limit)
    
    return {
        "success": True,
        "activities": activities,
        "count": len(activities)
    }


# ============================================================================
# Lead Endpoints
# ============================================================================

@router.get("/leads/{user_id}")
async def get_user_leads(
    user_id: str,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    skip: int = Query(default=0, ge=0)
):
    """Get all leads for a user"""
    services = get_services()
    
    leads = await services["lead_service"].get_leads_for_user(
        user_id=user_id,
        status=status,
        limit=limit,
        skip=skip
    )
    
    return {
        "success": True,
        "leads": leads,
        "count": len(leads)
    }


@router.get("/leads/mission/{mission_id}")
async def get_mission_leads(
    mission_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    skip: int = Query(default=0, ge=0)
):
    """Get leads for a specific mission"""
    services = get_services()
    
    leads = await services["lead_service"].get_leads_for_mission(
        mission_id=mission_id,
        status=status,
        priority=priority,
        limit=limit,
        skip=skip
    )
    
    return {
        "success": True,
        "leads": leads,
        "count": len(leads)
    }


@router.get("/leads/detail/{lead_id}")
async def get_lead(lead_id: str):
    """Get lead details"""
    services = get_services()
    
    lead = await services["lead_service"].get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {
        "success": True,
        "lead": lead
    }


@router.patch("/leads/detail/{lead_id}")
async def update_lead(lead_id: str, request: UpdateLeadRequest):
    """Update a lead"""
    services = get_services()
    
    results = []
    
    if request.status:
        status_map = {
            "new": LeadStatus.NEW,
            "contacted": LeadStatus.CONTACTED,
            "responding": LeadStatus.RESPONDING,
            "qualified": LeadStatus.QUALIFIED,
            "converted": LeadStatus.CONVERTED,
            "dismissed": LeadStatus.DISMISSED,
            "stale": LeadStatus.STALE
        }
        status_enum = status_map.get(request.status)
        if status_enum:
            result = await services["lead_service"].update_lead_status(lead_id, status_enum)
            results.append(result)
    
    if request.notes is not None:
        result = await services["lead_service"].add_user_notes(lead_id, request.notes)
        results.append(result)
    
    if request.rating is not None:
        result = await services["lead_service"].rate_lead(lead_id, request.rating)
        results.append(result)
    
    return {
        "success": all(r.get("success") for r in results),
        "lead_id": lead_id,
        "updates": len(results)
    }


@router.post("/leads/detail/{lead_id}/follow-up")
async def mark_lead_followed_up(lead_id: str):
    """Mark a lead as followed up"""
    services = get_services()
    
    result = await services["lead_service"].mark_followed_up(lead_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/leads/detail/{lead_id}/dismiss")
async def dismiss_lead(lead_id: str, reason: str = Body(default="")):
    """Dismiss a lead"""
    services = get_services()
    
    result = await services["lead_service"].dismiss_lead(lead_id, reason)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/leads/{user_id}/stats")
async def get_lead_stats(user_id: str):
    """Get lead statistics for a user"""
    services = get_services()
    
    stats = await services["lead_service"].get_lead_stats(user_id)
    
    return {
        "success": True,
        "stats": stats
    }


@router.get("/leads/{user_id}/top")
async def get_top_leads(
    user_id: str,
    limit: int = Query(default=10, le=50)
):
    """Get top leads by score"""
    services = get_services()
    
    leads = await services["lead_service"].get_top_leads(user_id, limit)
    
    return {
        "success": True,
        "leads": leads,
        "count": len(leads)
    }


# ============================================================================
# Workflow Types/Templates
# ============================================================================

@router.get("/types")
async def get_workflow_types():
    """Get available workflow types"""
    return {
        "success": True,
        "types": [
            {
                "id": "matchmaking",
                "name": "Find Matches",
                "description": "Find people with similar interests and compatible personalities",
                "icon": "💕",
                "default_criteria": {
                    "min_compatibility_score": 60,
                    "exclude_existing_friends": True
                },
                "default_strategy": {
                    "approach": "casual",
                    "max_targets": 50,
                    "max_conversations": 10
                }
            },
            {
                "id": "networking",
                "name": "Networking",
                "description": "Connect with professionals in your field of interest",
                "icon": "🤝",
                "default_criteria": {
                    "min_compatibility_score": 50,
                    "exclude_existing_friends": True
                },
                "default_strategy": {
                    "approach": "professional",
                    "max_targets": 30,
                    "max_conversations": 5
                }
            },
            {
                "id": "sales_leads",
                "name": "Find Sales Leads",
                "description": "Identify potential customers or business opportunities",
                "icon": "💼",
                "default_criteria": {
                    "min_compatibility_score": 40
                },
                "default_strategy": {
                    "approach": "professional",
                    "max_targets": 100,
                    "max_conversations": 0
                }
            },
            {
                "id": "job_finder",
                "name": "Job Opportunities",
                "description": "Find people who might help with job opportunities",
                "icon": "💼",
                "default_criteria": {
                    "min_compatibility_score": 50
                },
                "default_strategy": {
                    "approach": "professional",
                    "max_targets": 50,
                    "max_conversations": 5
                }
            }
        ]
    }

