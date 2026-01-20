"""
Bonding Memory Models
Models for bonding-specific memory types
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid


# ============================================================================
# IDENTITY MEMORY - User Preferences & Boundaries
# ============================================================================

class IdentityMemory(BaseModel):
    """
    Stores user preferences, boundaries, and communication style.
    
    This is what the avatar learns about "who the user is" and "how they like things".
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID of the user")
    avatar_id: str = Field(..., description="ID of the avatar")
    
    # What type of preference this is
    preference_type: str = Field(
        ...,
        description="Type: communication_style, boundary, life_context, value, goal, fear, aspiration"
    )
    
    # The actual preference
    label: str = Field(..., description="Short label (e.g., 'prefers morning check-ins')")
    description: str = Field(..., description="Full description of this preference")
    
    # Metadata
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="How sure we are (0-1)")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="How important this is (0-1)")
    source: str = Field(default="inferred", description="How we learned this: stated, inferred, observed")
    
    # Context
    examples: List[str] = Field(default_factory=list, description="Examples that demonstrate this")
    exceptions: List[str] = Field(default_factory=list, description="When this doesn't apply")
    
    # Timestamps
    first_observed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_confirmed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    times_observed: int = Field(default=1, description="How many times we've seen this")
    
    # Lifecycle
    is_active: bool = Field(default=True, description="Still relevant?")
    invalidated_at: Optional[datetime] = Field(default=None, description="When this stopped being true")
    
    class Config:
        use_enum_values = True
    
    def confirm(self):
        """Mark this preference as confirmed again"""
        self.last_confirmed = datetime.now(timezone.utc)
        self.times_observed += 1
        if self.confidence < 0.9:
            self.confidence = min(0.95, self.confidence + 0.1)
    
    def invalidate(self):
        """Mark this preference as no longer valid"""
        self.is_active = False
        self.invalidated_at = datetime.now(timezone.utc)


# ============================================================================
# NARRATIVE MEMORY - Story Arcs & Journey
# ============================================================================

class NarrativeMemory(BaseModel):
    """
    Stores the story of the user-avatar relationship.
    
    This is the "narrative arc" - where we've been, where we're going,
    and what the relationship journey looks like.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID of the user")
    avatar_id: str = Field(..., description="ID of the avatar")
    
    # Arc type
    arc_type: str = Field(
        ...,
        description="Type: growth, exploration, challenge, transformation, achievement, discovery"
    )
    
    # Story elements
    title: str = Field(..., description="Name of this arc (e.g., 'Learning to Code')")
    description: str = Field(..., description="What's happening in this arc")
    current_chapter: str = Field(default="beginning", description="Where we are: beginning, middle, climax, resolution")
    
    # Key moments
    key_moments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Important events in this arc"
    )
    # Each moment: {"timestamp": "...", "description": "...", "significance": 0.8}
    
    # Progression
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None, description="When this arc concluded")
    is_active: bool = Field(default=True, description="Still ongoing?")
    
    # Emotional journey
    emotional_tone: str = Field(default="neutral", description="Overall emotional feel")
    emotional_trajectory: List[str] = Field(
        default_factory=list,
        description="How emotions have evolved (e.g., ['anxious', 'hopeful', 'confident'])"
    )
    
    # Future
    expected_next_steps: List[str] = Field(default_factory=list, description="What might happen next")
    potential_obstacles: List[str] = Field(default_factory=list, description="What could go wrong")
    success_indicators: List[str] = Field(default_factory=list, description="What would success look like")
    
    # Metadata
    significance: float = Field(default=0.5, ge=0.0, le=1.0, description="How important this arc is")
    
    class Config:
        use_enum_values = True
    
    def add_moment(self, description: str, significance: float = 0.5):
        """Add a key moment to this arc"""
        moment = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "description": description,
            "significance": significance
        }
        self.key_moments.append(moment)
    
    def progress_chapter(self, new_chapter: str):
        """Move to the next chapter"""
        self.current_chapter = new_chapter
    
    def complete(self):
        """Mark this arc as complete"""
        self.is_active = False
        self.completed_at = datetime.now(timezone.utc)
        self.current_chapter = "resolution"


# ============================================================================
# BOND MOMENT - Special Closeness Events
# ============================================================================

class BondMoment(BaseModel):
    """
    Records special moments of closeness, vulnerability, or breakthrough.
    
    These are the "highlight reel" of the relationship - the moments that
    strengthen the bond and make the relationship feel meaningful.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID of the user")
    avatar_id: str = Field(..., description="ID of the avatar")
    
    # Moment type
    moment_type: str = Field(
        ...,
        description="Type: vulnerability, breakthrough, delight, achievement, connection, surprise, gratitude"
    )
    
    # What happened
    description: str = Field(..., description="What happened in this moment")
    context: str = Field(default="", description="What led to this moment")
    
    # Impact
    bond_impact: float = Field(default=0.0, description="How much this increased bond strength")
    emotional_intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="How intense (0-1)")
    significance: float = Field(default=0.5, ge=0.0, le=1.0, description="How important (0-1)")
    
    # Details
    user_emotion: Optional[str] = Field(default=None, description="User's emotion during this")
    avatar_response: Optional[str] = Field(default=None, description="How avatar responded")
    user_feedback: Optional[str] = Field(default=None, description="What user said about it")
    
    # Related data
    related_session_id: Optional[str] = Field(default=None, description="Bonding session ID")
    related_message_ids: List[str] = Field(default_factory=list, description="Message IDs involved")
    
    # Timestamp
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Recall
    times_recalled: int = Field(default=0, description="How often avatar references this")
    last_recalled: Optional[datetime] = Field(default=None, description="When last mentioned")
    
    class Config:
        use_enum_values = True
    
    def recall(self):
        """Mark that this moment was recalled/referenced"""
        self.times_recalled += 1
        self.last_recalled = datetime.now(timezone.utc)


