"""
Engagement MCP Tools
Tools for starting and managing conversations
"""

import logging
import uuid
from typing import Dict, List, Any
from datetime import datetime, timezone
from .tools import WorkflowBaseTool

logger = logging.getLogger(__name__)


class SendMissionMessageTool(WorkflowBaseTool):
    """Send a message as part of a mission workflow"""
    
    name = "send_mission_message"
    description = "Send a message to another user as part of a mission"
    
    schema = {
        "type": "object",
        "properties": {
            "recipient_id": {
                "type": "string",
                "description": "User ID to send message to"
            },
            "message_text": {
                "type": "string",
                "description": "Message content (optional - will be generated if not provided)"
            },
            "context": {
                "type": "object",
                "description": "Context for message generation",
                "properties": {
                    "mission_type": {"type": "string"},
                    "shared_interests": {"type": "array"},
                    "approach": {"type": "string"}
                }
            },
            "conversation_id": {
                "type": "string",
                "description": "Existing conversation ID (optional)"
            }
        },
        "required": ["recipient_id"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        recipient_id = kwargs.get("recipient_id")
        message_text = kwargs.get("message_text")
        context = kwargs.get("context", {})
        conversation_id = kwargs.get("conversation_id")
        
        logger.info(f"📤 Sending mission message from {avatar_id[:8]} to {recipient_id[:8]}")
        
        # Generate message if not provided
        if not message_text and self.intelligent_avatar:
            shared_interests = context.get("shared_interests", [])
            approach = context.get("approach", "casual")
            
            # Get conversation history if exists
            conversation_history = []
            if conversation_id:
                conv = await self.db.agent_conversations.find_one({"id": conversation_id})
                if conv:
                    conversation_history = [
                        {"role": "user" if m.get("sender") != avatar_id else "assistant", 
                         "content": m.get("content", "")}
                        for m in conv.get("messages", [])[-5:]
                    ]
            
            try:
                result = await self.intelligent_avatar.generate_chat_response(
                    user_id=avatar_id,
                    other_user_id=recipient_id,
                    conversation_history=conversation_history,
                    last_message=conversation_history[-1].get("content", "") if conversation_history else ""
                )
                
                if "error" not in result:
                    message_text = result.get("content", "").strip()
            except Exception as e:
                logger.error(f"Failed to generate message: {e}")
        
        if not message_text:
            return {"success": False, "error": "Could not generate message"}
        
        # Create or update conversation
        now = datetime.now(timezone.utc)
        message = {
            "id": str(uuid.uuid4()),
            "sender": avatar_id,
            "content": message_text,
            "timestamp": now.isoformat()
        }
        
        if conversation_id:
            # Add to existing conversation
            await self.db.agent_conversations.update_one(
                {"id": conversation_id},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": now.isoformat()}
                }
            )
        else:
            # Create new conversation
            conversation_id = str(uuid.uuid4())
            await self.db.agent_conversations.insert_one({
                "id": conversation_id,
                "participants": [avatar_id, recipient_id],
                "messages": [message],
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "source": "mission"
            })
        
        # Log activity
        await self._log_activity(avatar_id, "mission_message", {
            "recipient_id": recipient_id,
            "conversation_id": conversation_id,
            "message_preview": message_text[:50]
        })
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "message_sent": message_text[:100] + "..." if len(message_text) > 100 else message_text,
            "timestamp": now.isoformat()
        }


class StartConversationTool(WorkflowBaseTool):
    """Start a new conversation with personalized opener"""
    
    name = "start_conversation"
    description = "Initiate a conversation with a target user based on shared interests"
    
    schema = {
        "type": "object",
        "properties": {
            "target_user_id": {
                "type": "string",
                "description": "User to start conversation with"
            },
            "mission_type": {
                "type": "string",
                "enum": ["matchmaking", "networking", "sales_leads", "job_finder"],
                "description": "Type of mission context"
            },
            "talking_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Suggested topics to discuss"
            }
        },
        "required": ["target_user_id"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        target_id = kwargs.get("target_user_id")
        mission_type = kwargs.get("mission_type", "matchmaking")
        talking_points = kwargs.get("talking_points", [])
        
        logger.info(f"💬 Starting conversation: {avatar_id[:8]} -> {target_id[:8]}, type={mission_type}")
        
        # Get shared interests for context
        avatar_interests = set(await self._get_interests(avatar_id))
        target_interests = set(await self._get_interests(target_id))
        shared_interests = list(avatar_interests & target_interests)[:5]
        
        # Get target user info
        target_user = await self.db.users.find_one({"id": target_id})
        target_name = target_user.get("avatar_name", "there") if target_user else "there"
        
        # Generate opener
        opener = None
        if self.intelligent_avatar:
            try:
                result = await self.intelligent_avatar.generate_chat_response(
                    user_id=avatar_id,
                    other_user_id=target_id,
                    conversation_history=[],
                    last_message=""
                )
                
                if "error" not in result:
                    opener = result.get("content", "").strip()
            except Exception as e:
                logger.error(f"Failed to generate opener: {e}")
        
        # Fallback opener if generation failed
        if not opener:
            if shared_interests:
                opener = f"Hey {target_name}! I noticed we both share an interest in {shared_interests[0]}. What got you into it?"
            else:
                opener = f"Hey {target_name}! I came across your profile and thought it would be great to connect. How's it going?"
        
        # Create conversation
        now = datetime.now(timezone.utc)
        conversation_id = str(uuid.uuid4())
        
        await self.db.agent_conversations.insert_one({
            "id": conversation_id,
            "participants": [avatar_id, target_id],
            "messages": [{
                "id": str(uuid.uuid4()),
                "sender": avatar_id,
                "content": opener,
                "timestamp": now.isoformat()
            }],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "source": "mission",
            "mission_type": mission_type
        })
        
        # Log activity
        await self._log_activity(avatar_id, "start_conversation", {
            "target_id": target_id,
            "conversation_id": conversation_id,
            "mission_type": mission_type,
            "shared_interests": shared_interests
        })
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "opener_message": opener,
            "shared_interests_used": shared_interests,
            "timestamp": now.isoformat()
        }


class CheckResponseTool(WorkflowBaseTool):
    """Check if there's a response in a conversation"""
    
    name = "check_response"
    description = "Check if the target user has responded to a conversation"
    
    schema = {
        "type": "object",
        "properties": {
            "conversation_id": {
                "type": "string",
                "description": "Conversation ID to check"
            }
        },
        "required": ["conversation_id"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        conversation_id = kwargs.get("conversation_id")
        
        conversation = await self.db.agent_conversations.find_one({"id": conversation_id})
        
        if not conversation:
            return {"success": False, "error": "Conversation not found"}
        
        messages = conversation.get("messages", [])
        
        # Check if there's a response from someone other than the avatar
        responses = [m for m in messages if m.get("sender") != avatar_id]
        avatar_messages = [m for m in messages if m.get("sender") == avatar_id]
        
        last_response = None
        if responses:
            last_response = {
                "content": responses[-1].get("content", ""),
                "timestamp": responses[-1].get("timestamp"),
                "sender": responses[-1].get("sender")
            }
        
        return {
            "success": True,
            "has_response": len(responses) > 0,
            "response_count": len(responses),
            "avatar_message_count": len(avatar_messages),
            "last_response": last_response,
            "total_messages": len(messages),
            "conversation_status": "active" if responses else "awaiting_response"
        }

