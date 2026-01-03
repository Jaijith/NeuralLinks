"""
Avatar Chat Models
Models for user-avatar chat sessions and messages
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from .enums import MessageRole


class ExtractedMemory(BaseModel):
    """Memory extracted from a chat message"""
    type: str  # interest, preference, goal, fact
    label: str
    confidence: float = 0.5
    sentiment: Optional[str] = None  # positive, negative, neutral


class AvatarChatMessage(BaseModel):
    """A single message in an avatar chat session"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole = Field(..., description="Who sent this message")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Intent detection (for user messages)
    detected_intent: Optional[str] = None  # start_mission, ask_question, give_feedback, etc.
    intent_confidence: Optional[float] = None
    
    # Extracted data
    extracted_memories: List[ExtractedMemory] = Field(default_factory=list)
    
    # If this message triggered a mission
    triggered_mission_id: Optional[str] = None
    
    # Tool calls made by avatar
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class AvatarChatSession(BaseModel):
    """
    A chat session between user and their avatar.
    
    Used for giving instructions, asking questions, and
    receiving updates about missions.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID of the user")
    avatar_id: str = Field(..., description="ID of the avatar")
    
    # Messages
    messages: List[AvatarChatMessage] = Field(default_factory=list)
    
    # Session state
    is_active: bool = Field(default=True)
    last_activity_at: datetime = Field(default_factory=datetime.now)
    
    # Context for the conversation
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Linked missions from this session
    mission_ids: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def add_message(self, role: MessageRole, content: str, **kwargs) -> AvatarChatMessage:
        """Add a message to the session"""
        message = AvatarChatMessage(role=role, content=content, **kwargs)
        self.messages.append(message)
        self.last_activity_at = datetime.now()
        self.updated_at = datetime.now()
        return message
    
    def get_conversation_history(self, limit: int = 20) -> List[Dict[str, str]]:
        """Get recent conversation history for LLM context"""
        recent_messages = self.messages[-limit:]
        return [
            {"role": msg.role if msg.role != "avatar" else "assistant", "content": msg.content}
            for msg in recent_messages
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = self.dict()
        for key in ['last_activity_at', 'created_at', 'updated_at']:
            if isinstance(data.get(key), datetime):
                data[key] = data[key].isoformat()
        for msg in data.get('messages', []):
            if isinstance(msg.get('timestamp'), datetime):
                msg['timestamp'] = msg['timestamp'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AvatarChatSession":
        """Create from dictionary (MongoDB document)"""
        return cls(**data)

