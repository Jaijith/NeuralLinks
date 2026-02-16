"""
Skill Router Layer
Routes execution to the correct provider (MCP tools or workflow engines).
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SkillRouter:
    """Layer 5: Routes to the correct MCP tool or workflow engine"""

    def __init__(self, mcp_server, engine_registry=None):
        self.mcp_server = mcp_server
        self.engine_registry = engine_registry

    async def execute_mcp_tool(self, tool_name: str, avatar_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to AvatarMCPServer — call tool's _execute_action directly to skip double permission check"""
        try:
            if hasattr(self.mcp_server, 'tools'):
                tool = self.mcp_server.tools.get(tool_name)
                if not tool:
                    return {"success": False, "error": f"Tool '{tool_name}' not found in MCP server"}
                return await tool._execute_action(avatar_id, **arguments)
            else:
                return await self.mcp_server.call_tool(tool_name, avatar_id, arguments)
        except Exception as e:
            logger.error(f"MCP tool execution failed for {tool_name}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def execute_engine(
        self,
        mission_type: str,
        mission_id: str,
        avatar_id: str,
        db: Any,
        openai_client: Any = None,
        intelligent_avatar: Any = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Route to WorkflowEngineRegistry"""
        try:
            if not self.engine_registry:
                return {"success": False, "error": "Engine registry not available"}

            engine = self.engine_registry.get_engine(
                mission_type, db, self.mcp_server,
                openai_client=openai_client,
                intelligent_avatar=intelligent_avatar,
            )
            if not engine:
                return {"success": False, "error": f"No engine registered for '{mission_type}'"}

            return await engine.execute(mission_id, avatar_id, **kwargs)
        except Exception as e:
            logger.error(f"Engine execution failed for {mission_type}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
