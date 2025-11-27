"""
State Models
Data models for avatar states
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
from pydantic import BaseModel, Field


class MoodState(str, Enum):
    """Avatar mood states"""
    HAPPY = "happy"
    NEUTRAL = "neutral"
    CURIOUS = "curious"
    BORED = "bored"
    EXCITED = "excited"
    CONTEMPLATIVE = "contemplative"
    SOCIAL = "social"
    CREATIVE = "creative"
    RESTLESS = "restless"
    CALM = "calm"


class Goal(BaseModel):
    """Represents an active goal for the avatar"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    priority: float = Field(default=0.5, ge=0.0, le=1.0)  # 0.0 = low, 1.0 = high
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_completion: Optional[datetime] = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0)  # 0.0 = not started, 1.0 = complete
    related_friend_id: Optional[str] = None  # If goal is about a relationship
    goal_type: str = "general"  # e.g., "social", "creative", "exploration", "relationship"


class StateTransition(BaseModel):
    """Represents a state transition event"""
    from_state: str
    to_state: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str  # Why the transition occurred
    triggered_by: str = "system"  # "system", "perception", "action", "time"
    context: Dict[str, Any] = Field(default_factory=dict)


class ActionOutcome(BaseModel):
    """Represents the outcome of an action"""
    action_id: str
    action_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool
    outcome_data: Dict[str, Any] = Field(default_factory=dict)
    state_before: Optional[str] = None
    state_after: Optional[str] = None


class RelationshipSnapshot(BaseModel):
    """Snapshot of relationship state at a point in time"""
    friend_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    strength_score: float = Field(ge=0.0, le=1.0)
    interaction_count: int = 0
    last_interaction_days_ago: Optional[int] = None


# Import uuid for Goal.id
import uuid

