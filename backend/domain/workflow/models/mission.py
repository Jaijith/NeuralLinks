"""
Mission Model
Represents a user-initiated workflow/mission
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from .enums import MissionType, MissionStatus, MissionPhase, ApproachStyle


class MissionCriteria(BaseModel):
    """Criteria for finding matches/targets"""
    interests: List[str] = Field(default_factory=list, description="Interests to match")
    traits: List[str] = Field(default_factory=list, description="Personality traits to look for")
    keywords: List[str] = Field(default_factory=list, description="Keywords for filtering")
    min_compatibility_score: int = Field(default=60, ge=0, le=100, description="Minimum match score")
    exclude_existing_friends: bool = Field(default=True, description="Exclude current friends")
    exclude_contacted: bool = Field(default=True, description="Exclude already contacted")
    custom_filters: Dict[str, Any] = Field(default_factory=dict, description="Custom filter criteria")


class MissionStrategy(BaseModel):
    """Strategy for executing the mission"""
    approach: ApproachStyle = Field(default=ApproachStyle.CASUAL, description="Conversation approach")
    max_targets: int = Field(default=50, ge=1, le=500, description="Maximum targets to discover")
    max_conversations: int = Field(default=10, ge=1, le=100, description="Maximum conversations to start")
    min_messages_per_target: int = Field(default=1, ge=1, le=10, description="Min messages before moving on")
    max_messages_per_target: int = Field(default=5, ge=1, le=20, description="Max messages per target")
    follow_up_hours: int = Field(default=24, ge=1, le=168, description="Hours to wait before follow-up")
    talking_points: List[str] = Field(default_factory=list, description="Suggested conversation topics")
    custom_instructions: str = Field(default="", description="Custom instructions for the avatar")


class MissionProgress(BaseModel):
    """Progress tracking for a mission"""
    percentage: int = Field(default=0, ge=0, le=100)
    current_action: str = Field(default="Initializing...")
    stats: Dict[str, int] = Field(default_factory=lambda: {
        "profiles_discovered": 0,
        "profiles_evaluated": 0,
        "conversations_started": 0,
        "responses_received": 0,
        "leads_generated": 0
    })


class MissionTimeline(BaseModel):
    """Timeline tracking for mission execution"""
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None


class MissionResultsSummary(BaseModel):
    """Summary of mission results"""
    total_leads: int = 0
    avg_match_score: float = 0.0
    high_priority_leads: int = 0
    top_interest_matches: List[str] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)


class Mission(BaseModel):
    """
    Main Mission model representing a user-initiated workflow.
    
    A mission is created when a user instructs their avatar to find
    matches, leads, or perform any multi-step discovery task.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID of the user who created this mission")
    avatar_id: str = Field(..., description="ID of the avatar executing this mission")
    
    # Mission definition
    type: MissionType = Field(..., description="Type of mission")
    name: str = Field(..., description="User-friendly mission name")
    description: str = Field(default="", description="Optional description")
    
    # Configuration
    criteria: MissionCriteria = Field(default_factory=MissionCriteria)
    strategy: MissionStrategy = Field(default_factory=MissionStrategy)
    
    # State
    status: MissionStatus = Field(default=MissionStatus.DRAFT)
    phase: MissionPhase = Field(default=MissionPhase.INITIALIZING)
    progress: MissionProgress = Field(default_factory=MissionProgress)
    
    # Timeline
    timeline: MissionTimeline = Field(default_factory=MissionTimeline)
    
    # Results
    results_summary: Optional[MissionResultsSummary] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Source chat session (which chat created this mission)
    source_chat_id: Optional[str] = None
    
    class Config:
        use_enum_values = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = self.dict()
        # Convert datetime to ISO format for JSON serialization
        for key in ['created_at', 'updated_at']:
            if isinstance(data.get(key), datetime):
                data[key] = data[key].isoformat()
        if 'timeline' in data:
            for k, v in data['timeline'].items():
                if isinstance(v, datetime):
                    data['timeline'][k] = v.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Mission":
        """Create from dictionary (MongoDB document)"""
        return cls(**data)

