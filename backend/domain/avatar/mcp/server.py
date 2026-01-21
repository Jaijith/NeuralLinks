"""
MCP Server for Avatar Actions
Exposes all avatar actions as MCP tools with permission-based access control
"""

import asyncio
import json
import sys
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.avatar.intelligent import IntelligentAvatar
from pathlib import Path
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection - use core database module
from core.database import get_database, DB_NAME, MONGODB_URI
db = get_database()
print(f"🔧 MCP Server DB initialized: name={DB_NAME}, uri_set={bool(MONGODB_URI)}")

# Initialize IntelligentAvatar (will be set when server starts)
intelligent_avatar: Optional[IntelligentAvatar] = None


class AvatarMCPTool:
    """Base class for avatar action tools"""
    
    def __init__(self, name: str, description: str, action_key: str):
        self.name = name
        self.description = description
        self.action_key = action_key
    
    def get_tool_schema(self) -> Dict[str, Any]:
        """Get MCP tool schema definition"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.get_input_schema()
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Override in subclasses to define input parameters"""
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    async def check_permission(self, avatar_id: str) -> bool:
        """Check if avatar has permission to use this tool"""
        print(f"🔍 Checking permission: action_key={self.action_key}, avatar_id={avatar_id}")
        print(f"   DB name: {getattr(db, 'name', 'unknown')}, DB type: {type(db)}")
        
        # Try the query
        try:
            user = await db.users.find_one({"id": avatar_id})
            print(f"   Query result: {user is not None}")
            if user:
                print(f"   Found user: {user.get('avatar_name', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Query error: {e}")
            return False
        
        if not user:
            # Try to find by avatar_name as fallback
            print(f"❌ User not found by ID: {avatar_id[:8]}...")
            # Count total users to see if db is working
            try:
                total_users = await db.users.count_documents({})
                print(f"📊 Total users in DB: {total_users}")
                # Try to find any user with similar ID
                sample_user = await db.users.find_one({}, {"id": 1, "avatar_name": 1})
                if sample_user:
                    print(f"📋 Sample user ID format: {sample_user.get('id', 'N/A')[:20]}...")
            except Exception as e:
                print(f"   ❌ Count error: {e}")
            return False
        
        actions_enabled = user.get('avatar_actions_enabled', {})
        permission_value = actions_enabled.get(self.action_key, True)  # Default to True
        print(f"🔐 Permission check for {self.action_key}: {permission_value} (avatar_id: {avatar_id[:8]}..., actions_enabled: {actions_enabled})")
        return permission_value
    
    async def execute(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """Execute the tool action"""
        # Check permission first
        if not await self.check_permission(avatar_id):
            return {
                "success": False,
                "error": f"Action '{self.action_key}' is disabled for this avatar"
            }
        
        # Execute the action
        return await self._execute_action(avatar_id, **kwargs)
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """Override in subclasses to implement the actual action"""
        raise NotImplementedError


class LikePostTool(AvatarMCPTool):
    """Tool for liking posts"""
    
    def __init__(self):
        super().__init__(
            name="like_post",
            description="Like a post from a friend or in the feed",
            action_key="like_posts"
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "The ID of the post to like"
                }
            },
            "required": ["post_id"]
        }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        post_id = kwargs.get('post_id')
        
        # Get post
        post = await db.posts.find_one({"id": post_id})
        if not post:
            return {"success": False, "error": "Post not found"}
        
        # Check if already liked
        if avatar_id in post.get('liked_by', []):
            return {"success": False, "error": "Post already liked"}
        
        # Like the post
        await db.posts.update_one(
            {"id": post_id},
            {
                "$addToSet": {"liked_by": avatar_id},
                "$inc": {"likes": 1}
            }
        )
        
        # Log activity
        await self._log_activity(avatar_id, "post_like", {"post_id": post_id})
        
        return {
            "success": True,
            "message": f"Liked post {post_id}",
            "post_id": post_id
        }
    
    async def _log_activity(self, avatar_id: str, activity_type: str, details: Dict):
        """Log avatar activity"""
        user = await db.users.find_one({"id": avatar_id})
        activity = {
            "bot_id": avatar_id,
            "user_id": avatar_id,
            "bot_name": user.get('avatar_name', user.get('name', 'Unknown')) if user else 'Unknown',
            "action_type": activity_type,
            "description": f"Liked a post",
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.autonomous_activities.insert_one(activity)


class CommentOnPostTool(AvatarMCPTool):
    """Tool for commenting on posts"""
    
    def __init__(self):
        super().__init__(
            name="comment_on_post",
            description="Comment on a post from a friend or in the feed",
            action_key="comment_posts"
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "The ID of the post to comment on"
                },
                "comment_text": {
                    "type": "string",
                    "description": "Optional: Custom comment text. If not provided, AI will generate one."
                }
            },
            "required": ["post_id"]
        }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        global intelligent_avatar
        
        post_id = kwargs.get('post_id')
        comment_text = kwargs.get('comment_text')
        
        # Get post
        post = await db.posts.find_one({"id": post_id})
        if not post:
            return {"success": False, "error": "Post not found"}
        
        # Generate comment if not provided
        # Initialize intelligent_avatar if not already initialized
        if intelligent_avatar is None:
            logger.info("🔄 intelligent_avatar is None for comment, initializing now...")
            await initialize_intelligent_avatar()
        
        if not comment_text and intelligent_avatar:
            post_text = post.get('text', post.get('content', ''))
            post_author = post.get('user_id', 'someone')
            
            result = await intelligent_avatar.generate_chat_response(
                user_id=avatar_id,
                other_user_id=post_author,
                conversation_history=[],
                last_message=post_text
            )
            
            if 'error' not in result:
                comment_text = result.get('content', '').strip()
                # Keep it short for a comment
                if len(comment_text) > 200:
                    sentences = comment_text.split('. ')
                    comment_text = sentences[0] + '.' if sentences else comment_text[:197] + "..."
        
        if not comment_text:
            return {"success": False, "error": "Failed to generate comment"}
        
        # Create comment
        user = await db.users.find_one({"id": avatar_id})
        comment = {
            "id": f"comment-{datetime.now(timezone.utc).timestamp()}",
            "user_id": avatar_id,
            "user_name": user.get('avatar_name', user.get('name', 'Unknown')) if user else 'Unknown',
            "user_picture": user.get('avatar_picture', user.get('picture', '')) if user else '',
            "text": comment_text,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add comment to post
        await db.posts.update_one(
            {"id": post_id},
            {"$push": {"comments": comment}, "$inc": {"comment_count": 1}}
        )
        
        # Log activity
        await self._log_activity(avatar_id, "post_comment", {
            "post_id": post_id,
            "comment_text": comment_text
        })
        
        return {
            "success": True,
            "message": f"Commented on post {post_id}",
            "post_id": post_id,
            "comment": comment_text
        }
    
    async def _log_activity(self, avatar_id: str, activity_type: str, details: Dict):
        """Log avatar activity"""
        user = await db.users.find_one({"id": avatar_id})
        activity = {
            "bot_id": avatar_id,
            "user_id": avatar_id,
            "bot_name": user.get('avatar_name', user.get('name', 'Unknown')) if user else 'Unknown',
            "action_type": activity_type,
            "description": f"Commented: \"{details.get('comment_text', '')[:50]}...\"",
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.autonomous_activities.insert_one(activity)


class CreatePostTool(AvatarMCPTool):
    """Tool for creating posts"""
    
    def __init__(self):
        super().__init__(
            name="create_post",
            description="Create and publish a new post",
            action_key="create_posts"
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "post_type": {
                    "type": "string",
                    "enum": ["auto", "general", "interest", "thought", "experience", "friend_interaction", 
                             "joke", "pleasantry", "current_events", "friendly_banter"],
                    "description": "Type of post to create. Use 'auto' to let AI choose based on context.",
                    "default": "auto"
                },
                "post_text": {
                    "type": "string",
                    "description": "Optional: Custom post text. If not provided, AI will generate one based on avatar's personality."
                }
            },
            "required": []
        }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        global intelligent_avatar
        
        post_type = kwargs.get('post_type', 'general')
        post_text = kwargs.get('post_text')
        
        # Initialize intelligent_avatar if not already initialized
        if intelligent_avatar is None:
            logger.info("🔄 intelligent_avatar is None, initializing now...")
            print("🔄 intelligent_avatar is None, initializing now...")
            await initialize_intelligent_avatar()
        
        # Generate post if not provided
        print(f"📝 Creating post: post_text provided={bool(post_text)}, intelligent_avatar={intelligent_avatar is not None}")
        if not post_text and intelligent_avatar:
            print(f"   Generating {post_type} post content...")
            
            # Use diverse post generation for more variety
            if post_type in ["auto", "friend_interaction", "joke", "pleasantry", "current_events", "friendly_banter"]:
                result = await intelligent_avatar.generate_diverse_post(
                    user_id=avatar_id,
                    post_type=post_type
                )
            else:
                # Use traditional post generation for basic types
                result = await intelligent_avatar.generate_avatar_post(
                    user_id=avatar_id,
                    post_type=post_type
                )
            
            print(f"   Generation result: {result}")
            
            if 'error' in result:
                return {"success": False, "error": result['error']}
            
            post_text = result.get('content', '')
            print(f"   Generated post_text length: {len(post_text) if post_text else 0}")
        
        if not post_text:
            return {"success": False, "error": "Failed to generate post content"}
        
        # Limit length
        if len(post_text) > 500:
            post_text = post_text[:497] + "..."
        
        # Create post
        post = {
            "id": f"post-{avatar_id}-{datetime.now(timezone.utc).timestamp()}",
            "user_id": avatar_id,
            "text": post_text,
            "content": post_text,
            "post_type": "avatar",
            "likes": 0,
            "liked_by": [],
            "comments": [],
            "comment_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await db.posts.insert_one(post)
        
        # Also add to user document
        post_for_user = {k: v for k, v in post.items() if k != '_id'}
        await db.users.update_one(
            {"id": avatar_id},
            {"$push": {"avatar_posts": post_for_user}}
        )
        
        # Log activity
        await self._log_activity(avatar_id, "post_created", {
            "post_id": post['id'],
            "world_mode": "avatar"
        })
        
        return {
            "success": True,
            "message": f"Created post",
            "post_id": post['id'],
            "post_text": post_text
        }
    
    async def _log_activity(self, avatar_id: str, activity_type: str, details: Dict):
        """Log avatar activity"""
        user = await db.users.find_one({"id": avatar_id})
        activity = {
            "bot_id": avatar_id,
            "user_id": avatar_id,
            "bot_name": user.get('avatar_name', user.get('name', 'Unknown')) if user else 'Unknown',
            "action_type": activity_type,
            "description": f"Created post in avatar world",
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.autonomous_activities.insert_one(activity)


class SendFriendRequestTool(AvatarMCPTool):
    """Tool for sending friend requests"""
    
    def __init__(self):
        super().__init__(
            name="send_friend_request",
            description="Send a friend request to another avatar",
            action_key="send_friend_requests"
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_user_id": {
                    "type": "string",
                    "description": "The ID of the user to send a friend request to"
                }
            },
            "required": ["target_user_id"]
        }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        target_user_id = kwargs.get('target_user_id')
        
        if avatar_id == target_user_id:
            return {"success": False, "error": "Cannot send friend request to yourself"}
        
        # Check if already friends
        friendship = await db.friendships.find_one({
            "$or": [
                {"user1_id": avatar_id, "user2_id": target_user_id},
                {"user1_id": target_user_id, "user2_id": avatar_id}
            ]
        })
        
        if friendship:
            return {"success": False, "error": "Already friends or request pending"}
        
        # Create friendship (auto-accept for now)
        friendship = {
            "user1_id": avatar_id,
            "user2_id": target_user_id,
            "status": "accepted",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.friendships.insert_one(friendship)
        
        # Log activity
        await self._log_activity(avatar_id, "friend_request_sent", {
            "target_user_id": target_user_id
        })
        
        return {
            "success": True,
            "message": f"Sent friend request to {target_user_id}",
            "target_user_id": target_user_id
        }
    
    async def _log_activity(self, avatar_id: str, activity_type: str, details: Dict):
        """Log avatar activity"""
        user = await db.users.find_one({"id": avatar_id})
        activity = {
            "bot_id": avatar_id,
            "user_id": avatar_id,
            "bot_name": user.get('avatar_name', user.get('name', 'Unknown')) if user else 'Unknown',
            "action_type": activity_type,
            "description": f"Sent friend request",
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.autonomous_activities.insert_one(activity)


class AcceptFriendRequestTool(AvatarMCPTool):
    """Tool for accepting friend requests"""
    
    def __init__(self):
        super().__init__(
            name="accept_friend_request",
            description="Accept an incoming friend request",
            action_key="accept_friend_requests"
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "friendship_id": {
                    "type": "string",
                    "description": "The ID of the friendship request to accept"
                }
            },
            "required": ["friendship_id"]
        }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        friendship_id = kwargs.get('friendship_id')
        
        # Find friendship
        friendship = await db.friendships.find_one({
            "$or": [
                {"user1_id": avatar_id, "user2_id": friendship_id},
                {"user1_id": friendship_id, "user2_id": avatar_id}
            ]
        })
        
        if not friendship:
            return {"success": False, "error": "Friendship request not found"}
        
        if friendship.get('status') == 'accepted':
            return {"success": False, "error": "Friendship already accepted"}
        
        # Accept friendship
        await db.friendships.update_one(
            {"_id": friendship['_id']},
            {"$set": {"status": "accepted"}}
        )
        
        return {
            "success": True,
            "message": f"Accepted friend request",
            "friendship_id": str(friendship['_id'])
        }


class MessageFriendTool(AvatarMCPTool):
    """Tool for messaging friends"""
    
    def __init__(self):
        super().__init__(
            name="message_friend",
            description="Send a message to a friend",
            action_key="message_friends"
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "friend_id": {
                    "type": "string",
                    "description": "The ID of the friend to message"
                },
                "message_text": {
                    "type": "string",
                    "description": "Optional: Custom message text. If not provided, AI will generate one based on conversation context."
                }
            },
            "required": ["friend_id"]
        }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        global intelligent_avatar
        
        friend_id = kwargs.get('friend_id')
        message_text = kwargs.get('message_text')
        
        # Verify friendship
        # Note: friendships use user_id/friend_id fields, not user1_id/user2_id
        friendship = await db.friendships.find_one({
            "$or": [
                {"user_id": avatar_id, "friend_id": friend_id, "status": "accepted"},
                {"user_id": friend_id, "friend_id": avatar_id, "status": "accepted"}
            ]
        })
        
        if not friendship:
            return {"success": False, "error": "Not friends with this user"}
        
        # Generate message if not provided
        # Initialize intelligent_avatar if not already initialized
        if intelligent_avatar is None:
            logger.info("🔄 intelligent_avatar is None for message, initializing now...")
            await initialize_intelligent_avatar()
        
        if not message_text and intelligent_avatar:
            # Get conversation history
            user_ids = sorted([avatar_id, friend_id])
            conversation = await db.agent_conversations.find_one({
                "agent1_user_id": user_ids[0],
                "agent2_user_id": user_ids[1]
            })
            
            conversation_history = []
            if conversation:
                for msg in conversation.get('messages', [])[-5:]:
                    conversation_history.append({
                        "sender_id": msg.get('sender'),
                        "content": msg.get('message', '')
                    })
            
            # Generate response
            logger.info(f"📤 Generating message from {avatar_id} to {friend_id}, conversation_history length: {len(conversation_history)}")
            result = await intelligent_avatar.generate_chat_response(
                user_id=avatar_id,
                other_user_id=friend_id,
                conversation_history=conversation_history,
                last_message=conversation_history[-1].get('content', '') if conversation_history else "Hello!"
            )
            logger.info(f"📥 Message generation result: {result}")
            
            if 'error' not in result:
                message_text = result.get('content', '').strip()
            else:
                logger.warning(f"⚠️ Message generation returned error: {result.get('error')}")
        
        if not message_text:
            logger.warning(f"⚠️ No message_text generated, intelligent_avatar={intelligent_avatar is not None}")
            return {"success": False, "error": "Failed to generate message"}
        
        # Create or update conversation
        user_ids = sorted([avatar_id, friend_id])
        conversation = await db.agent_conversations.find_one({
            "agent1_user_id": user_ids[0],
            "agent2_user_id": user_ids[1]
        })
        
        if not conversation:
            from bson import ObjectId
            conversation_id = str(ObjectId())
            await db.agent_conversations.insert_one({
                "id": conversation_id,
                "agent1_user_id": user_ids[0],
                "agent2_user_id": user_ids[1],
                "messages": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            conversation = await db.agent_conversations.find_one({
                "agent1_user_id": user_ids[0],
                "agent2_user_id": user_ids[1]
            })
        
        # Add message
        message_dict = {
            "sender": avatar_id,
            "message": message_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await db.agent_conversations.update_one(
            {"agent1_user_id": user_ids[0], "agent2_user_id": user_ids[1]},
            {
                "$push": {"messages": message_dict},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        return {
            "success": True,
            "message": f"Sent message to {friend_id}",
            "friend_id": friend_id,
            "message_text": message_text
        }


class DiscoverProfilesTool(AvatarMCPTool):
    """Tool for discovering profiles"""
    
    def __init__(self):
        super().__init__(
            name="discover_profiles",
            description="Discover and view other avatar profiles",
            action_key="discover_profiles"
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Number of profiles to discover",
                    "default": 5
                }
            },
            "required": []
        }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        limit = kwargs.get('limit', 5)
        
        # Get random avatars
        users = await db.users.find({
            "id": {"$ne": avatar_id},
            "$or": [
                {"is_bot": True},
                {"avatar_autonomous": True}
            ],
            "avatar_name": {"$exists": True}
        }).limit(limit).to_list(limit)
        
        profiles = []
        for user in users:
            profiles.append({
                "user_id": user['id'],
                "avatar_name": user.get('avatar_name', user.get('name', 'Unknown')),
                "avatar_bio": user.get('avatar_bio', ''),
                "avatar_picture": user.get('avatar_picture', '')
            })
        
        # Log activity
        await self._log_activity(avatar_id, "profile_viewed", {
            "profiles_discovered": len(profiles)
        })
        
        return {
            "success": True,
            "message": f"Discovered {len(profiles)} profiles",
            "profiles": profiles
        }
    
    async def _log_activity(self, avatar_id: str, activity_type: str, details: Dict):
        """Log avatar activity"""
        user = await db.users.find_one({"id": avatar_id})
        activity = {
            "bot_id": avatar_id,
            "user_id": avatar_id,
            "bot_name": user.get('avatar_name', user.get('name', 'Unknown')) if user else 'Unknown',
            "action_type": activity_type,
            "description": f"Viewed profiles",
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.autonomous_activities.insert_one(activity)


class SharePostTool(AvatarMCPTool):
    """Tool for sharing posts (not yet implemented)"""
    
    def __init__(self):
        super().__init__(
            name="share_post",
            description="Share a post (coming soon)",
            action_key="share_posts"
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "The ID of the post to share"
                }
            },
            "required": ["post_id"]
        }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        return {
            "success": False,
            "error": "Share post feature is not yet implemented"
        }


class ReadMessagesTool(AvatarMCPTool):
    """Tool for reading/marking messages as read"""
    
    def __init__(self):
        super().__init__(
            name="read_messages",
            description="Read and mark messages as read",
            action_key="read_messages"
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "Optional: Specific conversation ID to mark as read. If not provided, marks all unread messages as read."
                }
            },
            "required": []
        }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """Mark messages as read"""
        try:
            conversation_id = kwargs.get("conversation_id")
            messages_marked = 0
            
            # Mark messages as read in direct_messages collection (real world)
            if conversation_id:
                # Mark specific conversation
                result = await db.direct_messages.update_many(
                    {
                        "$or": [
                            {"user1_id": avatar_id},
                            {"user2_id": avatar_id}
                        ],
                        "conversation_id": conversation_id
                    },
                    {
                        "$set": {
                            "messages.$[elem].read": True
                        }
                    },
                    array_filters=[{"elem.sender_id": {"$ne": avatar_id}, "elem.read": False}]
                )
                messages_marked += result.modified_count
            else:
                # Mark all unread messages
                conversations = await db.direct_messages.find({
                    "$or": [
                        {"user1_id": avatar_id},
                        {"user2_id": avatar_id}
                    ]
                }).to_list(100)
                
                for conv in conversations:
                    messages = conv.get('messages', [])
                    updated = False
                    for msg in messages:
                        if msg.get('read', True) == False and msg.get('sender_id') != avatar_id:
                            msg['read'] = True
                            updated = True
                            messages_marked += 1
                    
                    if updated:
                        await db.direct_messages.update_one(
                            {"_id": conv["_id"]},
                            {"$set": {"messages": messages}}
                        )
            
            # Mark messages as read in agent_conversations collection (avatar world)
            if conversation_id:
                result = await db.agent_conversations.update_many(
                    {
                        "$or": [
                            {"agent1_user_id": avatar_id},
                            {"agent2_user_id": avatar_id}
                        ],
                        "id": conversation_id
                    },
                    {
                        "$set": {
                            "messages.$[elem].read": True
                        }
                    },
                    array_filters=[{"elem.sender": {"$ne": avatar_id}, "elem.read": {"$ne": True}}]
                )
                messages_marked += result.modified_count
            else:
                # Mark all unread messages in agent conversations
                conversations = await db.agent_conversations.find({
                    "$or": [
                        {"agent1_user_id": avatar_id},
                        {"agent2_user_id": avatar_id}
                    ]
                }).to_list(100)
                
                for conv in conversations:
                    messages = conv.get('messages', [])
                    updated = False
                    for msg in messages:
                        if msg.get('read', True) == False and msg.get('sender') != avatar_id:
                            msg['read'] = True
                            updated = True
                            messages_marked += 1
                    
                    if updated:
                        await db.agent_conversations.update_one(
                            {"_id": conv["_id"]},
                            {"$set": {"messages": messages}}
                        )
            
            return {
                "success": True,
                "messages_marked": messages_marked,
                "message": f"Marked {messages_marked} message(s) as read"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error marking messages as read: {str(e)}"
            }


class GetFriendActivitiesTool(AvatarMCPTool):
    """Tool for getting recent friend activities (state-aware: high friend_focus)"""
    
    def __init__(self):
        super().__init__(
            name="get_friend_activities",
            description="Get recent activities from your friends (posts, interactions). Use when you want to know what friends are up to.",
            action_key="get_friend_activities"  # New permission
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hours_back": {
                    "type": "number",
                    "description": "How many hours back to look for activities (default: 24)",
                    "default": 24
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of activities to return (default: 10)",
                    "default": 10
                }
            },
            "required": []
        }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """Get recent friend activities"""
        from services.friend_activity_service import FriendActivityService
        
        hours_back = kwargs.get('hours_back', 24)
        limit = kwargs.get('limit', 10)
        
        service = FriendActivityService(db)
        activities = await service.get_recent_friend_activities(avatar_id, hours=hours_back)
        
        # Limit results
        activities = activities[:limit]
        
        # Format for readability
        formatted_activities = []
        for activity in activities:
            formatted_activities.append({
                "friend_name": activity.get("friend_name"),
                "type": activity.get("type"),
                "summary": activity.get("summary"),
                "post_id": activity.get("post_id"),
                "content_preview": activity.get("content", "")[:150],
                "likes": activity.get("likes", 0),
                "comments": activity.get("comments", 0),
                "is_popular": activity.get("is_popular", False)
            })
        
        return {
            "success": True,
            "activities": formatted_activities,
            "count": len(formatted_activities),
            "message": f"Found {len(formatted_activities)} recent friend activities"
        }


