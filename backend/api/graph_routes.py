"""
Graph Routes
"""

from fastapi import APIRouter, Request, HTTPException, Query
from typing import Dict, Any
from core.auth import require_auth
from core.database import get_database
from api.models import GraphNode
from services.graph_service import GraphService
import logging

db = get_database()
router = APIRouter(prefix="/api/graph", tags=["graph"])
logger = logging.getLogger(__name__)


def get_graph_service() -> GraphService:
    """Get graph service instance"""
    from app.globals import graph_service
    return graph_service


@router.get("/visualization")
async def get_graph_visualization(request: Request):
    """Get graph visualization data for current user"""
    user = await require_auth(request)
    graph_service = get_graph_service()
    return await graph_service.get_visualization_data(user.id)


@router.post("/build-from-profile")
async def build_graph_from_profile(request: Request):
    """Build knowledge graph from user profile"""
    user = await require_auth(request)
    user_doc = await db.users.find_one({"id": user.id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    graph_service = get_graph_service()
    result = await graph_service.build_graph_from_profile(user_doc)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Graph build failed"))
    return {"message": "Graph built from profile"}


@router.post("/enrich-from-post")
async def enrich_graph_from_post(post_data: Dict[str, str], request: Request):
    """Enrich knowledge graph from post content"""
    user = await require_auth(request)
    post_text = post_data.get('text', '')
    if not post_text:
        raise HTTPException(status_code=400, detail="Post text is required")
    
    graph_service = get_graph_service()
    result = await graph_service.enrich_graph_from_post(post_text, user.id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Graph enrichment failed"))
    return {"message": "Graph enriched from post"}


@router.get("/compatibility/{other_user_id}")
async def get_compatibility(other_user_id: str, request: Request):
    """Get compatibility score with another user"""
    user = await require_auth(request)
    graph_service = get_graph_service()
    return await graph_service.calculate_compatibility(user.id, other_user_id)


@router.get("/my-graph")
async def get_my_graph(request: Request):
    """Get user's knowledge graph"""
    user = await require_auth(request)
    
    nodes = await db.graph_nodes.find({"user_id": user.id}, {"_id": 0}).to_list(1000)
    edges = await db.graph_edges.find(
        {"$or": [
            {"from_node_id": {"$in": [n['id'] for n in nodes]}},
            {"to_node_id": {"$in": [n['id'] for n in nodes]}}
        ]},
        {"_id": 0}
    ).to_list(1000)
    
    return {"nodes": nodes, "edges": edges}


@router.post("/add-node")
async def add_graph_node(node_data: Dict[str, Any], request: Request):
    """Add a node to user's knowledge graph"""
    user = await require_auth(request)
    
    node = GraphNode(
        user_id=user.id,
        node_type=node_data['node_type'],
        label=node_data['label'],
        properties=node_data.get('properties', {})
    )
    
    node_dict = node.model_dump()
    node_dict['created_at'] = node_dict['created_at'].isoformat()
    node_dict['updated_at'] = node_dict['updated_at'].isoformat()
    await db.graph_nodes.insert_one(node_dict)
    
    return node


@router.post("/enrich-from-interaction")
async def enrich_graph_from_interaction(request: Request, data: Dict[str, Any]):
    """Enrich graph from user interaction"""
    user = await require_auth(request)
    
    target_user_id = data.get("target_user_id")
    interaction_type = data.get("interaction_type", "view")  # view, like, match, message
    
    if not target_user_id:
        raise HTTPException(status_code=400, detail="Target user ID required")
    
    graph_builder = get_graph_builder()
    _ = await graph_builder.enrich_graph_from_interaction(
        user.id, target_user_id, interaction_type
    )
    
    return {"message": "Graph enriched from interaction"}


@router.get("/context")
async def get_graph_context(request: Request):
    """Get user's graph context"""
    user = await require_auth(request)
    
    from app.globals import graph_rag
    context = await graph_rag.get_user_context(user.id)
    
    return context


@router.get("/similar-users")
async def find_similar_users(request: Request, limit: int = Query(10, ge=1, le=50)):
    """Find users with similar graphs"""
    user = await require_auth(request)
    
    from app.globals import graph_rag
    similar = await graph_rag.find_similar_users(user.id, limit)
    
    return {"similar_users": similar}


def get_graph_builder():
    """Get GraphBuilder instance"""
    from app.globals import graph_builder
    return graph_builder