# ============================================================================
# REFLECTION LOG - Avatar Learnings
# ============================================================================

class ReflectionLog(BaseModel):
    """
    Records what the avatar has learned about the user over time.
    
    This is the avatar's "journal" - insights, patterns, surprises,
    and understanding that develops through the relationship.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID of the user")
    avatar_id: str = Field(..., description="ID of the avatar")
    
    # Reflection type
    reflection_type: str = Field(
        ...,
        description="Type: insight, pattern, surprise, learning, hypothesis, question"
    )
    
    # The reflection
    title: str = Field(..., description="Short title (e.g., 'User values authenticity')")
    content: str = Field(..., description="The full reflection")
    
    # Evidence
    evidence: List[str] = Field(
        default_factory=list,
        description="What supports this reflection"
    )
    counterevidence: List[str] = Field(
        default_factory=list,
        description="What contradicts this"
    )
    
    # Confidence
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="How sure (0-1)")
    
    # Impact
    usefulness: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="How useful this has been (set after using)"
    )
    
    # Lifecycle
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    times_applied: int = Field(default=0, description="How many times used in decisions")
    
    # Related
    related_identity_memory_ids: List[str] = Field(
        default_factory=list,
        description="Identity memories this relates to"
    )
    related_bond_moment_ids: List[str] = Field(
        default_factory=list,
        description="Bond moments this stems from"
    )
    
    class Config:
        use_enum_values = True
    
    def add_evidence(self, evidence: str):
        """Add supporting evidence"""
        self.evidence.append(evidence)
        if self.confidence < 0.9:
            self.confidence = min(0.95, self.confidence + 0.05)
        self.updated_at = datetime.now(timezone.utc)
    
    def add_counterevidence(self, counterevidence: str):
        """Add contradicting evidence"""
        self.counterevidence.append(counterevidence)
        self.confidence = max(0.1, self.confidence - 0.1)
        self.updated_at = datetime.now(timezone.utc)
    
    def apply(self, usefulness_rating: Optional[float] = None):
        """Record that this reflection was used in a decision"""
        self.times_applied += 1
        if usefulness_rating is not None:
            # Running average of usefulness
            if self.usefulness is None:
                self.usefulness = usefulness_rating
            else:
                self.usefulness = (self.usefulness * (self.times_applied - 1) + usefulness_rating) / self.times_applied
        self.updated_at = datetime.now(timezone.utc)


# ============================================================================
# BONDING SESSION - Session Tracking
# ============================================================================

class BondingSession(BaseModel):
    """
    Records a single bonding interaction session.
    
    Used for tracking patterns, computing metrics, and providing
    context for future bonding conversations.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID of the user")
    avatar_id: str = Field(..., description="ID of the avatar")
    
    # Session details
    trigger: str = Field(..., description="What triggered this: user_initiated, scheduled, return_from_mission")
    detected_intent: Optional[str] = Field(default=None, description="User's intent")
    selected_bonding_mode: Optional[str] = Field(default=None, description="Bonding mode used")
    
    # Content
    user_message: Optional[str] = Field(default=None, description="What user said")
    cards_generated: List[Dict[str, Any]] = Field(default_factory=list, description="Response cards")
    guidance_asked: bool = Field(default=False, description="Did avatar ask for guidance?")
    micro_missions_proposed: int = Field(default=0, description="Number of missions proposed")
    
    # Metrics
    delight_score: float = Field(default=0.5, ge=0.0, le=1.0, description="User delight (0-1)")
    bond_delta: float = Field(default=0.0, description="Change in bond strength")
    trust_delta: float = Field(default=0.0, description="Change in trust")
    alignment_delta: float = Field(default=0.0, description="Change in alignment")
    
    # User feedback
    user_rated: bool = Field(default=False, description="Did user provide rating?")
    user_rating: Optional[float] = Field(default=None, ge=0.0, le=5.0, description="Star rating (0-5)")
    user_found_helpful: Optional[bool] = Field(default=None, description="Thumbs up/down")
    user_feedback_text: Optional[str] = Field(default=None, description="Optional feedback")
    
    # Timestamps
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = Field(default=None, description="When session ended")
    duration_seconds: Optional[float] = Field(default=None, description="Session duration")
    
    # Summary
    summary: Optional[str] = Field(default=None, description="What happened in this session")
    
    class Config:
        use_enum_values = True
    
    def end_session(self, summary: Optional[str] = None):
        """Mark session as complete"""
        self.end_time = datetime.now(timezone.utc)
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        if summary:
            self.summary = summary