class GetTrendingTopicsTool(AvatarMCPTool):
    """Tool for getting trending topics/news (state-aware: high world_awareness)"""
    
    def __init__(self):
        super().__init__(
            name="get_trending_topics",
            description="Get trending topics and news relevant to your interests. Use when you want to know what's happening in the world.",
            action_key="get_trending_topics"  # New permission
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["general", "technology", "entertainment", "business", "science"],
                    "description": "Category of topics to fetch",
                    "default": "general"
                },
                "include_news_for_interests": {
                    "type": "boolean",
                    "description": "Whether to include news matching your personal interests",
                    "default": True
                }
            },
            "required": []
        }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """Get trending topics and news"""
        from services.content_awareness_service import ContentAwarenessService
        
        category = kwargs.get('category', 'general')
        include_interests = kwargs.get('include_news_for_interests', True)
        
        service = ContentAwarenessService()
        
        # Get trending topics
        trending = await service.get_trending_topics(category)
        
        # Get news for interests if requested
        interest_news = []
        if include_interests:
            user = await db.users.find_one({"id": avatar_id})
            if user:
                interests = user.get('avatar_character_profile', {}).get('interests', [])
                if interests:
                    interest_news = await service.get_news_for_interests(interests)
        
        return {
            "success": True,
            "trending_topics": trending[:5],
            "interest_news": interest_news[:3],
            "total_items": len(trending) + len(interest_news),
            "message": f"Found {len(trending)} trending topics and {len(interest_news)} news items matching your interests"
        }


