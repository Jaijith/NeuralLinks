"""
Internal State
Avatar's internal mental and emotional state
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
from .state_models import MoodState, Goal


class InternalState(BaseModel):
    """
    Avatar's internal mental and emotional state
    
    This represents what the avatar is feeling, thinking, and desiring
    """
    
    # Mood and emotional state
    mood: MoodState = MoodState.NEUTRAL
    
    # Energy and desire levels (0.0 - 1.0)
    energy_level: float = Field(default=0.5, ge=0.0, le=1.0)
    social_desire: float = Field(default=0.5, ge=0.0, le=1.0)  # How much it wants to interact
    creative_urge: float = Field(default=0.5, ge=0.0, le=1.0)  # How much it wants to create
    focus_level: float = Field(default=0.5, ge=0.0, le=1.0)  # How focused it is on a task/goal
    
    # Temporal states (time since last actions)
    time_since_last_action: timedelta = Field(default_factory=lambda: timedelta(0))
    time_since_last_post: timedelta = Field(default_factory=lambda: timedelta(0))
    time_since_last_conversation: timedelta = Field(default_factory=lambda: timedelta(0))
    time_since_last_reaction: timedelta = Field(default_factory=lambda: timedelta(0))
    
    # Goals and objectives
    goals: List[Goal] = Field(default_factory=list)
    
    # Memory and context
    memory_summary: str = ""  # LLM-generated summary of recent memories/experiences
    recent_thoughts: List[str] = Field(default_factory=list)  # Recent thoughts/considerations
    
    # State metadata
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    state_version: int = Field(default=1)  # For tracking state evolution
    
    def update_temporal_states(self, last_action_time: Optional[datetime] = None,
                              last_post_time: Optional[datetime] = None,
                              last_conversation_time: Optional[datetime] = None,
                              last_reaction_time: Optional[datetime] = None):
        """Update temporal states based on current time"""
        now = datetime.now(timezone.utc)
        
        # Helper to ensure timezone-aware datetime
        def ensure_timezone_aware(dt: Optional[datetime]) -> Optional[datetime]:
            if dt is None:
                return None
            if dt.tzinfo is None:
                # Naive datetime - assume UTC
                return dt.replace(tzinfo=timezone.utc)
            return dt
        
        if last_action_time:
            last_action_time = ensure_timezone_aware(last_action_time)
            if last_action_time:
                self.time_since_last_action = now - last_action_time
        
        if last_post_time:
            last_post_time = ensure_timezone_aware(last_post_time)
            if last_post_time:
                self.time_since_last_post = now - last_post_time
        
        if last_conversation_time:
            last_conversation_time = ensure_timezone_aware(last_conversation_time)
            if last_conversation_time:
                self.time_since_last_conversation = now - last_conversation_time
        
        if last_reaction_time:
            last_reaction_time = ensure_timezone_aware(last_reaction_time)
            if last_reaction_time:
                self.time_since_last_reaction = now - last_reaction_time
        
        self.last_updated = now
    
    def add_goal(self, goal: Goal):
        """Add a new goal"""
        self.goals.append(goal)
        # Keep only active goals (remove completed ones)
        self.goals = [g for g in self.goals if g.progress < 1.0]
    
    def update_goal_progress(self, goal_id: str, progress: float):
        """Update progress on a goal"""
        for goal in self.goals:
            if goal.id == goal_id:
                goal.progress = min(max(progress, 0.0), 1.0)
                break
    
    def get_active_goals(self) -> List[Goal]:
        """Get all active (incomplete) goals"""
        return [g for g in self.goals if g.progress < 1.0]
    
    def get_high_priority_goals(self, threshold: float = 0.7) -> List[Goal]:
        """Get goals with priority above threshold"""
        return [g for g in self.get_active_goals() if g.priority >= threshold]
    
    def decay_energy(self, decay_rate: float = 0.1):
        """Gradually decay energy level over time"""
        self.energy_level = max(0.0, self.energy_level - decay_rate)
    
    def boost_energy(self, boost_amount: float = 0.2):
        """Boost energy level (e.g., from positive interactions)"""
        self.energy_level = min(1.0, self.energy_level + boost_amount)
    
    def adjust_mood(self, new_mood: MoodState, reason: str = ""):
        """Change mood state"""
        self.mood = new_mood
        # Mood changes can affect energy and desires
        if new_mood in [MoodState.HAPPY, MoodState.EXCITED, MoodState.CREATIVE]:
            self.boost_energy(0.1)
        elif new_mood in [MoodState.BORED, MoodState.RESTLESS]:
            self.decay_energy(0.05)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "mood": self.mood.value,
            "energy_level": self.energy_level,
            "social_desire": self.social_desire,
            "creative_urge": self.creative_urge,
            "focus_level": self.focus_level,
            "time_since_last_action_seconds": self.time_since_last_action.total_seconds(),
            "time_since_last_post_seconds": self.time_since_last_post.total_seconds(),
            "time_since_last_conversation_seconds": self.time_since_last_conversation.total_seconds(),
            "time_since_last_reaction_seconds": self.time_since_last_reaction.total_seconds(),
            "goals": [goal.model_dump() for goal in self.goals],
            "memory_summary": self.memory_summary,
            "recent_thoughts": self.recent_thoughts,
            "last_updated": self.last_updated.isoformat(),
            "state_version": self.state_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InternalState":
        """Create from dictionary"""
        # Convert timedelta from seconds
        if "time_since_last_action_seconds" in data:
            data["time_since_last_action"] = timedelta(seconds=data.pop("time_since_last_action_seconds"))
        if "time_since_last_post_seconds" in data:
            data["time_since_last_post"] = timedelta(seconds=data.pop("time_since_last_post_seconds"))
        if "time_since_last_conversation_seconds" in data:
            data["time_since_last_conversation"] = timedelta(seconds=data.pop("time_since_last_conversation_seconds"))
        if "time_since_last_reaction_seconds" in data:
            data["time_since_last_reaction"] = timedelta(seconds=data.pop("time_since_last_reaction_seconds"))
        
        # Convert mood string to enum
        if "mood" in data and isinstance(data["mood"], str):
            try:
                data["mood"] = MoodState(data["mood"])
            except ValueError:
                data["mood"] = MoodState.NEUTRAL
        
        # Convert goals
        if "goals" in data:
            goals_data = data["goals"]
            data["goals"] = [Goal(**g) if isinstance(g, dict) else g for g in goals_data]
        
        # Convert datetime strings
        if "last_updated" in data and isinstance(data["last_updated"], str):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"].replace('Z', '+00:00'))
        
        return cls(**data)

