"""
Graph CRUD API Routes
Endpoints for managing interests, connections, traits, and visualization
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import logging

from core.database import get_database
from core.auth import require_auth, get_current_user
from app.globals import get_graph_service
from domain.memory.bayesian import add_bayesian_defaults

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/graph", tags=["graph"])


# =============================================================================
# MODELS
# =============================================================================

class InterestCreate(BaseModel):
    label: str = Field(..., description="Interest name")
    strength: float = Field(default=0.7, ge=0, le=1)


class InterestUpdate(BaseModel):
    label: Optional[str] = None
    strength: Optional[float] = Field(default=None, ge=0, le=1)


class ConnectionCreate(BaseModel):
    name: str = Field(..., description="Person's name")
    relationship: str = Field(..., description="Relationship type (daughter, friend, etc.)")
    details: Optional[str] = None


class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    relationship: Optional[str] = None
    details: Optional[str] = None


class TraitCreate(BaseModel):
    label: str = Field(..., description="Trait name")
    strength: float = Field(default=0.7, ge=0, le=1)


class TraitUpdate(BaseModel):
    label: Optional[str] = None
    strength: Optional[float] = Field(default=None, ge=0, le=1)


# =============================================================================
# VISUALIZATION
# =============================================================================

@router.get("/visualization")
async def get_graph_visualization(request: Request):
    """Get graph visualization data for the avatar settings page"""
    try:
        user = await require_auth(request)
        graph_service = get_graph_service()
        
        visualization_data = await graph_service.get_visualization_data(user.id)
        return visualization_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting graph visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# INTERESTS CRUD
# =============================================================================

@router.get("/interests")
async def get_interests(request: Request):
    """Get all interests for the current user"""
    try:
        user = await require_auth(request)
        db = get_database()
        
        interests = await db.graph_nodes.find({
            "user_id": user.id,
            "node_type": "interest"
        }).sort("strength", -1).to_list(100)
        
        return {
            "success": True,
            "interests": [
                {
                    "id": str(i.get("id") or i.get("_id")),
                    "label": i.get("display_label") or i.get("label", "").title(),
                    "strength": i.get("strength", 0.5),
                    "source": i.get("properties", {}).get("source", "unknown"),
                    "mention_count": i.get("mention_count", 0)
                }
                for i in interests
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting interests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interests")
async def create_interest(req: InterestCreate, request: Request):
    """Create a new interest"""
    try:
        user = await require_auth(request)
        db = get_database()
        now = datetime.now(timezone.utc)
        
        # Check if already exists
        existing = await db.graph_nodes.find_one({
            "user_id": user.id,
            "node_type": "interest",
            "label": req.label.lower()
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Interest already exists")
        
        node_id = f"interest_{user.id}_{req.label.lower().replace(' ', '_')}"
        
        node = {
            "id": node_id,
            "user_id": user.id,
            "node_type": "interest",
            "label": req.label.lower(),
            "display_label": req.label.title(),
            "strength": req.strength,
            "properties": {"source": "explicit", "service": "manual"},
            "mention_count": 1,
            "created_at": now,
            "updated_at": now,
        }
        add_bayesian_defaults(node, prior="verified", source="manual")
        await db.graph_nodes.insert_one(node)
        
        return {"success": True, "id": node_id, "message": "Interest created"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating interest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/interests/{interest_id:path}")
async def update_interest(interest_id: str, req: InterestUpdate, request: Request):
    """Update an existing interest"""
    try:
        from urllib.parse import unquote
        user = await require_auth(request)
        db = get_database()
        
        # URL decode the interest_id
        decoded_id = unquote(interest_id)
        
        # Try to extract label from interest_id format
        label_to_match = None
        if decoded_id.startswith("interest_"):
            parts = decoded_id.split("_", 2)
            if len(parts) >= 3:
                label_to_match = parts[2].replace("_", " ")
        
        update_fields = {"updated_at": datetime.now(timezone.utc)}
        if req.label:
            update_fields["label"] = req.label.lower()
            update_fields["display_label"] = req.label.title()
        if req.strength is not None:
            update_fields["strength"] = req.strength
        
        result = await db.graph_nodes.update_one(
            {
                "user_id": user.id,
                "node_type": "interest",
                "$or": [
                    {"id": decoded_id},
                    {"_id": decoded_id},
                    {"label": decoded_id.lower()},
                    {"display_label": {"$regex": f"^{decoded_id}$", "$options": "i"}},
                    *([{"label": {"$regex": f"^{label_to_match}$", "$options": "i"}}] if label_to_match else [])
                ]
            },
            {"$set": update_fields}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Interest not found")
        
        return {"success": True, "message": "Interest updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating interest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/interests/{interest_id:path}")
async def delete_interest(interest_id: str, request: Request):
    """Delete an interest"""
    try:
        from urllib.parse import unquote
        user = await require_auth(request)
        db = get_database()
        
        # URL decode the interest_id
        decoded_id = unquote(interest_id)
        
        # Try to extract label from interest_id format: interest_{user_id}_{label}
        label_to_match = None
        if decoded_id.startswith("interest_"):
            parts = decoded_id.split("_", 2)
            if len(parts) >= 3:
                label_to_match = parts[2].replace("_", " ")
        
        # Try multiple matching strategies
        result = await db.graph_nodes.delete_one({
            "user_id": user.id,
            "node_type": "interest",
            "$or": [
                {"id": decoded_id},
                {"_id": decoded_id},
                {"label": decoded_id.lower()},
                {"display_label": {"$regex": f"^{decoded_id}$", "$options": "i"}},
                *([{"label": {"$regex": f"^{label_to_match}$", "$options": "i"}}] if label_to_match else [])
            ]
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Interest not found")
        
        return {"success": True, "message": "Interest deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting interest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CONNECTIONS CRUD
# =============================================================================

@router.get("/connections")
async def get_connections(request: Request):
    """Get all connections for the current user"""
    try:
        user = await require_auth(request)
        db = get_database()
        
        # Get from users.connections
        user_doc = await db.users.find_one({"id": user.id}, {"connections": 1})
        user_connections = user_doc.get("connections", []) if user_doc else []
        
        # Get from graph_nodes
        conn_nodes = await db.graph_nodes.find({
            "user_id": user.id,
            "node_type": "connection"
        }).to_list(100)
        
        # Merge and dedupe
        connections = []
        seen_names = set()
        
        for conn in user_connections:
            name = conn.get("name", "").strip()
            if name and name.lower() not in seen_names:
                seen_names.add(name.lower())
                connections.append({
                    "id": f"conn_{user.id}_{name.lower().replace(' ', '_')}",
                    "name": name,
                    "relationship": conn.get("relationship", "friend"),
                    "source": conn.get("source", "conversation"),
                    "details": conn.get("details", ""),
                    "mentioned_count": conn.get("mentioned_count", 1)
                })
        
        for node in conn_nodes:
            name = node.get("display_label") or node.get("label", "").title()
            if name and name.lower() not in seen_names:
                seen_names.add(name.lower())
                props = node.get("properties", {})
                connections.append({
                    "id": str(node.get("id") or node.get("_id")),
                    "name": name,
                    "relationship": props.get("relationship", "friend"),
                    "source": props.get("source", "implicit"),
                    "details": props.get("details", ""),
                    "mentioned_count": node.get("mention_count", 1)
                })
        
        return {"success": True, "connections": connections}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting connections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connections")
async def create_connection(req: ConnectionCreate, request: Request):
    """Create a new connection"""
    try:
        user = await require_auth(request)
        db = get_database()
        now = datetime.now(timezone.utc)
        
        # Add to users.connections
        await db.users.update_one(
            {"id": user.id},
            {
                "$push": {
                    "connections": {
                        "name": req.name.strip(),
                        "relationship": req.relationship,
                        "details": req.details or "",
                        "source": "explicit",
                        "mentioned_count": 1,
                        "last_mentioned": now.isoformat()
                    }
                }
            },
            upsert=True
        )
        
        node_id = f"connection_{user.id}_{req.name.lower().replace(' ', '_')}"
        bayesian_insert = {
            "belief_alpha": 3.0,
            "belief_beta": 1.0,
            "belief_strength": 0.75,
            "belief_variance": 0.0375,
            "belief_confidence": 0.85,
            "salience": 0.8,
            "salience_stability": 60.0,
            "salience_last_computed": now,
            "status": "active",
            "evidence_count": 1,
            "evidence_log": [{
                "at": now.isoformat() if isinstance(now, datetime) else now,
                "source": "manual", "weight": 0.8,
                "subtype": "connection_definitive", "session_id": "",
            }],
            "evidence_sources": ["manual"],
            "first_evidence_at": now,
            "evidence_pattern": "single_mention",
            "narrative_descriptor": "",
            "mention_frequency": 0.0,
            "evidence_span_days": 0,
        }
        await db.graph_nodes.update_one(
            {"user_id": user.id, "node_type": "connection", "label": req.name.lower()},
            {
                "$set": {
                    "id": node_id,
                    "user_id": user.id,
                    "node_type": "connection",
                    "label": req.name.lower(),
                    "display_label": req.name.strip(),
                    "properties": {
                        "source": "explicit",
                        "relationship": req.relationship,
                        "details": req.details or ""
                    },
                    "strength": 0.8,
                    "updated_at": now,
                    "last_evidence_at": now,
                },
                "$setOnInsert": {
                    "created_at": now, "mention_count": 1,
                    **bayesian_insert,
                }
            },
            upsert=True
        )
        
        return {"success": True, "id": node_id, "message": "Connection created"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/connections/{connection_id}")
async def update_connection(connection_id: str, req: ConnectionUpdate, request: Request):
    """Update an existing connection"""
    try:
        user = await require_auth(request)
        db = get_database()
        now = datetime.now(timezone.utc)
        
        # Try to extract name from connection_id
        # Format: conn_{user_id}_{name} or connection_{user_id}_{name}
        parts = connection_id.split("_")
        if len(parts) >= 3:
            old_name = "_".join(parts[2:]).replace("_", " ")
        else:
            old_name = connection_id
        
        # Update in users.connections
        update_user_fields = {}
        if req.name:
            update_user_fields["connections.$.name"] = req.name.strip()
        if req.relationship:
            update_user_fields["connections.$.relationship"] = req.relationship
        if req.details is not None:
            update_user_fields["connections.$.details"] = req.details
        update_user_fields["connections.$.last_mentioned"] = now.isoformat()
        
        await db.users.update_one(
            {"id": user.id, "connections.name": {"$regex": f"^{old_name}$", "$options": "i"}},
            {"$set": update_user_fields}
        )
        
        # Update in graph_nodes
        update_node_fields = {"updated_at": now}
        if req.name:
            update_node_fields["label"] = req.name.lower()
            update_node_fields["display_label"] = req.name.strip()
        if req.relationship:
            update_node_fields["properties.relationship"] = req.relationship
        if req.details is not None:
            update_node_fields["properties.details"] = req.details
        
        await db.graph_nodes.update_one(
            {
                "user_id": user.id,
                "node_type": "connection",
                "$or": [
                    {"id": connection_id},
                    {"label": {"$regex": f"^{old_name}$", "$options": "i"}}
                ]
            },
            {"$set": update_node_fields}
        )
        
        return {"success": True, "message": "Connection updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str, request: Request):
    """Delete a connection"""
    try:
        user = await require_auth(request)
        db = get_database()
        
        # Extract name from connection_id
        parts = connection_id.split("_")
        if len(parts) >= 3:
            name = "_".join(parts[2:]).replace("_", " ")
        else:
            name = connection_id
        
        # Delete from users.connections
        await db.users.update_one(
            {"id": user.id},
            {"$pull": {"connections": {"name": {"$regex": f"^{name}$", "$options": "i"}}}}
        )
        
        # Delete from graph_nodes
        await db.graph_nodes.delete_one({
            "user_id": user.id,
            "node_type": "connection",
            "$or": [
                {"id": connection_id},
                {"label": {"$regex": f"^{name}$", "$options": "i"}}
            ]
        })
        
        return {"success": True, "message": "Connection deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TRAITS CRUD
# =============================================================================

@router.get("/traits")
async def get_traits(request: Request):
    """Get all traits for the current user"""
    try:
        user = await require_auth(request)
        db = get_database()
        
        traits = await db.graph_nodes.find({
            "user_id": user.id,
            "node_type": "trait"
        }).sort("strength", -1).to_list(100)
        
        return {
            "success": True,
            "traits": [
                {
                    "id": str(t.get("id") or t.get("_id")),
                    "label": t.get("display_label") or t.get("label", "").title(),
                    "strength": t.get("strength", 0.5),
                    "source": t.get("properties", {}).get("source", "unknown")
                }
                for t in traits
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting traits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/traits")
async def create_trait(req: TraitCreate, request: Request):
    """Create a new trait"""
    try:
        user = await require_auth(request)
        db = get_database()
        now = datetime.now(timezone.utc)
        
        existing = await db.graph_nodes.find_one({
            "user_id": user.id,
            "node_type": "trait",
            "label": req.label.lower()
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Trait already exists")
        
        node_id = f"trait_{user.id}_{req.label.lower().replace(' ', '_')}"
        
        node = {
            "id": node_id,
            "user_id": user.id,
            "node_type": "trait",
            "label": req.label.lower(),
            "display_label": req.label.title(),
            "strength": req.strength,
            "properties": {"source": "explicit", "service": "manual"},
            "created_at": now,
            "updated_at": now,
        }
        add_bayesian_defaults(node, prior="verified", source="manual")
        await db.graph_nodes.insert_one(node)
        
        return {"success": True, "id": node_id, "message": "Trait created"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating trait: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/traits/{trait_id:path}")
async def update_trait(trait_id: str, req: TraitUpdate, request: Request):
    """Update an existing trait"""
    try:
        from urllib.parse import unquote
        user = await require_auth(request)
        db = get_database()
        
        decoded_id = unquote(trait_id)
        
        # Try to extract label from trait_id format
        label_to_match = None
        if decoded_id.startswith("trait_"):
            parts = decoded_id.split("_", 2)
            if len(parts) >= 3:
                label_to_match = parts[2].replace("_", " ")
        
        update_fields = {"updated_at": datetime.now(timezone.utc)}
        if req.label:
            update_fields["label"] = req.label.lower()
            update_fields["display_label"] = req.label.title()
        if req.strength is not None:
            update_fields["strength"] = req.strength
        
        result = await db.graph_nodes.update_one(
            {
                "user_id": user.id,
                "node_type": "trait",
                "$or": [
                    {"id": decoded_id},
                    {"_id": decoded_id},
                    {"label": decoded_id.lower()},
                    {"display_label": {"$regex": f"^{decoded_id}$", "$options": "i"}},
                    *([{"label": {"$regex": f"^{label_to_match}$", "$options": "i"}}] if label_to_match else [])
                ]
            },
            {"$set": update_fields}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Trait not found")
        
        return {"success": True, "message": "Trait updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating trait: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/traits/{trait_id:path}")
async def delete_trait(trait_id: str, request: Request):
    """Delete a trait"""
    try:
        from urllib.parse import unquote
        user = await require_auth(request)
        db = get_database()
        
        decoded_id = unquote(trait_id)
        
        # Try to extract label from trait_id format
        label_to_match = None
        if decoded_id.startswith("trait_"):
            parts = decoded_id.split("_", 2)
            if len(parts) >= 3:
                label_to_match = parts[2].replace("_", " ")
        
        result = await db.graph_nodes.delete_one({
            "user_id": user.id,
            "node_type": "trait",
            "$or": [
                {"id": decoded_id},
                {"_id": decoded_id},
                {"label": decoded_id.lower()},
                {"display_label": {"$regex": f"^{decoded_id}$", "$options": "i"}},
                *([{"label": {"$regex": f"^{label_to_match}$", "$options": "i"}}] if label_to_match else [])
            ]
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Trait not found")
        
        return {"success": True, "message": "Trait deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting trait: {e}")
        raise HTTPException(status_code=500, detail=str(e))