class BrowseFeedTool(AvatarMCPTool):
    """Tool for browsing the feed to discover new content"""

    def __init__(self):
        super().__init__(
            name="browse_feed",
            description="Browse the feed to discover new posts and content from friends and the network",
            action_key="browse_feed"
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of posts to fetch (default: 20)",
                    "default": 20
                },
                "post_type": {
                    "type": "string",
                    "description": "Type of posts to browse (default: 'all')",
                    "enum": ["all", "avatar", "user"],
                    "default": "all"
                }
            },
            "required": []
        }

    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """
        Browse the feed - fetch recent posts from friends and network
        
        This action:
        1. Fetches recent posts from friends
        2. Fetches trending posts from the network
        3. Updates the avatar's perception of the feed
        """
        from datetime import datetime, timezone, timedelta
        
        limit = kwargs.get("limit", 20)
        post_type = kwargs.get("post_type", "all")
        
        try:
            # Get avatar's friends
            from services.friend_service import FriendService
            friend_service = FriendService(db)
            friends = await friend_service.get_friends(avatar_id)
            friend_ids = [f['id'] for f in friends]
            
            # Build query
            query = {}
            if post_type == "avatar":
                query["post_type"] = "avatar"
            elif post_type == "user":
                query["post_type"] = {"$ne": "avatar"}
            
            # Get recent posts (last 7 days)
            since_time = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Fetch posts from friends first
            friend_posts = []
            if friend_ids:
                friend_query = {**query, "user_id": {"$in": friend_ids}}
                friend_posts_cursor = db.posts.find(friend_query).sort("created_at", -1).limit(limit)
                friend_posts = await friend_posts_cursor.to_list(limit)
            
            # Fetch trending posts from network (not from friends)
            network_limit = max(5, limit - len(friend_posts))
            network_query = {**query}
            if friend_ids:
                network_query["user_id"] = {"$nin": friend_ids}
            
            network_posts_cursor = db.posts.find(network_query).sort("created_at", -1).limit(network_limit)
            network_posts = await network_posts_cursor.to_list(network_limit)
            
            # Combine and sort by created_at
            all_posts = friend_posts + network_posts
            all_posts.sort(key=lambda p: p.get('created_at', ''), reverse=True)
            all_posts = all_posts[:limit]
            
            # Format posts for response
            posts_data = []
            for post in all_posts:
                posts_data.append({
                    "id": post.get("id"),
                    "user_id": post.get("user_id"),
                    "content": post.get("content", "")[:200],  # Truncate for response
                    "post_type": post.get("post_type", "general"),
                    "created_at": post.get("created_at"),
                    "likes": post.get("likes", 0),
                    "comment_count": post.get("comment_count", 0)
                })
            
            return {
                "success": True,
                "message": f"Feed browsed - found {len(posts_data)} posts",
                "posts": posts_data,
                "friend_posts_count": len(friend_posts),
                "network_posts_count": len(network_posts)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error browsing feed: {str(e)}"
            }


