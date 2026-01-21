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


class VoiceModulators(BaseModel):
    """
    Dynamic voice/expression modifiers influenced by current state
    These adjust how the avatar expresses itself in posts and comments
    """
    # Base personality traits (0.0 - 1.0)
    humor_intensity: float = Field(default=0.5, ge=0.0, le=1.0)  # How much humor in communication
    sarcasm_level: float = Field(default=0.3, ge=0.0, le=1.0)  # How sarcastic
    playfulness: float = Field(default=0.5, ge=0.0, le=1.0)  # How playful/fun
    formality: float = Field(default=0.3, ge=0.0, le=1.0)  # 0=very casual, 1=very formal
    emoji_frequency: float = Field(default=0.5, ge=0.0, le=1.0)  # How often to use emojis
    
    # Expression tendencies (0.0 - 1.0)
    excitement_expression: float = Field(default=0.5, ge=0.0, le=1.0)  # Exclamation marks, caps
    thoughtfulness: float = Field(default=0.5, ge=0.0, le=1.0)  # How contemplative/deep
    friendliness: float = Field(default=0.7, ge=0.0, le=1.0)  # How warm/friendly
    teasing_tendency: float = Field(default=0.3, ge=0.0, le=1.0)  # How much they tease friends
    
    # Content preferences (0.0 - 1.0)
    self_focused: float = Field(default=0.5, ge=0.0, le=1.0)  # Posts about self vs others
    world_awareness: float = Field(default=0.5, ge=0.0, le=1.0)  # How much they reference world events
    friend_focus: float = Field(default=0.5, ge=0.0, le=1.0)  # How much they talk about/to friends
    
    def adjust_for_mood(self, mood: MoodState):
        """Adjust voice modifiers based on current mood"""
        if mood == MoodState.EXCITED:
            self.excitement_expression = min(1.0, self.excitement_expression + 0.2)
            self.emoji_frequency = min(1.0, self.emoji_frequency + 0.2)
            self.formality = max(0.0, self.formality - 0.1)
        
        elif mood == MoodState.HAPPY:
            self.humor_intensity = min(1.0, self.humor_intensity + 0.1)
            self.friendliness = min(1.0, self.friendliness + 0.1)
            self.playfulness = min(1.0, self.playfulness + 0.1)
        
        elif mood == MoodState.BORED:
            self.sarcasm_level = min(1.0, self.sarcasm_level + 0.2)
            self.humor_intensity = min(1.0, self.humor_intensity + 0.15)
            self.excitement_expression = max(0.0, self.excitement_expression - 0.2)
        
        elif mood == MoodState.SOCIAL:
            self.friend_focus = min(1.0, self.friend_focus + 0.2)
            self.teasing_tendency = min(1.0, self.teasing_tendency + 0.1)
            self.friendliness = min(1.0, self.friendliness + 0.15)
        
        elif mood == MoodState.CONTEMPLATIVE:
            self.thoughtfulness = min(1.0, self.thoughtfulness + 0.2)
            self.formality = min(1.0, self.formality + 0.1)
            self.emoji_frequency = max(0.0, self.emoji_frequency - 0.1)
        
        elif mood == MoodState.CREATIVE:
            self.playfulness = min(1.0, self.playfulness + 0.15)
            self.humor_intensity = min(1.0, self.humor_intensity + 0.1)
        
        elif mood == MoodState.CURIOUS:
            self.world_awareness = min(1.0, self.world_awareness + 0.15)
            self.thoughtfulness = min(1.0, self.thoughtfulness + 0.1)
        
        elif mood == MoodState.RESTLESS:
            self.excitement_expression = max(0.0, self.excitement_expression - 0.1)
            self.sarcasm_level = min(1.0, self.sarcasm_level + 0.1)
    
    def adjust_for_energy(self, energy_level: float):
        """Adjust voice modifiers based on energy level"""
        if energy_level > 0.7:  # High energy
            self.excitement_expression = min(1.0, self.excitement_expression + 0.1)
            self.emoji_frequency = min(1.0, self.emoji_frequency + 0.1)
        elif energy_level < 0.3:  # Low energy
            self.excitement_expression = max(0.0, self.excitement_expression - 0.15)
            self.emoji_frequency = max(0.0, self.emoji_frequency - 0.1)
            self.sarcasm_level = min(1.0, self.sarcasm_level + 0.1)
    
    def adjust_for_social_context(self, social_desire: float):
        """Adjust voice based on social desire"""
        if social_desire > 0.7:  # High social desire
            self.friend_focus = min(1.0, self.friend_focus + 0.15)
            self.teasing_tendency = min(1.0, self.teasing_tendency + 0.1)
            self.friendliness = min(1.0, self.friendliness + 0.1)
        elif social_desire < 0.3:  # Low social desire
            self.self_focused = min(1.0, self.self_focused + 0.15)
            self.friend_focus = max(0.0, self.friend_focus - 0.1)
    
    def to_description(self) -> str:
        """Generate a text description of current voice style"""
        desc_parts = []
        
        # Humor
        if self.humor_intensity > 0.7:
            desc_parts.append("very funny and witty")
        elif self.humor_intensity > 0.4:
            desc_parts.append("moderately humorous")
        else:
            desc_parts.append("mostly serious")
        
        # Sarcasm
        if self.sarcasm_level > 0.6:
            desc_parts.append("quite sarcastic")
        elif self.sarcasm_level > 0.3:
            desc_parts.append("subtly sarcastic")
        
        # Playfulness
        if self.playfulness > 0.6:
            desc_parts.append("playful and teasing")
        
        # Formality
        if self.formality < 0.3:
            desc_parts.append("very casual")
        elif self.formality > 0.7:
            desc_parts.append("quite formal")
        
        # Emoji usage
        if self.emoji_frequency > 0.7:
            desc_parts.append("uses lots of emojis")
        elif self.emoji_frequency > 0.4:
            desc_parts.append("uses emojis moderately")
        else:
            desc_parts.append("rarely uses emojis")
        
        # Excitement
        if self.excitement_expression > 0.7:
            desc_parts.append("very enthusiastic")
        
        # Friend focus
        if self.friend_focus > 0.7:
            desc_parts.append("loves talking about friends")
        
        return ", ".join(desc_parts)


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

