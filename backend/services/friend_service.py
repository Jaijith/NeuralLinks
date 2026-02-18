"""
Friend Service
Handles friend requests and friendships
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


class FriendService:
    """Service for friend operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def send_friend_request(self, user_id: str, friend_id: str) -> Dict[str, Any]:
        """Send a friend request"""
        logger.info(f"send_friend_request called: user_id={user_id}, friend_id={friend_id}")
        
        if not user_id or not friend_id:
            logger.error(f"Invalid user_id or friend_id: user_id={user_id}, friend_id={friend_id}")
            return {"success": False, "error": "Invalid user ID or friend ID"}
        
        if user_id == friend_id:
            logger.warning(f"User tried to send friend request to themselves: {user_id}")
            return {"success": False, "error": "Cannot send friend request to yourself"}
        
        # Verify both users exist
        user_exists = await self.db.users.find_one({"id": user_id})
        friend_exists = await self.db.users.find_one({"id": friend_id})
        
        if not user_exists:
            logger.error(f"User not found: {user_id}")
            return {"success": False, "error": "User not found"}
        
        if not friend_exists:
            logger.error(f"Friend not found: {friend_id}")
            return {"success": False, "error": "User not found"}
        
        # Check if friendship already exists
        existing = await self.db.friendships.find_one({
            "$or": [
                {"user_id": user_id, "friend_id": friend_id},
                {"user_id": friend_id, "friend_id": user_id}
            ]
        })
        
        if existing:
            logger.info(f"Friendship already exists: user_id={user_id}, friend_id={friend_id}, status={existing.get('status')}")
            return {"success": False, "error": "Friendship already exists or request pending"}
        
        # Create friendship request
        friendship = {
            "user_id": user_id,
            "friend_id": friend_id,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            result = await self.db.friendships.insert_one(friendship)
            logger.info(f"Friend request created successfully: {result.inserted_id}")
            
            # Convert friendship to JSON-serializable format (remove _id or convert to string)
            friendship_response = {
                "user_id": friendship["user_id"],
                "friend_id": friendship["friend_id"],
                "status": friendship["status"],
                "created_at": friendship["created_at"]
            }
            
            return {"success": True, "message": "Friend request sent", "friendship": friendship_response}
        except Exception as e:
            logger.error(f"Error creating friend request: {str(e)}")
            return {"success": False, "error": f"Failed to create friend request: {str(e)}"}
    
    async def accept_friend_request(self, friendship_id: str, user_id: str) -> Dict[str, Any]:
        """Accept a friend request"""
        from bson import ObjectId
        
        # First try to find by MongoDB _id
        friendship = None
        try:
            friendship = await self.db.friendships.find_one({
                "_id": ObjectId(friendship_id),
                "friend_id": user_id,  # Ensure current user is the recipient
                "status": "pending"
            })
        except Exception:
            pass
        
        # Fallback: try finding by user_id/friend_id (for backwards compatibility)
        if not friendship:
            friendship = await self.db.friendships.find_one({
                "$or": [
                    {"user_id": friendship_id, "friend_id": user_id},
                    {"user_id": user_id, "friend_id": friendship_id}
                ],
                "status": "pending"
            })
        
        if not friendship:
            return {"success": False, "error": "Friend request not found"}
        
        if friendship.get('status') == 'accepted':
            return {"success": False, "error": "Friendship already accepted"}
        
        # Accept friendship
        await self.db.friendships.update_one(
            {"_id": friendship['_id']},
            {"$set": {"status": "accepted", "accepted_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"success": True, "message": "Friend request accepted"}
    
    async def decline_friend_request(self, friendship_id: str, user_id: str) -> Dict[str, Any]:
        """Decline a friend request"""
        from bson import ObjectId
        
        # First try to delete by MongoDB _id
        result = None
        try:
            result = await self.db.friendships.delete_one({
                "_id": ObjectId(friendship_id),
                "friend_id": user_id,  # Ensure current user is the recipient
                "status": "pending"
            })
        except Exception:
            pass
        
        # Fallback if not found or invalid ObjectId
        if not result or result.deleted_count == 0:
            result = await self.db.friendships.delete_one({
                "$or": [
                    {"user_id": friendship_id, "friend_id": user_id},
                    {"user_id": user_id, "friend_id": friendship_id}
                ],
                "status": "pending"
            })
        
        if result.deleted_count == 0:
            return {"success": False, "error": "Friend request not found"}
        
        return {"success": True, "message": "Friend request declined"}
    
    async def get_friends(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's friends list - returns all accepted friendships"""
        friendships = await self.db.friendships.find({
            "$or": [
                {"user_id": user_id, "status": "accepted"},
                {"friend_id": user_id, "status": "accepted"}
            ]
        }).to_list(1000)
        
        friend_ids = []
        friend_type_map = {}
        for f in friendships:
            if f['user_id'] == user_id:
                fid = f['friend_id']
            else:
                fid = f['user_id']
            friend_ids.append(fid)
            friend_type_map[fid] = f.get('friend_type', 'human')
        
        if not friend_ids:
            return []
        
        # Get friend user documents with all necessary fields
        friends = await self.db.users.find(
            {"id": {"$in": friend_ids}},
            {
                "_id": 0, 
                "id": 1, 
                "name": 1, 
                "picture": 1, 
                "avatar_name": 1, 
                "avatar_picture": 1,
                "avatar_bio": 1,
                "bio": 1,
                "avatar_location": 1,
                "location": 1,
                "avatar_interests": 1,
                "interests": 1,
                "avatar_job_title": 1,
                "job_title": 1,
                "age": 1,
                "is_bot": 1,
                "is_ai_agent": 1,
                "agent_domain": 1,
                "agent_domain_label": 1,
                "agent_expertise": 1,
            }
        ).to_list(1000)
        
        # Attach friend_type from friendship document
        for friend in friends:
            friend["friend_type"] = friend_type_map.get(friend["id"], "human")
        
        # Sort alphabetically by name (frontend handles recency-based ordering)
        friends.sort(key=lambda x: (x.get('avatar_name') or x.get('name') or '').lower())
        
        return friends
    
    async def get_friend_requests(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending friend requests for user"""
        requests = await self.db.friendships.find({
            "friend_id": user_id,
            "status": "pending"
        }).to_list(100)
        
        requester_ids = [r['user_id'] for r in requests]
        
        if not requester_ids:
            return []
        
        # Get requester user documents
        requesters = await self.db.users.find(
            {"id": {"$in": requester_ids}},
            {"_id": 0, "id": 1, "name": 1, "picture": 1, "avatar_name": 1, "avatar_picture": 1}
        ).to_list(100)
        
        # Combine with friendship info
        result = []
        for req in requests:
            requester = next((r for r in requesters if r['id'] == req['user_id']), None)
            if requester:
                result.append({
                    "friendship_id": str(req['_id']),
                    "requester": requester,
                    "created_at": req.get('created_at')
                })
        
        return result
    
    async def get_friendship_status(self, user_id: str, other_user_id: str) -> str:
        """Get friendship status between two users"""
        friendship = await self.db.friendships.find_one({
            "$or": [
                {"user_id": user_id, "friend_id": other_user_id},
                {"user_id": other_user_id, "friend_id": user_id}
            ]
        })
        
        if not friendship:
            return "none"
        
        return friendship.get('status', 'none')
    
    async def remove_friend(self, user_id: str, friend_id: str) -> Dict[str, Any]:
        """Remove a friend"""
        result = await self.db.friendships.delete_one({
            "$or": [
                {"user_id": user_id, "friend_id": friend_id},
                {"user_id": friend_id, "friend_id": user_id}
            ]
        })
        
        if result.deleted_count == 0:
            return {"success": False, "error": "Friendship not found"}
        
        return {"success": True, "message": "Friend removed"}