class AvatarMCPServer:
    """MCP Server for Avatar Actions"""
    
    def __init__(self):
        self.tools: Dict[str, AvatarMCPTool] = {}
        self._register_tools()
    
    def _register_tools(self):
        """Register all available tools"""
        self.tools = {
            "like_post": LikePostTool(),
            "comment_on_post": CommentOnPostTool(),
            "create_post": CreatePostTool(),
            "send_friend_request": SendFriendRequestTool(),
            "accept_friend_request": AcceptFriendRequestTool(),
            "message_friend": MessageFriendTool(),
            "discover_profiles": DiscoverProfilesTool(),
            "share_post": SharePostTool(),
            "read_messages": ReadMessagesTool(),
            "browse_feed": BrowseFeedTool(),
            "get_friend_activities": GetFriendActivitiesTool(),  # NEW: State-aware
            "get_trending_topics": GetTrendingTopicsTool()  # NEW: State-aware
        }
    
    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Get list of all available tools"""
        return [tool.get_tool_schema() for tool in self.tools.values()]
    
    async def call_tool(self, tool_name: str, avatar_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool for a specific avatar"""
        print(f"🔧 MCP call_tool: tool_name={tool_name}, avatar_id={avatar_id}, avatar_id_len={len(avatar_id) if avatar_id else 0}")
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }
        
        tool = self.tools[tool_name]
        return await tool.execute(avatar_id, **arguments)
    
    async def get_available_tools_for_avatar(self, avatar_id: str) -> List[Dict[str, Any]]:
        """Get list of tools available for a specific avatar based on permissions"""
        available_tools = []
        
        for tool in self.tools.values():
            if await tool.check_permission(avatar_id):
                available_tools.append(tool.get_tool_schema())
        
        return available_tools


