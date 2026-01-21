"""
Friend Activity Service
Tracks and surfaces friend activities for avatars to comment on and interact with
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class FriendActivityService:
    """Tracks friend activities for social awareness"""
    
    def __init__(self, db):
        self.db = db
    
    async def get_recent_friend_activities(self, user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent activities from friends:
        - Posts they made
        - Comments/interactions
        - Profile updates
        
        Args:
            user_id: Avatar's user ID
            hours: How many hours back to look (default 24)
            
        Returns:
            List of friend activities with context
        """
        try:
            # Get friends
            friend_ids = await self._get_friend_ids(user_id)
            
            if not friend_ids:
                return []
            
            # Get recent posts from friends
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            posts = await self.db.posts.find({
                "user_id": {"$in": friend_ids},
                "created_at": {"$gte": cutoff_time.isoformat()}
            }).sort("created_at", -1).limit(10).to_list(None)
            
            activities = []
            
            for post in posts:
                # Get friend info
                friend = await self.db.users.find_one({"id": post.get("user_id")})
                if not friend:
                    continue
                
                friend_name = friend.get("avatar_name") or friend.get("display_name") or friend.get("name", "Friend")
                
                # Count engagement
                likes_count = len(post.get("likes", []))
                comments_count = len(post.get("comments", []))
                
                activities.append({
                    "type": "post",
                    "friend_id": post.get("user_id"),
                    "friend_name": friend_name,
                    "post_id": post.get("id"),
                    "content": post.get("text", post.get("content", "")),
                    "summary": f"Posted: {post.get('text', post.get('content', ''))[:100]}...",
                    "likes": likes_count,
                    "comments": comments_count,
                    "created_at": post.get("created_at"),
                    "is_popular": likes_count > 3 or comments_count > 2
                })
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting friend activities: {e}", exc_info=True)
            return []
    
    async def get_commentable_moments(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get specific moments worth commenting on:
        - Friend got lots of likes (popular post)
        - Friend posted something unusual/funny
        - Friend hasn't posted in a while (can check in)
        - Recent interesting conversations
        
        Returns:
            List of commentable moments with context
        """
        try:
            activities = await self.get_recent_friend_activities(user_id, hours=48)
            
            commentable = []
            
            for activity in activities:
                # Popular posts (good engagement)
                if activity.get("is_popular"):
                    commentable.append({
                        **activity,
                        "reason": "popular_post",
                        "suggestion": f"React to {activity['friend_name']}'s popular post"
                    })
                
                # Recent posts (last 6 hours) - good for quick reactions
                try:
                    post_time = datetime.fromisoformat(activity.get("created_at").replace("Z", "+00:00"))
                    hours_ago = (datetime.now(timezone.utc) - post_time).total_seconds() / 3600
                    
                    if hours_ago < 6:
                        commentable.append({
                            **activity,
                            "reason": "recent_post",
                            "suggestion": f"React to {activity['friend_name']}'s recent post"
                        })
                except:
                    pass
            
            return commentable[:5]  # Top 5 commentable moments
            
        except Exception as e:
            logger.error(f"Error getting commentable moments: {e}", exc_info=True)
            return []
    
    async def suggest_friend_to_interact_with(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Suggest a friend to tease/appreciate/chat with
        
        Returns:
            Friend info with interaction suggestions
        """
        try:
            friend_ids = await self._get_friend_ids(user_id)
            
            if not friend_ids:
                return None
            
            # Get friends with their recent activity
            friends_with_activity = []
            
            for friend_id in friend_ids:
                friend = await self.db.users.find_one({"id": friend_id})
                if not friend:
                    continue
                
                # Get their recent posts
                recent_posts = await self.db.posts.find({
                    "user_id": friend_id
                }).sort("created_at", -1).limit(3).to_list(None)
                
                friend_name = friend.get("avatar_name") or friend.get("display_name") or friend.get("name", "Friend")
                
                friends_with_activity.append({
                    "friend_id": friend_id,
                    "friend_name": friend_name,
                    "recent_posts": recent_posts,
                    "post_count": len(recent_posts),
                    "archetype": friend.get("avatar_archetype", "casual_observer")
                })
            
            # Pick a friend (prefer those who post frequently)
            if friends_with_activity:
                # Sort by post count, pick one
                friends_with_activity.sort(key=lambda x: x["post_count"], reverse=True)
                return friends_with_activity[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error suggesting friend interaction: {e}", exc_info=True)
            return None
    
    async def _get_friend_ids(self, user_id: str) -> List[str]:
        """Get list of friend IDs for a user"""
        try:
            friendships = await self.db.friendships.find({
                "$or": [
                    {"user_id": user_id, "status": "accepted"},
                    {"friend_id": user_id, "status": "accepted"}
                ]
            }).to_list(None)
            
            friend_ids = []
            for friendship in friendships:
                if friendship.get("user_id") == user_id:
                    friend_ids.append(friendship.get("friend_id"))
                else:
                    friend_ids.append(friendship.get("user_id"))
            
            return friend_ids
            
        except Exception as e:
            logger.error(f"Error getting friend IDs: {e}", exc_info=True)
            return []
