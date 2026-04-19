"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Profile fields
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    
    # Avatar profile fields (parallel to real profile)
    avatar_name: Optional[str] = None
    avatar_picture: Optional[str] = None
    avatar_bio: Optional[str] = None
    avatar_job_title: Optional[str] = None
    avatar_location: Optional[str] = None
    avatar_interests: List[str] = Field(default_factory=list)
    
    # Profile completion status
    profile_completed: bool = False
    onboarding_stage: str = "start"  # start, basic_info, personality, interests, complete


class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphNode(BaseModel):
    """Represents a node in the knowledge graph (LTM)."""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    node_type: str  # interest, trait, value, experience, preference, connection, fact, demographic
    label: str
    display_label: Optional[str] = None
    strength: Optional[float] = None
    mention_count: Optional[int] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Bayesian Belief Parameters
    belief_alpha: float = 1.0
    belief_beta: float = 1.0
    belief_strength: Optional[float] = None
    belief_variance: Optional[float] = None
    belief_confidence: Optional[float] = None

    # Evidence Tracking (permanent, never deleted)
    evidence_count: Optional[int] = None
    evidence_log: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_sources: List[str] = Field(default_factory=list)
    first_evidence_at: Optional[datetime] = None
    last_evidence_at: Optional[datetime] = None

    # Frequency Metrics
    mention_frequency: Optional[float] = None
    evidence_span_days: Optional[int] = None
    evidence_pattern: Optional[str] = None
    narrative_descriptor: Optional[str] = None

    # Temporal Salience
    salience: Optional[float] = None
    salience_stability: Optional[float] = None
    salience_last_computed: Optional[datetime] = None

    # Status
    status: Optional[str] = None  # "pending" | "active" | "fading"


class GraphEdge(BaseModel):
    """Represents a relationship between nodes (LTM)."""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_node_id: str
    to_node_id: str
    relationship_type: str
    weight: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Bayesian Edge Parameters
    belief_alpha: Optional[float] = None
    belief_beta: Optional[float] = None
    edge_strength: Optional[float] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    last_evidence_at: Optional[datetime] = None
    evidence_count: Optional[int] = None
    user_id: Optional[str] = None


class AIAgent(BaseModel):
    """Represents a user's AI agent"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    personality_summary: str = ""
    conversation_style: str = "friendly"
    knowledge_graph_version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentConversation(BaseModel):
    """Conversation between two AI agents"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent1_user_id: str
    agent2_user_id: str
    messages: List[Dict[str, str]] = Field(default_factory=list)
    compatibility_score: Optional[float] = None
    conversation_summary: str = ""
    status: str = "active"  # active, completed, archived
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Match(BaseModel):
    """Represents a match between two users"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    matched_user_id: str
    compatibility_score: float
    shared_interests: List[str] = Field(default_factory=list)
    personality_compatibility: float = 0.0
    conversation_quality: float = 0.0
    agent_conversation_id: str
    status: str = "pending"  # pending, accepted, rejected
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HumanConversation(BaseModel):
    """Real conversation between matched users"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserIntegration(BaseModel):
    """User's connected platform integration"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    platform_name: str
    platform_type: str  # social_media, ecommerce, email, messaging, dating
    connected: bool = True
    connected_at: str
    last_sync: str
    data_collected: int = 0


class Friendship(BaseModel):
    """Friendship/connection between users"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    friend_id: str
    status: str  # pending, accepted, blocked
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = None


class SignupRequest(BaseModel):
    """User signup request pending approval"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None  # Admin user ID who reviewed
    notes: Optional[str] = None

