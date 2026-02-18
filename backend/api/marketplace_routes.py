"""
Siddhi Bazaar - API Routes
REST endpoints for the marketplace.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketplace", tags=["Siddhi Bazaar"])


def get_service(request: Request):
    """Get marketplace service from app state"""
    return request.app.state.marketplace_service


async def get_user_from_request(request: Request):
    """Extract authenticated user from request"""
    from core.auth import get_current_user
    return await get_current_user(request)


def extract_user_id(user) -> str:
    """Extract user ID from User model or dict"""
    if hasattr(user, 'id'):
        return user.id
    if isinstance(user, dict):
        return user.get("id", "")
    return str(user)


class InstallRequest(BaseModel):
    pass


class ToggleRequest(BaseModel):
    enabled: bool


class ReviewRequest(BaseModel):
    rating: int
    review_text: str = ""


class ConsultRequest(BaseModel):
    query: str
    agent_user_id: Optional[str] = None
    source: str = "chat"


# ── Catalog ────────────────────────────────────────────

@router.get("/skills")
async def search_skills(
    request: Request,
    query: Optional[str] = None,
    category: Optional[str] = None,
    tier: Optional[str] = None,
    skill_type: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Search and filter skills"""
    service = get_service(request)
    return await service.search_skills(
        query=query, category=category, tier=tier,
        skill_type=skill_type, page=page, limit=limit,
    )


@router.get("/skills/{skill_id}")
async def get_skill(request: Request, skill_id: str):
    """Get skill detail by ID"""
    service = get_service(request)
    skill = await service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.get("/categories")
async def get_categories(request: Request):
    """List all categories with skill counts"""
    service = get_service(request)
    return await service.get_categories()


@router.get("/featured")
async def get_featured(request: Request):
    """Get featured skills"""
    service = get_service(request)
    return await service.get_featured_skills()


@router.get("/popular")
async def get_popular(request: Request, limit: int = Query(default=10, ge=1, le=50)):
    """Get most installed skills"""
    service = get_service(request)
    return await service.get_popular_skills(limit)


@router.get("/recommended")
async def get_recommended(request: Request):
    """Get personalized skill recommendations"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    recommender = request.app.state.skill_recommender
    return await recommender.get_recommendations(extract_user_id(user))


# ── Installation ───────────────────────────────────────

@router.get("/installed")
async def get_installed(request: Request):
    """Get installed skills for the current user"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = get_service(request)
    return await service.get_installed_skills(extract_user_id(user))


@router.post("/install/{skill_id}")
async def install_skill(request: Request, skill_id: str):
    """Install a skill"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = get_service(request)
    result = await service.install_skill(extract_user_id(user), skill_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.reason)

    return {"success": True, "installation_id": result.installation_id, "message": result.reason or "Skill installed"}


@router.delete("/uninstall/{skill_id}")
async def uninstall_skill(request: Request, skill_id: str):
    """Uninstall a skill"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = get_service(request)
    success = await service.uninstall_skill(extract_user_id(user), skill_id)

    if not success:
        raise HTTPException(status_code=404, detail="Installation not found")

    return {"success": True, "message": "Skill uninstalled"}


@router.patch("/toggle/{skill_id}")
async def toggle_skill(request: Request, skill_id: str, body: ToggleRequest):
    """Toggle a skill on/off"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = get_service(request)
    success = await service.toggle_skill(extract_user_id(user), skill_id, body.enabled)

    if not success:
        raise HTTPException(status_code=404, detail="Installation not found")

    return {"success": True, "enabled": body.enabled}


# ── Reviews ────────────────────────────────────────────

@router.get("/skills/{skill_id}/reviews")
async def get_reviews(
    request: Request,
    skill_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Get reviews for a skill"""
    service = get_service(request)
    return await service.get_reviews(skill_id, page, limit)


