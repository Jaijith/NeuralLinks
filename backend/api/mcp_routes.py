"""
MCP (Model Context Protocol) Server Routes
Exposes avatar actions as callable tools with permission checks
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
import asyncio
import logging

router = APIRouter(prefix="/api/mcp", tags=["mcp"])
logger = logging.getLogger(__name__)


# Lazy import to avoid circular dependencies
def get_mcp_server():
    """Lazy import MCP server"""
    from domain.avatar.mcp.server import mcp_server, initialize_intelligent_avatar
    # Initialize on first access
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(initialize_intelligent_avatar())
    except RuntimeError:
        # No event loop running, will initialize later
        pass
    return mcp_server


@router.get("/tools")
async def list_mcp_tools():
    """List all available MCP tools"""
    mcp = get_mcp_server()
    tools = mcp.get_tools_list()
    return {"tools": tools}


@router.get("/tools/available")
async def get_available_tools(avatar_id: str = Query(..., description="Avatar ID to check permissions for")):
    """Get list of tools available for a specific avatar based on permissions"""
    mcp = get_mcp_server()
    tools = await mcp.get_available_tools_for_avatar(avatar_id)
    return {"tools": tools}


@router.post("/tools/call")
async def call_mcp_tool(data: Dict[str, Any]):
    """Call an MCP tool for a specific avatar"""
    mcp = get_mcp_server()
    tool_name = data.get("tool_name")
    avatar_id = data.get("avatar_id")
    arguments = data.get("arguments", {})
    
    if not tool_name:
        raise HTTPException(status_code=400, detail="tool_name is required")
    if not avatar_id:
        raise HTTPException(status_code=400, detail="avatar_id is required")
    
    result = await mcp.call_tool(tool_name, avatar_id, arguments)
    return result

