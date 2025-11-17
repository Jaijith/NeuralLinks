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
        if user_id == friend_id:
            return {"success": False, "error": "Cannot send friend request to yourself"}
        
        # Check if friendship already exists
        existing = await self.db.friendships.find_one({
            "$or": [
                {"user_id": user_id, "friend_id": friend_id},
                {"user_id": friend_id, "friend_id": user_id}
            ]
        })
        
        if existing:
            return {"success": False, "error": "Friendship already exists or request pending"}
        
        # Create friendship request
        friendship = {
            "user_id": user_id,
            "friend_id": friend_id,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.friendships.insert_one(friendship)
        
        return {"success": True, "message": "Friend request sent", "friendship": friendship}
    
    async def accept_friend_request(self, friendship_id: str, user_id: str) -> Dict[str, Any]:
        """Accept a friend request"""
        friendship = await self.db.friendships.find_one({
            "$or": [
                {"user_id": friendship_id, "friend_id": user_id},
                {"user_id": user_id, "friend_id": friendship_id}
            ]
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
        for f in friendships:
            if f['user_id'] == user_id:
                friend_ids.append(f['friend_id'])
            else:
                friend_ids.append(f['user_id'])
        
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
                "is_bot": 1
            }
        ).to_list(1000)
        
        # Sort by name for consistency
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

