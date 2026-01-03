"""
Mission Activity Model
Tracks all activities performed during mission execution
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from .enums import AgentType


class MissionActivity(BaseModel):
    """
    Represents a single activity/action performed during mission execution.
    
    Used for audit trail, debugging, and user transparency.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str = Field(..., description="ID of the mission")
    
    # What happened
    action: str = Field(..., description="MCP tool/action name")
    agent_type: AgentType = Field(default=AgentType.ORCHESTRATOR, description="Which agent performed this")
    phase: str = Field(default="", description="Mission phase when this occurred")
    
    # Action details
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_result: Dict[str, Any] = Field(default_factory=dict)
    
    # Outcome
    success: bool = Field(default=True)
    error_message: Optional[str] = None
    
    # Duration
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Context
    target_user_id: Optional[str] = None  # If action was on a specific user
    description: str = Field(default="", description="Human-readable description")
    
    class Config:
        use_enum_values = True
    
    def complete(self, success: bool = True, result: Dict = None, error: str = None):
        """Mark activity as complete"""
        self.completed_at = datetime.now()
        self.success = success
        if result:
            self.output_result = result
        if error:
            self.error_message = error
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = self.dict()
        for key in ['started_at', 'completed_at']:
            if isinstance(data.get(key), datetime):
                data[key] = data[key].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MissionActivity":
        """Create from dictionary (MongoDB document)"""
        return cls(**data)


class AgentTask(BaseModel):
    """
    A task assigned to a worker agent by the orchestrator.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str = Field(..., description="Parent mission ID")
    
    # Task definition
    agent_type: AgentType = Field(..., description="Which agent should handle this")
    action: str = Field(..., description="MCP tool to call")
    params: Dict[str, Any] = Field(default_factory=dict)
    
    # Priority and ordering
    priority: int = Field(default=1, ge=1, le=10)
    depends_on: List[str] = Field(default_factory=list)  # Task IDs this depends on
    
    # Status
    status: str = Field(default="pending")  # pending, running, completed, failed
    retries: int = Field(default=0)
    max_retries: int = Field(default=3)
    
    # Result
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

