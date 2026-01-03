"""
Lead Model
Represents a discovered match/lead from a mission
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from .enums import LeadStatus, LeadPriority


class LeadScoreBreakdown(BaseModel):
    """Detailed breakdown of the compatibility score"""
    interest_overlap: float = Field(default=0.0, ge=0, le=1)
    trait_compatibility: float = Field(default=0.0, ge=0, le=1)
    activity_alignment: float = Field(default=0.0, ge=0, le=1)
    mutual_connections: float = Field(default=0.0, ge=0, le=1)
    engagement_quality: float = Field(default=0.0, ge=0, le=1)


class ConversationSummary(BaseModel):
    """Summary of conversation with this lead"""
    conversation_id: Optional[str] = None
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    sentiment: str = "neutral"  # positive, neutral, negative
    engagement_signals: List[str] = Field(default_factory=list)
    summary: str = ""
    key_topics: List[str] = Field(default_factory=list)


class MatchDetails(BaseModel):
    """Details about why this is a match"""
    shared_interests: List[str] = Field(default_factory=list)
    shared_traits: List[str] = Field(default_factory=list)
    unique_interests: List[str] = Field(default_factory=list)  # Interesting things they have that user doesn't
    connection_points: List[str] = Field(default_factory=list)  # Suggested talking points
    compatibility_reasons: List[str] = Field(default_factory=list)


class Lead(BaseModel):
    """
    A lead represents a discovered match from a mission.
    
    Contains all information about the matched user, compatibility score,
    conversation history summary, and follow-up status.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str = Field(..., description="ID of the mission that generated this lead")
    user_id: str = Field(..., description="ID of the user who owns this lead")
    
    # Target information
    target_user_id: str = Field(..., description="ID of the matched user")
    target_avatar_name: str = Field(..., description="Avatar name of the matched user")
    target_real_name: Optional[str] = None
    target_picture: Optional[str] = None
    target_archetype: Optional[str] = None
    
    # Scoring
    score: int = Field(..., ge=0, le=100, description="Compatibility score 0-100")
    score_breakdown: LeadScoreBreakdown = Field(default_factory=LeadScoreBreakdown)
    confidence: float = Field(default=0.5, ge=0, le=1, description="Confidence in the score")
    
    # Match details
    match_details: MatchDetails = Field(default_factory=MatchDetails)
    
    # Conversation
    conversation: ConversationSummary = Field(default_factory=ConversationSummary)
    
    # Status
    status: LeadStatus = Field(default=LeadStatus.NEW)
    priority: LeadPriority = Field(default=LeadPriority.MEDIUM)
    
    # User follow-up
    user_notes: str = Field(default="", description="User's personal notes about this lead")
    user_rating: Optional[int] = Field(default=None, ge=1, le=5, description="User's rating 1-5")
    followed_up: bool = Field(default=False)
    followed_up_at: Optional[datetime] = None
    
    # AI-generated insights
    insights: List[str] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True
    
    def set_priority_from_score(self):
        """Set priority based on score"""
        if self.score >= 85:
            self.priority = LeadPriority.HIGH
        elif self.score >= 70:
            self.priority = LeadPriority.MEDIUM
        else:
            self.priority = LeadPriority.LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = self.dict()
        for key in ['created_at', 'updated_at', 'followed_up_at']:
            if isinstance(data.get(key), datetime):
                data[key] = data[key].isoformat()
        if 'conversation' in data and isinstance(data['conversation'].get('last_message_at'), datetime):
            data['conversation']['last_message_at'] = data['conversation']['last_message_at'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lead":
        """Create from dictionary (MongoDB document)"""
        return cls(**data)

