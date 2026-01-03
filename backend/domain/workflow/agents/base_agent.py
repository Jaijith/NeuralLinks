"""
Base Agent
Base class for all workflow agents
"""

import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..mcp.tools import WorkflowMCPServer

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for workflow agents.
    
    All agents can call MCP tools to perform actions.
    """
    
    agent_type: str = "base"
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        mcp_server: WorkflowMCPServer,
        openai_client=None
    ):
        self.db = db
        self.mcp_server = mcp_server
        self.openai_client = openai_client
        self.logger = logging.getLogger(f"{__name__}.{self.agent_type}")
    
    async def call_tool(self, tool_name: str, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """Call an MCP tool"""
        self.logger.info(f"🔧 {self.agent_type} calling tool: {tool_name}")
        result = await self.mcp_server.call_tool(tool_name, avatar_id, **kwargs)
        return result
    
    async def think(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to think about what to do next.
        Override in subclasses for agent-specific reasoning.
        """
        if not self.openai_client:
            return {"decision": "continue", "reason": "No LLM available"}
        
        return {"decision": "continue", "reason": "Default behavior"}
    
    @abstractmethod
    async def execute(self, mission_id: str, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """
        Execute the agent's task.
        Must be implemented by subclasses.
        """
        raise NotImplementedError
    
    async def log_activity(
        self,
        mission_id: str,
        action: str,
        result: Dict[str, Any],
        target_user_id: Optional[str] = None
    ):
        """Log agent activity to the database"""
        from datetime import datetime, timezone
        
        activity = {
            "mission_id": mission_id,
            "agent_type": self.agent_type,
            "action": action,
            "output_result": result,
            "success": result.get("success", False),
            "target_user_id": target_user_id,
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.mission_activities.insert_one(activity)

