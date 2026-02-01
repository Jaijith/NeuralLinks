"""
Bonding State Models
Models for tracking user-avatar bonding state and relationship health
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, field_validator
import uuid

from .enums import UserMood, UserEmotion


class UnresolvedThread(BaseModel):
    """An unresolved conversation thread or pending decision"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = Field(..., description="What this thread is about")
    context: str = Field(..., description="Context and details")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="How important (0-1)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_mentioned: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    needs_user_input: bool = Field(default=False, description="Waiting for user decision")
    suggested_actions: List[str] = Field(default_factory=list, description="Potential next steps")


class RelationshipArc(BaseModel):
    """The overarching narrative of the user-avatar relationship"""
    arc_type: str = Field(..., description="Type of arc: growth, exploration, challenge, etc.")
    description: str = Field(..., description="What's happening in this arc")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    key_moments: List[str] = Field(default_factory=list, description="Important events in this arc")
    current_chapter: str = Field(default="beginning", description="Where we are in the arc")
    expected_next_steps: List[str] = Field(default_factory=list, description="What might happen next")
    emotional_tone: str = Field(default="neutral", description="Overall emotional feel")


class BondingMetrics(BaseModel):
    """Quantitative metrics for bond health"""
    bond_strength: float = Field(default=0.5, description="Overall closeness (0-1)")
    trust: float = Field(default=0.5, description="User trust in avatar (0-1)")
    alignment_confidence: float = Field(default=0.5, description="How well avatar understands user (0-1)")
    engagement_rate: float = Field(default=0.5, description="How often user engages (0-1)")
    satisfaction_score: float = Field(default=0.5, description="User satisfaction (0-1)")
    
    # Deltas (change since last session)
    bond_delta: float = Field(default=0.0, description="Change in bond strength")
    trust_delta: float = Field(default=0.0, description="Change in trust")
    alignment_delta: float = Field(default=0.0, description="Change in alignment")
    
    @field_validator('bond_strength', 'trust', 'alignment_confidence', 'engagement_rate', 'satisfaction_score', mode='before')
    @classmethod
    def clamp_to_valid_range(cls, v):
        """Clamp values to 0.0-1.0 range to handle floating point precision"""
        if v is None:
            return 0.5
        return max(0.0, min(1.0, float(v)))


