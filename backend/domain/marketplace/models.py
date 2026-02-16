"""
Siddhi Bazaar - Data Models
Pydantic models for skills, installations, reviews, and gateway results.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class SkillType(str, Enum):
    MCP_TOOL = "mcp_tool"
    WORKFLOW_ENGINE = "workflow_engine"
    SKILL_BUNDLE = "skill_bundle"


class SkillTier(str, Enum):
    CORE = "core"
    STANDARD = "standard"
    ADVANCED = "advanced"
    PREMIUM = "premium"


class CircuitStatus(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


SKILL_CATEGORIES = {
    "social_engagement": {
        "name": "Social Engagement",
        "icon": "heart",
        "color": "#ef4444",
        "description": "React to and interact with content"
    },
    "content_creation": {
        "name": "Content Creation",
        "icon": "pen-tool",
        "color": "#8b5cf6",
        "description": "Create and publish original content"
    },
    "social_networking": {
        "name": "Social Networking",
        "icon": "users",
        "color": "#3b82f6",
        "description": "Build and manage relationships"
    },
    "discovery": {
        "name": "Discovery & Exploration",
        "icon": "compass",
        "color": "#10b981",
        "description": "Find people and content"
    },
    "intelligence": {
        "name": "Intelligence & Awareness",
        "icon": "brain",
        "color": "#f59e0b",
        "description": "Contextual awareness and sensing"
    },
    "workflow_engines": {
        "name": "Workflow Engines",
        "icon": "cog",
        "color": "#6366f1",
        "description": "Automated multi-step workflows"
    },
    "analytics": {
        "name": "Analytics & Memory",
        "icon": "bar-chart-3",
        "color": "#06b6d4",
        "description": "Knowledge graph and insights"
    },
    "mission_ops": {
        "name": "Mission Operations",
        "icon": "target",
        "color": "#ec4899",
        "description": "Mission lifecycle management"
    },
    "bundles": {
        "name": "Skill Bundles",
        "icon": "package",
        "color": "#84cc16",
        "description": "Curated skill packs"
    }
}


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_skill_doc(
    slug: str,
    name: str,
    tagline: str,
    description: str,
    skill_type: str,
    category: str,
    tier: str,
    icon: str,
    color: str,
    binding: Dict[str, Any],
    gateway_config: Optional[Dict] = None,
    state_affinity: Optional[Dict] = None,
    tags: Optional[List[str]] = None,
    is_default: bool = False,
    is_featured: bool = False,
    sort_order: int = 100,
) -> Dict[str, Any]:
    """Create a skill document for MongoDB"""
    return {
        "id": new_id(),
        "slug": slug,
        "name": name,
        "tagline": tagline,
        "description": description,
        "type": skill_type,
        "category": category,
        "tags": tags or [],
        "tier": tier,
        "binding": {
            "mcp_tool_name": binding.get("mcp_tool_name"),
            "permission_key": binding.get("permission_key"),
            "engine_name": binding.get("engine_name"),
            "engine_mission_types": binding.get("engine_mission_types", []),
            "bundled_skill_ids": binding.get("bundled_skill_ids", []),
            "workflow_tools_included": binding.get("workflow_tools_included", []),
        },
        "gateway_config": gateway_config or {
            "rate_limit": {"max_per_hour": None, "max_per_day": None, "cooldown_seconds": 0},
            "circuit_breaker": {"failure_threshold": 5, "recovery_seconds": 300},
            "priority": 1,
        },
        "state_affinity": state_affinity or {
            "preferred_states": [],
            "utility_boost": 0.0,
            "min_energy": 0.0,
            "drives_affected": [],
        },
        "icon": icon,
        "color": color,
        "preview_image": None,
        "author": "NeuralLinks",
        "version": "1.0.0",
        "stats": {
            "total_installs": 0,
            "active_users": 0,
            "avg_rating": 0.0,
            "total_ratings": 0,
            "total_executions": 0,
            "success_rate": 0.0,
            "avg_latency_ms": 0.0,
        },
        "is_default": is_default,
        "is_featured": is_featured,
        "sort_order": sort_order,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def make_installation_doc(user_id: str, skill: Dict[str, Any]) -> Dict[str, Any]:
    """Create an installation document"""
    return {
        "id": new_id(),
        "user_id": user_id,
        "skill_id": skill["id"],
        "skill_slug": skill["slug"],
        "skill_type": skill["type"],
        "installed_at": now_iso(),
        "enabled": True,
        "gateway_state": {
            "circuit_status": CircuitStatus.CLOSED.value,
            "consecutive_failures": 0,
            "last_failure_at": None,
            "last_success_at": None,
        },
        "usage": {
            "total_executions": 0,
            "success_count": 0,
            "failure_count": 0,
            "last_used_at": None,
            "avg_latency_ms": 0.0,
            "executions_today": 0,
            "executions_today_date": None,
        },
        "config": {},
        "user_rating": None,
        "updated_at": now_iso(),
    }


def make_review_doc(skill_id: str, user_id: str, avatar_name: str, rating: int, review_text: str) -> Dict[str, Any]:
    """Create a review document"""
    return {
        "id": new_id(),
        "skill_id": skill_id,
        "user_id": user_id,
        "avatar_name": avatar_name,
        "rating": max(1, min(5, rating)),
        "review_text": review_text,
        "created_at": now_iso(),
    }


@dataclass
class GatewayResult:
    """Standardized result from every gateway execution"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    skill_slug: str = ""
    source: str = "agent"
    avatar_id: str = ""
    was_permitted: bool = True
    denial_reason: Optional[str] = None
    latency_ms: float = 0.0
    tool_health: str = "healthy"
    consecutive_failures: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "skill_slug": self.skill_slug,
            "source": self.source,
            "avatar_id": self.avatar_id,
            "was_permitted": self.was_permitted,
            "denial_reason": self.denial_reason,
            "latency_ms": self.latency_ms,
            "tool_health": self.tool_health,
            "consecutive_failures": self.consecutive_failures,
        }
