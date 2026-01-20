"""
Bonding Workflow Routes
API endpoints for bonding interactions
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow/bonding", tags=["bonding"])


# ============================================================================
# Request/Response Models
# ============================================================================

class BondingTriggerRequest(BaseModel):
    """Request to trigger a bonding workflow"""
    user_id: str
    avatar_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class BondingFeedbackRequest(BaseModel):
    """Request to submit feedback on bonding interaction"""
    session_id: str
    rating: int = Field(..., ge=1, le=5)
    helpful: bool
    comments: Optional[str] = None


# ============================================================================
# Dependency Injection
# ============================================================================

def get_services():
    """Get workflow services from app globals"""
    from app.globals import db, azure_client, intelligent_avatar
    from domain.workflow.mcp.tools import WorkflowMCPServer
    
    # Initialize MCP server
    mcp_server = WorkflowMCPServer(db, intelligent_avatar, azure_client)
    
    return {
        "db": db,
        "mcp_server": mcp_server,
        "intelligent_avatar": intelligent_avatar
    }


# ============================================================================
# Bonding Endpoints
# ============================================================================

@router.post("/trigger")
async def trigger_bonding_workflow(request: BondingTriggerRequest):
    """Trigger a bonding workflow for deepening user-avatar relationship"""
    try:
        from domain.workflow.engines.engine_registry import WorkflowEngineRegistry
        from domain.workflow.engines.base_engine import WorkflowState
        from domain.workflow.models.enums import MissionType
        
        services = get_services()
        db = services["db"]
        
        # Get or create bonding session
        if request.session_id:
            session = await db.bonding_sessions.find_one({"id": request.session_id})
        else:
            session = None
        
        # Initialize bonding engine
        bonding_engine = WorkflowEngineRegistry.get_engine(
            "bonding",
            db=db,
            mcp_server=services["mcp_server"],
            intelligent_avatar=services["intelligent_avatar"]
        )
        
        # Execute bonding workflow with correct signature
        result = await bonding_engine.execute(
            user_id=request.user_id,
            avatar_id=request.avatar_id,
            user_message=request.message,
            session_id=request.session_id
        )
        
        # result is already a dict from BondingWorkflowEngine
        return {
            "success": True,
            "type": "bonding",
            **result  # Spread the result dict
        }
        
    except Exception as e:
        logger.error(f"Bonding workflow failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_bonding_feedback(request: BondingFeedbackRequest):
    """Submit user feedback on a bonding interaction"""
    try:
        from domain.workflow.services.delight_scorer import UserDelightScorer
        
        services = get_services()
        db = services["db"]
        
        # Get session
        session = await db.bonding_sessions.find_one({"id": request.session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update session with feedback
        await db.bonding_sessions.update_one(
            {"id": request.session_id},
            {
                "$set": {
                    "user_feedback": {
                        "rating": request.rating,
                        "helpful": request.helpful,
                        "comments": request.comments
                    }
                }
            }
        )
        
        # Recompute delight score with feedback
        scorer = UserDelightScorer(db)
        await scorer.update_delight_trend(
            user_id=session["user_id"],
            avatar_id=session["avatar_id"],
            session_data=session,
            feedback={
                "rating": request.rating,
                "helpful": request.helpful
            }
        )
        
        return {
            "success": True,
            "message": "Feedback recorded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit bonding feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state/{avatar_id}")
async def get_bonding_state(avatar_id: str, user_id: str = Query(...)):
    """Get current bonding state for user-avatar relationship"""
    try:
        services = get_services()
        db = services["db"]
        
        # Get bonding state
        state = await db.avatar_bonding_state.find_one({
            "user_id": user_id,
            "avatar_id": avatar_id
        })
        
        if not state:
            return {
                "exists": False,
                "message": "No bonding state found"
            }
        
        # Remove MongoDB _id
        state.pop("_id", None)
        
        return {
            "exists": True,
            "state": state
        }
        
    except Exception as e:
        logger.error(f"Failed to get bonding state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_bonding_session(session_id: str):
    """Get details of a specific bonding session"""
    try:
        services = get_services()
        db = services["db"]
        
        session = await db.bonding_sessions.find_one({"id": session_id})
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Remove MongoDB _id
        session.pop("_id", None)
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get bonding session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_bonding_sessions(
    user_id: str = Query(...),
    avatar_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100)
):
    """List bonding sessions for a user"""
    try:
        services = get_services()
        db = services["db"]
        
        query = {"user_id": user_id}
        if avatar_id:
            query["avatar_id"] = avatar_id
        
        sessions = await db.bonding_sessions.find(query).sort(
            [("start_time", -1)]
        ).limit(limit).to_list(None)
        
        # Remove MongoDB _id from each
        for session in sessions:
            session.pop("_id", None)
        
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Failed to list bonding sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