@router.post("/skills/{skill_id}/review")
async def submit_review(request: Request, skill_id: str, body: ReviewRequest):
    """Submit a review"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if body.rating < 1 or body.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    service = get_service(request)
    review = await service.rate_skill(extract_user_id(user), skill_id, body.rating, body.review_text)
    return review


# ── AI Agent Subscriptions ─────────────────────────────

@router.get("/agents")
async def get_ai_agents(request: Request):
    """Get all available AI Agent Assistants"""
    service = get_service(request)
    return await service.get_ai_agents()


@router.get("/agents/subscribed")
async def get_subscribed_agents(request: Request):
    """Get the current user's subscribed agents"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = get_service(request)
    return await service.get_subscribed_agents(extract_user_id(user))


@router.post("/agents/subscribe/{skill_id}")
async def subscribe_agent(request: Request, skill_id: str):
    """Subscribe to an AI Agent Assistant"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = get_service(request)
    result = await service.subscribe_agent(extract_user_id(user), skill_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to subscribe"))

    return result


@router.post("/agents/unsubscribe/{skill_id}")
async def unsubscribe_agent(request: Request, skill_id: str):
    """Unsubscribe from an AI Agent Assistant"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = get_service(request)
    result = await service.unsubscribe_agent(extract_user_id(user), skill_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to unsubscribe"))

    return result


@router.patch("/agents/toggle/{skill_id}")
async def toggle_agent(request: Request, skill_id: str, body: ToggleRequest):
    """Toggle an AI Agent on/off"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = get_service(request)
    result = await service.toggle_agent(extract_user_id(user), skill_id, body.enabled)

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Agent not found"))

    return result


# ── A2A Consultation ──────────────────────────────────

@router.post("/agents/consult")
async def consult_agent(request: Request, body: ConsultRequest):
    """
    Consult an AI Agent Assistant via A2A protocol.
    If agent_user_id is provided, consults that specific agent.
    Otherwise, auto-selects the best agent for the query.
    """
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from domain.marketplace.agent_a2a_service import A2AService
    from core.database import get_database
    db = get_database()
    a2a = A2AService(db)
    user_id = extract_user_id(user)

    if body.agent_user_id:
        result = await a2a.consult(
            client_agent_id=user_id,
            remote_agent_id=body.agent_user_id,
            query=body.query,
            source=body.source,
        )
    else:
        result = await a2a.consult_best_agent(
            client_agent_id=user_id,
            query=body.query,
            source=body.source,
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Consultation failed")
        )

    return result


@router.get("/agents/tasks")
async def get_agent_tasks(request: Request, limit: int = Query(default=20, ge=1, le=100)):
    """Get recent A2A consultation tasks for the current user"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from domain.marketplace.agent_a2a_service import A2AService
    from core.database import get_database
    db = get_database()
    a2a = A2AService(db)

    return await a2a.get_user_tasks(extract_user_id(user), limit=limit)


# ── Admin ──────────────────────────────────────────────

@router.post("/admin/seed")
async def seed_catalog(request: Request):
    """Seed the skill catalog (idempotent)"""
    from domain.marketplace.catalog import seed_catalog as do_seed
    from core.database import get_database
    db = get_database()
    created = await do_seed(db)
    return {"success": True, "skills_created": created}


@router.get("/admin/stats")
async def get_stats(request: Request):
    """Get global marketplace stats"""
    service = get_service(request)
    return await service.get_marketplace_stats()


# ── Gateway Status ─────────────────────────────────────

@router.get("/gateway/status")
async def gateway_status(request: Request):
    """Get gateway health for the current user"""
    user = await get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = get_service(request)
    installed = await service.get_installed_skills(extract_user_id(user))

    healthy = 0
    degraded = 0
    broken = 0
    total_executions = 0
    total_success = 0

    for item in installed:
        inst = item["installation"]
        status = inst.get("gateway_state", {}).get("circuit_status", "closed")
        if status == "closed":
            healthy += 1
        elif status == "half_open":
            degraded += 1
        else:
            broken += 1

        usage = inst.get("usage", {})
        total_executions += usage.get("total_executions", 0)
        total_success += usage.get("success_count", 0)

    success_rate = (total_success / total_executions * 100) if total_executions > 0 else 100.0

    return {
        "status": "operational" if broken == 0 else ("degraded" if broken < 3 else "unhealthy"),
        "skills_installed": len(installed),
        "healthy": healthy,
        "degraded": degraded,
        "broken": broken,
        "total_executions": total_executions,
        "success_rate": round(success_rate, 1),
    }