# Global server instance
mcp_server = AvatarMCPServer()


async def initialize_intelligent_avatar():
    """Initialize IntelligentAvatar for the MCP server"""
    global intelligent_avatar
    
    try:
        from domain.graph.rag import GraphRAG
        from core.config import get_openai_client, OPENAI_MODEL
        
        openai_client = get_openai_client()
        if not openai_client:
            logger.warning("⚠️ OpenAI client not available - intelligent_avatar will not be initialized")
            print("⚠️ OpenAI client not available - intelligent_avatar will not be initialized")
            intelligent_avatar = None
            return
        
        model_name = OPENAI_MODEL  # OPENAI_MODEL has a default in config.py
        graph_rag = GraphRAG(db)
        intelligent_avatar = IntelligentAvatar(db, openai_client, model_name, graph_rag)
        logger.info(f"✅ IntelligentAvatar initialized for MCP server with model: {model_name}")
        print(f"✅ IntelligentAvatar initialized for MCP server with model: {model_name}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize IntelligentAvatar: {e}", exc_info=True)
        print(f"❌ Failed to initialize IntelligentAvatar: {e}")
        intelligent_avatar = None


# Initialize on import (only if event loop is running)
# Otherwise, will be initialized when MCP server is accessed
try:
    loop = asyncio.get_running_loop()
    asyncio.create_task(initialize_intelligent_avatar())