class BondingState(BaseModel):
    """
    Complete bonding state for a user-avatar relationship.
    
    This tracks:
    - Relationship health metrics (bond, trust, alignment)
    - User's estimated mood and emotion
    - Unresolved conversation threads
    - Relationship narrative arc
    - Session history and patterns
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID of the user")
    avatar_id: str = Field(..., description="ID of the avatar")
    
    # === METRICS ===
    metrics: BondingMetrics = Field(default_factory=BondingMetrics)
    
    # === USER STATE ESTIMATION ===
    user_mood_estimate: UserMood = Field(default=UserMood.NEUTRAL, description="Best guess at user's mood")
    mood_confidence: float = Field(default=0.3, ge=0.0, le=1.0, description="Confidence in mood estimate")
    last_user_emotion: Optional[UserEmotion] = Field(default=None, description="Most recent detected emotion")
    emotion_confidence: float = Field(default=0.3, ge=0.0, le=1.0, description="Confidence in emotion detection")
    
    # === CONVERSATION STATE ===
    unresolved_threads: List[UnresolvedThread] = Field(default_factory=list, description="Pending topics/decisions")
    relationship_arc: Optional[RelationshipArc] = Field(default=None, description="Current relationship journey")
    
    # === ENGAGEMENT PATTERNS ===
    return_pressure: float = Field(default=0.0, ge=0.0, le=1.0, description="How much user wants space (0=welcome, 1=give space)")
    last_bonding_session: Optional[datetime] = Field(default=None, description="Last bonding interaction")
    total_sessions: int = Field(default=0, description="Total bonding sessions")
    average_session_duration: Optional[timedelta] = Field(default=None, description="Average time per session")
    
    # === DELIGHT TRACKING ===
    delight_history: List[float] = Field(default_factory=list, description="Recent delight scores (0-1)")
    last_delight_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Most recent delight score")
    delight_trend: str = Field(default="stable", description="rising, falling, or stable")
    
    # === TIMESTAMPS ===
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        use_enum_values = True
    
    def update_metrics(
        self,
        bond_delta: float = 0.0,
        trust_delta: float = 0.0,
        alignment_delta: float = 0.0
    ):
        """Update bonding metrics with deltas"""
        self.metrics.bond_strength = max(0.0, min(1.0, self.metrics.bond_strength + bond_delta))
        self.metrics.trust = max(0.0, min(1.0, self.metrics.trust + trust_delta))
        self.metrics.alignment_confidence = max(0.0, min(1.0, self.metrics.alignment_confidence + alignment_delta))
        
        self.metrics.bond_delta = bond_delta
        self.metrics.trust_delta = trust_delta
        self.metrics.alignment_delta = alignment_delta
        
        self.updated_at = datetime.now(timezone.utc)
    
    def add_unresolved_thread(self, topic: str, context: str, importance: float = 0.5):
        """Add a new unresolved conversation thread"""
        thread = UnresolvedThread(
            topic=topic,
            context=context,
            importance=importance
        )
        self.unresolved_threads.append(thread)
        self.updated_at = datetime.now(timezone.utc)
    
    def resolve_thread(self, thread_id: str):
        """Mark a thread as resolved and remove it"""
        self.unresolved_threads = [
            thread for thread in self.unresolved_threads
            if thread.id != thread_id
        ]
        self.updated_at = datetime.now(timezone.utc)
    
    def update_delight(self, score: float):
        """Add a new delight score and update trend"""
        self.delight_history.append(score)
        # Keep only last 10 scores
        if len(self.delight_history) > 10:
            self.delight_history = self.delight_history[-10:]
        
        self.last_delight_score = score
        
        # Calculate trend
        if len(self.delight_history) >= 3:
            recent_avg = sum(self.delight_history[-3:]) / 3
            older_avg = sum(self.delight_history[-6:-3]) / 3 if len(self.delight_history) >= 6 else recent_avg
            
            if recent_avg > older_avg + 0.1:
                self.delight_trend = "rising"
            elif recent_avg < older_avg - 0.1:
                self.delight_trend = "falling"
            else:
                self.delight_trend = "stable"
        
        self.updated_at = datetime.now(timezone.utc)
    
    def compute_return_pressure(self) -> float:
        """
        Calculate how much the user might want space.
        
        Higher return pressure (closer to 1.0) means:
        - Give the user more space
        - Be less proactive
        - Wait for them to initiate
        
        Lower return pressure (closer to 0.0) means:
        - User welcomes engagement
        - Safe to be proactive
        - Can suggest things
        """
        pressure = 0.0
        
        # If sessions are too frequent (< 1 day apart), increase pressure
        if self.last_bonding_session:
            time_since_last = datetime.now(timezone.utc) - self.last_bonding_session
            if time_since_last < timedelta(hours=12):
                pressure += 0.3
            elif time_since_last < timedelta(days=1):
                pressure += 0.1
        
        # If delight is falling, increase pressure
        if self.delight_trend == "falling":
            pressure += 0.2
        
        # If engagement rate is low, increase pressure
        if self.metrics.engagement_rate < 0.3:
            pressure += 0.2
        
        # If user seems stressed/overwhelmed, increase pressure
        if self.user_mood_estimate in [UserMood.STRESSED, UserMood.FRUSTRATED]:
            pressure += 0.2
        
        # Cap at 1.0
        self.return_pressure = min(1.0, pressure)
        return self.return_pressure
    
    def should_engage(self) -> bool:
        """
        Determine if it's appropriate to initiate bonding engagement.
        
        Returns:
            True if engagement is welcome, False if user needs space
        """
        self.compute_return_pressure()
        
        # If return pressure is high, don't initiate
        if self.return_pressure > 0.7:
            return False
        
        # If bond is very weak, be cautious
        if self.metrics.bond_strength < 0.3:
            return False
        
        # If delight is falling, wait for user to initiate
        if self.delight_trend == "falling":
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = self.dict()
        
        # Convert datetime fields to ISO strings
        if isinstance(data.get("created_at"), datetime):
            data["created_at"] = data["created_at"].isoformat()
        if isinstance(data.get("updated_at"), datetime):
            data["updated_at"] = data["updated_at"].isoformat()
        if isinstance(data.get("last_bonding_session"), datetime):
            data["last_bonding_session"] = data["last_bonding_session"].isoformat()
        
        # Convert timedelta to seconds
        if data.get("average_session_duration"):
            data["average_session_duration"] = data["average_session_duration"].total_seconds()
        
        # Convert unresolved threads
        for thread in data.get("unresolved_threads", []):
            if isinstance(thread.get("created_at"), datetime):
                thread["created_at"] = thread["created_at"].isoformat()
            if isinstance(thread.get("last_mentioned"), datetime):
                thread["last_mentioned"] = thread["last_mentioned"].isoformat()
        
        # Convert relationship arc
        if data.get("relationship_arc"):
            arc = data["relationship_arc"]
            if isinstance(arc.get("started_at"), datetime):
                arc["started_at"] = arc["started_at"].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BondingState":
        """Create from dictionary (MongoDB document)"""
        # This is a simplified version - in production, you'd handle datetime parsing
        return cls(**data)
