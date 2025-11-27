"""
External State
Avatar's perception of the external environment
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ExternalState(BaseModel):
    """
    Avatar's perception of the external environment
    
    This represents what the avatar perceives about the world around them,
    derived from the PerceptionEngine
    """
    
    # Social network state (from SocialNetworkPerception)
    social_network_state: Dict[str, Any] = Field(default_factory=dict)
    # Contains: friend_activity_level, recent_posts, trending_topics, etc.
    
    # Relationship state (from RelationshipPerception)
    relationship_state: Dict[str, Any] = Field(default_factory=dict)
    # Contains: relationship_map, relationship_types, social_status, etc.
    
    # Environment state (from EnvironmentPerception)
    environment_state: Dict[str, Any] = Field(default_factory=dict)
    # Contains: temporal_context, content_trends, platform_state, etc.
    
    # Current task context
    current_task_context: Dict[str, Any] = Field(default_factory=dict)
    # Contains: current_action, action_history, pending_followups, etc.
    
    # Convenience fields (derived from above)
    friend_activity_level: float = Field(default=0.0, ge=0.0, le=1.0)
    unread_messages: int = Field(default=0, ge=0)
    pending_friend_requests: int = Field(default=0, ge=0)
    time_of_day: str = "unknown"
    is_weekend: bool = False
    platform_activity_level: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # State metadata
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    perception_timestamp: Optional[datetime] = None  # When perception was gathered
    
    def update_from_perception(self, perception_data: Dict[str, Any]):
        """
        Update external state from perception engine output
        
        Args:
            perception_data: Output from PerceptionEngine.perceive_all()
        """
        # Update main state dictionaries
        self.social_network_state = perception_data.get("social_network", {})
        self.relationship_state = perception_data.get("relationships", {})
        self.environment_state = perception_data.get("environment", {})
        
        # Update convenience fields
        self.friend_activity_level = perception_data.get("friend_activity_level", 0.0)
        self.unread_messages = perception_data.get("unread_messages", 0)
        self.pending_friend_requests = perception_data.get("pending_friend_requests", 0)
        self.time_of_day = perception_data.get("time_of_day", "unknown")
        self.is_weekend = perception_data.get("is_weekend", False)
        self.platform_activity_level = perception_data.get("platform_activity_level", 0.5)
        
        # Update perception timestamp
        perceived_at = perception_data.get("perceived_at")
        if perceived_at:
            if isinstance(perceived_at, str):
                self.perception_timestamp = datetime.fromisoformat(perceived_at.replace('Z', '+00:00'))
            else:
                self.perception_timestamp = perceived_at
        
        self.last_updated = datetime.now(timezone.utc)
    
    def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent posts from social network state"""
        friend_activity = self.social_network_state.get("friend_activity", {})
        return friend_activity.get("recent_posts", [])[:limit]
    
    def get_relationship_map(self) -> Dict[str, Any]:
        """Get relationship map from relationship state"""
        relationship_context = self.relationship_state.get("context", {})
        return relationship_context.get("relationship_map", {})
    
    def get_relationship_types(self) -> Dict[str, str]:
        """Get relationship types (friend_id -> type)"""
        relationship_context = self.relationship_state.get("context", {})
        return relationship_context.get("relationship_types", {})
    
    def get_trending_topics(self, limit: int = 10) -> List[str]:
        """Get trending topics from environment state"""
        content_trends = self.environment_state.get("content_trends", {})
        return content_trends.get("trending_topics", [])[:limit]
    
    def has_unread_interactions(self) -> bool:
        """Check if there are unread messages or pending requests"""
        return self.unread_messages > 0 or self.pending_friend_requests > 0
    
    def is_high_activity_period(self) -> bool:
        """Check if current period has high activity"""
        return self.friend_activity_level > 0.5 or self.platform_activity_level > 0.7
    
    def get_social_status(self) -> Dict[str, Any]:
        """Get social status metrics"""
        return self.relationship_state.get("social_status", {})
    
    def get_content_opportunities(self) -> List[Dict[str, Any]]:
        """Get posts/content worth engaging with"""
        # This could be enhanced to filter posts based on various criteria
        recent_posts = self.get_recent_posts(limit=50)
        
        # Filter posts with engagement potential
        opportunities = []
        for post in recent_posts:
            # Posts with some engagement are worth engaging with
            likes = post.get('likes', 0)
            comments = post.get('comment_count', 0)
            if likes > 0 or comments > 0:
                opportunities.append(post)
        
        return opportunities
    
    def update_task_context(self, task_data: Dict[str, Any]):
        """Update current task context"""
        self.current_task_context.update(task_data)
        self.last_updated = datetime.now(timezone.utc)
    
    def clear_task_context(self):
        """Clear current task context"""
        self.current_task_context = {}
        self.last_updated = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "social_network_state": self.social_network_state,
            "relationship_state": self.relationship_state,
            "environment_state": self.environment_state,
            "current_task_context": self.current_task_context,
            "friend_activity_level": self.friend_activity_level,
            "unread_messages": self.unread_messages,
            "pending_friend_requests": self.pending_friend_requests,
            "time_of_day": self.time_of_day,
            "is_weekend": self.is_weekend,
            "platform_activity_level": self.platform_activity_level,
            "last_updated": self.last_updated.isoformat(),
            "perception_timestamp": self.perception_timestamp.isoformat() if self.perception_timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExternalState":
        """Create from dictionary"""
        # Convert datetime strings
        if "last_updated" in data and isinstance(data["last_updated"], str):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"].replace('Z', '+00:00'))
        
        if "perception_timestamp" in data and data["perception_timestamp"]:
            if isinstance(data["perception_timestamp"], str):
                data["perception_timestamp"] = datetime.fromisoformat(
                    data["perception_timestamp"].replace('Z', '+00:00')
                )
        
        return cls(**data)

