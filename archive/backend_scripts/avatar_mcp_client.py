"""
MCP Client for Avatar Actions
Client library to interact with the Avatar MCP Server
"""

import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime


class AvatarMCPClient:
    """Client for interacting with Avatar MCP Server"""
    
    def __init__(self, server_url: str = "http://localhost:8001"):
        self.server_url = server_url
        self.base_url = f"{server_url}/api/mcp"
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/tools")
            response.raise_for_status()
            return response.json().get("tools", [])
    
    async def get_available_tools(self, avatar_id: str) -> List[Dict[str, Any]]:
        """Get list of tools available for a specific avatar"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/tools/available",
                params={"avatar_id": avatar_id}
            )
            response.raise_for_status()
            return response.json().get("tools", [])
    
    async def call_tool(self, tool_name: str, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """Call a tool for a specific avatar"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tools/call",
                json={
                    "tool_name": tool_name,
                    "avatar_id": avatar_id,
                    "arguments": kwargs
                }
            )
            response.raise_for_status()
            return response.json()
    
    # Convenience methods for each tool
    async def like_post(self, avatar_id: str, post_id: str) -> Dict[str, Any]:
        """Like a post"""
        return await self.call_tool("like_post", avatar_id, post_id=post_id)
    
    async def comment_on_post(self, avatar_id: str, post_id: str, comment_text: Optional[str] = None) -> Dict[str, Any]:
        """Comment on a post"""
        args = {"post_id": post_id}
        if comment_text:
            args["comment_text"] = comment_text
        return await self.call_tool("comment_on_post", avatar_id, **args)
    
    async def create_post(self, avatar_id: str, post_type: str = "general", post_text: Optional[str] = None) -> Dict[str, Any]:
        """Create a post"""
        args = {"post_type": post_type}
        if post_text:
            args["post_text"] = post_text
        return await self.call_tool("create_post", avatar_id, **args)
    
    async def send_friend_request(self, avatar_id: str, target_user_id: str) -> Dict[str, Any]:
        """Send a friend request"""
        return await self.call_tool("send_friend_request", avatar_id, target_user_id=target_user_id)
    
    async def accept_friend_request(self, avatar_id: str, friendship_id: str) -> Dict[str, Any]:
        """Accept a friend request"""
        return await self.call_tool("accept_friend_request", avatar_id, friendship_id=friendship_id)
    
    async def message_friend(self, avatar_id: str, friend_id: str, message_text: Optional[str] = None) -> Dict[str, Any]:
        """Send a message to a friend"""
        args = {"friend_id": friend_id}
        if message_text:
            args["message_text"] = message_text
        return await self.call_tool("message_friend", avatar_id, **args)
    
    async def discover_profiles(self, avatar_id: str, limit: int = 5) -> Dict[str, Any]:
        """Discover profiles"""
        return await self.call_tool("discover_profiles", avatar_id, limit=limit)
    
    async def share_post(self, avatar_id: str, post_id: str) -> Dict[str, Any]:
        """Share a post (not yet implemented)"""
        return await self.call_tool("share_post", avatar_id, post_id=post_id)

