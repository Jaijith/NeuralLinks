"""
Workflow MCP Server and Base Tool
Core infrastructure for workflow MCP tools
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class WorkflowBaseTool:
    """Base class for workflow MCP tools"""
    
    name: str = "base_tool"
    description: str = "Base workflow tool"
    schema: Dict[str, Any] = {}
    
    def __init__(self, db: AsyncIOMotorDatabase, intelligent_avatar=None, openai_client=None):
        self.db = db
        self.intelligent_avatar = intelligent_avatar
        self.openai_client = openai_client
    
    def get_tool_schema(self) -> Dict[str, Any]:
        """Get MCP tool schema definition"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.schema
        }
    
    async def execute(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """Execute the tool action"""
        try:
            return await self._execute_action(avatar_id, **kwargs)
        except Exception as e:
            logger.error(f"Tool {self.name} failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """Override in subclasses to implement the actual action"""
        raise NotImplementedError
    
    async def _get_interests(self, user_id: str) -> List[str]:
        """Helper: Get user interests from knowledge graph"""
        nodes = await self.db.knowledge_graph.find({
            "user_id": user_id,
            "type": "interest"
        }).to_list(100)
        return [n.get("label") for n in nodes if n.get("label")]
    
    async def _get_traits(self, user_id: str) -> List[str]:
        """Helper: Get user traits from knowledge graph"""
        nodes = await self.db.knowledge_graph.find({
            "user_id": user_id,
            "type": "trait"
        }).to_list(50)
        return [n.get("label") for n in nodes if n.get("label")]
    
    async def _get_friend_ids(self, user_id: str) -> List[str]:
        """Helper: Get list of friend IDs"""
        friendships = await self.db.friendships.find({
            "$or": [
                {"user_id": user_id, "status": "accepted"},
                {"friend_id": user_id, "status": "accepted"}
            ]
        }).to_list(1000)
        
        friend_ids = set()
        for f in friendships:
            friend_ids.add(f.get("user_id"))
            friend_ids.add(f.get("friend_id"))
        friend_ids.discard(user_id)
        return list(friend_ids)
    
    async def _log_activity(self, avatar_id: str, activity_type: str, details: Dict):
        """Log workflow activity"""
        user = await self.db.users.find_one({"id": avatar_id})
        activity = {
            "bot_id": avatar_id,
            "user_id": avatar_id,
            "bot_name": user.get('avatar_name', user.get('name', 'Unknown')) if user else 'Unknown',
            "action_type": activity_type,
            "description": f"Workflow action: {activity_type}",
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "workflow"
        }
        await self.db.autonomous_activities.insert_one(activity)


class WorkflowMCPServer:
    """MCP Server with workflow-specific tools"""
    
    def __init__(self, db: AsyncIOMotorDatabase, intelligent_avatar=None, openai_client=None):
        self.db = db
        self.intelligent_avatar = intelligent_avatar
        self.openai_client = openai_client
        self.tools: Dict[str, WorkflowBaseTool] = {}
        
        # Register all workflow tools
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all workflow tools"""
        from .discovery_tools import (
            SearchProfilesTool, GetUserInterestsTool, FilterByCriteriaTool
        )
        from .evaluation_tools import (
            ScoreCompatibilityTool, AnalyzeProfileTool, GetSharedInterestsTool
        )
        from .engagement_tools import (
            SendMissionMessageTool, StartConversationTool, CheckResponseTool
        )
        from .analysis_tools import (
            AnalyzeConversationTool, CreateLeadTool, GenerateSummaryTool
        )
        from .memory_tools import (
            ExtractMemoriesTool, UpdateGraphTool, GetUserContextTool
        )
        from .mission_tools import (
            GetMissionStateTool, UpdateMissionProgressTool, SaveMissionStateTool
        )
        
        tool_classes = [
            # Discovery
            SearchProfilesTool,
            GetUserInterestsTool,
            FilterByCriteriaTool,
            # Evaluation
            ScoreCompatibilityTool,
            AnalyzeProfileTool,
            GetSharedInterestsTool,
            # Engagement
            SendMissionMessageTool,
            StartConversationTool,
            CheckResponseTool,
            # Analysis
            AnalyzeConversationTool,
            CreateLeadTool,
            GenerateSummaryTool,
            # Memory
            ExtractMemoriesTool,
            UpdateGraphTool,
            GetUserContextTool,
            # Mission
            GetMissionStateTool,
            UpdateMissionProgressTool,
            SaveMissionStateTool,
        ]
        
        for tool_class in tool_classes:
            tool = tool_class(self.db, self.intelligent_avatar, self.openai_client)
            self.tools[tool.name] = tool
            logger.info(f"📦 Registered workflow tool: {tool.name}")
    
    def register_tool(self, tool: WorkflowBaseTool):
        """Register a single tool"""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[WorkflowBaseTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        return [tool.get_tool_schema() for tool in self.tools.values()]
    
    async def call_tool(self, tool_name: str, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """Call a tool by name"""
        tool = self.tools.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        logger.info(f"🔧 Calling workflow tool: {tool_name} for avatar {avatar_id[:8]}...")
        result = await tool.execute(avatar_id, **kwargs)
        logger.info(f"✅ Tool {tool_name} completed: success={result.get('success', False)}")
        
        return result