except RuntimeError:
    # No event loop running, will initialize later
    pass


if __name__ == "__main__":
    """Run MCP server in stdio mode"""
    import sys
    
    async def main():
        await initialize_intelligent_avatar()
        
        # Simple stdio-based MCP server
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                request = json.loads(line.strip())
                
                if request.get('method') == 'tools/list':
                    tools = mcp_server.get_tools_list()
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get('id'),
                        "result": {"tools": tools}
                    }
                
                elif request.get('method') == 'tools/call':
                    tool_name = request['params']['name']
                    avatar_id = request['params'].get('avatar_id')
                    arguments = request['params'].get('arguments', {})
                    
                    if not avatar_id:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request.get('id'),
                            "error": {"code": -32602, "message": "avatar_id is required"}
                        }
                    else:
                        result = await mcp_server.call_tool(tool_name, avatar_id, arguments)
                        response = {
                            "jsonrpc": "2.0",
                            "id": request.get('id'),
                            "result": result
                        }
                
                elif request.get('method') == 'tools/available':
                    avatar_id = request['params'].get('avatar_id')
                    if not avatar_id:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request.get('id'),
                            "error": {"code": -32602, "message": "avatar_id is required"}
                        }
                    else:
                        tools = await mcp_server.get_available_tools_for_avatar(avatar_id)
                        response = {
                            "jsonrpc": "2.0",
                            "id": request.get('id'),
                            "result": {"tools": tools}
                        }
                
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get('id'),
                        "error": {"code": -32601, "message": "Method not found"}
                    }
                
                print(json.dumps(response))
                sys.stdout.flush()
            
            except json.JSONDecodeError:
                continue
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get('id') if 'request' in locals() else None,
                    "error": {"code": -32603, "message": str(e)}
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
    
    asyncio.run(main())

