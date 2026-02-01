"""
Social Context Service for Voice
Fetches and formats social context for the voice agent to feel alive
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import asyncio
import logging

logger = logging.getLogger(__name__)


class SocialContextService:
    """
    Fetches social context for voice conversations.
    
    Provides comprehensive context so the avatar can naturally talk about:
    - Its recent activities (posts, likes, comments)
    - Its friends and their activities
    - Ongoing conversations
    - Social happenings in its network
    
    Design principles:
    - Tier 1 (session start): Comprehensive enough for most conversations
    - Tier 2 (on-demand): Specific details when AI calls for them
    - Parallel queries: All fetches run concurrently
    - Graceful degradation: Missing data doesn't break the conversation
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._friends_cache: Dict[str, List[Dict]] = {}  # Cache friends within request
    
    async def get_tier1_context(self, avatar_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive Tier 1 context at session start.
        
        This should be enough for most casual conversations without
        needing additional function calls.
        
        Returns formatted context ready to inject into the voice prompt.
        """
        try:
            # Clear cache at start of new request
            self._friends_cache = {}
            
            # FAST PATH: Run all independent queries in parallel
            # Don't wait for friends first - fetch everything at once
            results = await asyncio.gather(
                self._get_my_posts_with_engagement(avatar_id, limit=2),
                self._get_conversation_summaries_optimized(avatar_id, limit=2),
                self._get_friends_quick(avatar_id, limit=8),  # Lightweight friends fetch
                return_exceptions=True
            )
            
            # Unpack results
            my_posts = results[0] if not isinstance(results[0], Exception) else []
            conversations = results[1] if not isinstance(results[1], Exception) else []
            friends = results[2] if not isinstance(results[2], Exception) else []
            
            # Format into natural language context
            context = self._format_tier1_context_fast(
                my_posts=my_posts,
                friends=friends,
                conversations=conversations
            )
            
            return {
                "formatted_context": context,
                "raw_data": {
                    "my_posts": my_posts,
                    "friends": friends,
                    "conversations": conversations
                },
                "fetch_time": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching Tier 1 context: {e}")
            return {
                "formatted_context": "",
                "raw_data": {},
                "fetch_time": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def _get_friends_quick(self, avatar_id: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Get friend names quickly without full user lookup"""
        try:
            # Get accepted friendships with limited fields
            friendships = await self.db.friendships.find(
                {
                    "$or": [
                        {"user_id": avatar_id, "status": "accepted"},
                        {"friend_id": avatar_id, "status": "accepted"}
                    ]
                },
                {"user_id": 1, "friend_id": 1}  # Only fetch needed fields
            ).limit(limit).to_list(limit)
            
            friend_ids = []
            for f in friendships:
                if f.get("user_id") == avatar_id:
                    friend_ids.append(f.get("friend_id"))
                else:
                    friend_ids.append(f.get("user_id"))
            
            if not friend_ids:
                return []
            
            # Get only names from users (minimal projection)
            friends = await self.db.users.find(
                {"id": {"$in": friend_ids}},
                {"id": 1, "avatar_name": 1, "display_name": 1, "name": 1}  # Minimal fields
            ).to_list(len(friend_ids))
            
            return [
                {
                    "id": f.get("id"),
                    "name": f.get("avatar_name") or f.get("display_name") or f.get("name", "Friend")
                }
                for f in friends
            ]
            
        except Exception as e:
            logger.error(f"Error in quick friends fetch: {e}")
            return []
    
    def _format_tier1_context_fast(
        self,
        my_posts: List[Dict],
        friends: List[Dict],
        conversations: List[Dict]
    ) -> str:
        """Format minimal Tier 1 context for fast loading"""
        sections = []
        
        # My posts and engagement
        if my_posts:
            post_lines = []
            for post in my_posts[:2]:
                content = post.get("content", "something")[:50]
                likes = post.get("likes", 0)
                comments = post.get("comments", 0)
                line = f"- \"{content}...\""
                if likes > 0 or comments > 0:
                    line += f" ({likes} likes, {comments} comments)"
                post_lines.append(line)
            if post_lines:
                sections.append("### My Recent Posts\n" + "\n".join(post_lines))
        
        # Friends (just names)
        if friends:
            friend_names = [f.get("name") for f in friends[:8]]
            sections.append(f"### My Friends\n{', '.join(friend_names)}")
        
        # Conversations
        if conversations:
            conv_lines = []
            for conv in conversations[:2]:
                with_name = conv.get("with", "someone")
                summary = conv.get("summary", "")[:40] or conv.get("last_message", "")[:40]
                if summary:
                    conv_lines.append(f"- With {with_name}: {summary}...")
                else:
                    conv_lines.append(f"- Talking with {with_name}")
            if conv_lines:
                sections.append("### Recent Conversations\n" + "\n".join(conv_lines))
        
        if sections:
            return "## Your Social Life Right Now\n\n" + "\n\n".join(sections)
        else:
            return ""
    
    async def get_specific_context(
        self, 
        avatar_id: str, 
        context_type: str,
        friend_name: Optional[str] = None,
        time_range: str = "recent"
    ) -> Dict[str, Any]:
        """
        Get specific context on-demand (Tier 2).
        Called when AI needs more details than Tier 1 provides.
        
        Args:
            avatar_id: The avatar's ID
            context_type: Type of context to fetch:
                - "my_activities" - Detailed activity history
                - "my_posts" - Detailed post engagement
                - "friends" - Full friends list with details
                - "friend_activity" - What friends are doing
                - "conversations" - Conversation details
                - "specific_friend" - Details about a specific friend
                - "specific_conversation" - Specific conversation history
            friend_name: Optional friend name for specific queries
            time_range: "today", "yesterday", "this_week", "recent"
        """
        try:
            time_filter = self._get_time_filter(time_range)
            
            if context_type == "my_activities":
                data = await self._get_my_recent_activities(avatar_id, limit=10, since=time_filter)
                return self._format_activity_response(data)
                
            elif context_type == "my_posts":
                data = await self._get_my_posts_with_engagement(avatar_id, limit=5, since=time_filter)
                return self._format_posts_response(data)
                
            elif context_type == "friends":
                data = await self._get_friends_summary(avatar_id, limit=20)
                return self._format_friends_response(data)
                
            elif context_type == "friend_activity":
                data = await self._get_friend_activity_summary(avatar_id, limit=10, since=time_filter)
                return self._format_friend_activity_response(data)
                
            elif context_type == "conversations":
                data = await self._get_conversation_summaries(avatar_id, limit=5)
                return self._format_conversations_response(data)
                
            elif context_type == "specific_friend" and friend_name:
                data = await self._get_specific_friend_details(avatar_id, friend_name)
                return self._format_specific_friend_response(data, friend_name)
                
            elif context_type == "specific_conversation" and friend_name:
                data = await self._get_specific_conversation(avatar_id, friend_name)
                return self._format_specific_conversation_response(data, friend_name)
                
            else:
                return {"summary": "I'm not sure what you're asking about.", "data": None}
                
        except Exception as e:
            logger.error(f"Error fetching specific context: {e}")
            return {"summary": "I'm having trouble remembering right now.", "data": None, "error": str(e)}
    
    # ===== Data Fetching Methods =====
    
    async def _get_my_recent_activities(
        self, 
        avatar_id: str, 
        limit: int = 5,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get avatar's recent activities"""
        try:
            query = {"bot_id": avatar_id}
            if since:
                query["timestamp"] = {"$gte": since.isoformat()}
            
            activities = await self.db.autonomous_activities.find(query)\
                .sort("timestamp", -1)\
                .limit(limit)\
                .to_list(limit)
            
            formatted = []
            for act in activities:
                formatted.append({
                    "type": act.get("action_type", act.get("activity_type", "activity")),
                    "description": act.get("description", ""),
                    "timestamp": act.get("timestamp"),
                    "target": act.get("target_user_id")
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error fetching activities: {e}")
            return []
    
    async def _get_my_posts_with_engagement(
        self, 
        avatar_id: str, 
        limit: int = 3,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get avatar's recent posts with engagement stats"""
        try:
            query = {"user_id": avatar_id}
            if since:
                query["created_at"] = {"$gte": since.isoformat()}
            
            posts = await self.db.posts.find(query)\
                .sort("created_at", -1)\
                .limit(limit)\
                .to_list(limit)
            
            formatted = []
            for post in posts:
                # Get commenter names
                comments = post.get("comments", [])
                commenter_names = []
                for c in comments[:3]:  # First 3 commenters
                    name = c.get("user_name")
                    if name:
                        commenter_names.append(name)
                
                # Get liker names (if available)
                liked_by = post.get("liked_by", [])
                liker_count = len(liked_by) if isinstance(liked_by, list) else post.get("likes", 0)
                
                formatted.append({
                    "content": (post.get("text") or post.get("content", ""))[:100],
                    "timestamp": post.get("created_at"),
                    "likes": liker_count,
                    "comments": len(comments),
                    "commenter_names": commenter_names,
                    "has_image": bool(post.get("image_url"))
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error fetching posts: {e}")
            return []
    
    async def _get_friends_summary(self, avatar_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get summary of avatar's friends"""
        try:
            # Get accepted friendships
            friendships = await self.db.friendships.find({
                "$or": [
                    {"user_id": avatar_id, "status": "accepted"},
                    {"friend_id": avatar_id, "status": "accepted"}
                ]
            }).limit(limit).to_list(limit)
            
            friend_ids = []
            for f in friendships:
                if f.get("user_id") == avatar_id:
                    friend_ids.append(f.get("friend_id"))
                else:
                    friend_ids.append(f.get("user_id"))
            
            if not friend_ids:
                return []
            
            # Get friend details
            friends = await self.db.users.find(
                {"id": {"$in": friend_ids}}
            ).to_list(len(friend_ids))
            
            formatted = []
            for friend in friends:
                formatted.append({
                    "id": friend.get("id"),
                    "name": friend.get("avatar_name") or friend.get("display_name") or friend.get("name", "Friend"),
                    "archetype": friend.get("avatar_archetype", friend.get("archetype")),
                    "interests": (friend.get("avatar_interests") or friend.get("interests", []))[:3]
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error fetching friends: {e}")
            return []
    
    async def _get_friend_activity_summary(
        self, 
        avatar_id: str, 
        limit: int = 5,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get summary of what friends are doing"""
        try:
            # First get friend IDs
            friends = await self._get_friends_summary(avatar_id, limit=20)
            friend_ids = [f["id"] for f in friends]
            friend_names = {f["id"]: f["name"] for f in friends}
            
            return await self._get_friend_activity_optimized(friend_ids, friend_names, limit, since)
            
        except Exception as e:
            logger.error(f"Error fetching friend activity: {e}")
            return []
    
    async def _get_friend_activity_optimized(
        self,
        friend_ids: List[str],
        friend_names: Dict[str, str],
        limit: int = 5,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get friend activity with pre-fetched friend data (no redundant queries)"""
        try:
            if not friend_ids:
                return []
            
            # Get recent posts from friends
            query = {"user_id": {"$in": friend_ids}}
            if since:
                query["created_at"] = {"$gte": since.isoformat()}
            else:
                # Default to last 48 hours for more content
                default_since = datetime.now(timezone.utc) - timedelta(hours=48)
                query["created_at"] = {"$gte": default_since.isoformat()}
            
            posts = await self.db.posts.find(query)\
                .sort("created_at", -1)\
                .limit(limit)\
                .to_list(limit)
            
            formatted = []
            for post in posts:
                friend_id = post.get("user_id")
                friend_name = friend_names.get(friend_id, "A friend")
                
                formatted.append({
                    "friend_name": friend_name,
                    "friend_id": friend_id,
                    "action": "posted",
                    "content_preview": (post.get("text") or post.get("content", ""))[:80],
                    "timestamp": post.get("created_at"),
                    "likes": len(post.get("liked_by", [])) if isinstance(post.get("liked_by"), list) else post.get("likes", 0),
                    "comments": len(post.get("comments", []))
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error fetching friend activity: {e}")
            return []
    
    async def _get_conversation_summaries(self, avatar_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get summaries of recent conversations"""
        return await self._get_conversation_summaries_optimized(avatar_id, limit)
    
    async def _get_conversation_summaries_optimized(self, avatar_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get summaries of recent conversations with batched user lookups"""
        try:
            # Get agent conversations
            conversations = await self.db.agent_conversations.find({
                "$or": [
                    {"agent1_user_id": avatar_id},
                    {"agent2_user_id": avatar_id}
                ]
            }).sort("updated_at", -1).limit(limit).to_list(limit)
            
            if not conversations:
                return []
            
            # Collect all other user IDs for batch lookup
            other_ids = []
            for conv in conversations:
                other_id = conv.get("agent2_user_id") if conv.get("agent1_user_id") == avatar_id else conv.get("agent1_user_id")
                if other_id:
                    other_ids.append(other_id)
            
            # Batch fetch all users at once
            users = await self.db.users.find({"id": {"$in": other_ids}}).to_list(len(other_ids))
            user_map = {u.get("id"): u for u in users}
            
            formatted = []
            for conv in conversations:
                other_id = conv.get("agent2_user_id") if conv.get("agent1_user_id") == avatar_id else conv.get("agent1_user_id")
                
                other_user = user_map.get(other_id, {})
                other_name = other_user.get("avatar_name") or other_user.get("display_name") or other_user.get("name", "Someone")
                
                messages = conv.get("messages", [])
                last_messages = messages[-3:] if messages else []
                
                summary = conv.get("conversation_summary", "")
                if not summary and last_messages:
                    last_msg = last_messages[-1]
                    summary = f"Talking about: {last_msg.get('message', '')[:50]}..."
                
                formatted.append({
                    "with": other_name,
                    "with_id": other_id,
                    "summary": summary,
                    "message_count": len(messages),
                    "last_message": last_messages[-1].get("message", "") if last_messages else "",
                    "last_activity": conv.get("updated_at"),
                    "status": conv.get("status", "active")
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error fetching conversations: {e}")
            return []
    
    async def _get_unread_messages(self, avatar_id: str) -> Dict[str, Any]:
        """Get count and sources of unread messages (full version)"""
        return await self._get_unread_count(avatar_id)
    
    async def _get_unread_count(self, avatar_id: str) -> Dict[str, Any]:
        """Get count of unread messages (optimized - no sender lookup)"""
        try:
            unread_count = 0
            
            # Check direct messages - just count, don't fetch sender details
            conversations = await self.db.direct_messages.find({
                "$or": [
                    {"user1_id": avatar_id},
                    {"user2_id": avatar_id}
                ]
            }).sort("updated_at", -1).limit(5).to_list(5)
            
            for conv in conversations:
                messages = conv.get("messages", [])
                for msg in messages[-10:]:  # Only check last 10 messages per conversation
                    if not msg.get("read", True) and msg.get("sender_id") != avatar_id:
                        unread_count += 1
            
            return {
                "count": unread_count,
                "from": []  # Skip sender lookup for speed
            }
            
        except Exception as e:
            logger.error(f"Error fetching unread count: {e}")
            return {"count": 0, "from": []}
    
    async def _get_specific_friend_details(self, avatar_id: str, friend_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a specific friend by name"""
        try:
            # Find friend by name (case-insensitive)
            friend = await self.db.users.find_one({
                "$or": [
                    {"avatar_name": {"$regex": friend_name, "$options": "i"}},
                    {"display_name": {"$regex": friend_name, "$options": "i"}},
                    {"name": {"$regex": friend_name, "$options": "i"}}
                ]
            })
            
            if not friend:
                return None
            
            friend_id = friend.get("id")
            
            # Get recent posts by this friend
            recent_posts = await self.db.posts.find(
                {"user_id": friend_id}
            ).sort("created_at", -1).limit(3).to_list(3)
            
            # Get conversation history with this friend
            conversation = await self.db.agent_conversations.find_one({
                "$or": [
                    {"agent1_user_id": avatar_id, "agent2_user_id": friend_id},
                    {"agent1_user_id": friend_id, "agent2_user_id": avatar_id}
                ]
            })
            
            return {
                "name": friend.get("avatar_name") or friend.get("display_name") or friend.get("name"),
                "bio": friend.get("bio", ""),
                "interests": friend.get("avatar_interests") or friend.get("interests", []),
                "archetype": friend.get("avatar_archetype", friend.get("archetype")),
                "recent_posts": [
                    {
                        "content": (p.get("text") or p.get("content", ""))[:100],
                        "likes": len(p.get("liked_by", [])) if isinstance(p.get("liked_by"), list) else p.get("likes", 0),
                        "timestamp": p.get("created_at")
                    }
                    for p in recent_posts
                ],
                "conversation_summary": conversation.get("conversation_summary") if conversation else None,
                "last_talked": conversation.get("updated_at") if conversation else None
            }
            
        except Exception as e:
            logger.error(f"Error fetching specific friend: {e}")
            return None
    
    async def _get_specific_conversation(self, avatar_id: str, friend_name: str) -> Optional[Dict[str, Any]]:
        """Get specific conversation history with a friend"""
        try:
            # Find friend by name
            friend = await self.db.users.find_one({
                "$or": [
                    {"avatar_name": {"$regex": friend_name, "$options": "i"}},
                    {"display_name": {"$regex": friend_name, "$options": "i"}},
                    {"name": {"$regex": friend_name, "$options": "i"}}
                ]
            })
            
            if not friend:
                return None
            
            friend_id = friend.get("id")
            friend_display_name = friend.get("avatar_name") or friend.get("display_name") or friend.get("name")
            
            # Get conversation
            conversation = await self.db.agent_conversations.find_one({
                "$or": [
                    {"agent1_user_id": avatar_id, "agent2_user_id": friend_id},
                    {"agent1_user_id": friend_id, "agent2_user_id": avatar_id}
                ]
            })
            
            if not conversation:
                return {
                    "friend_name": friend_display_name,
                    "has_conversation": False,
                    "messages": []
                }
            
            messages = conversation.get("messages", [])
            
            # Get last 10 messages
            recent_messages = messages[-10:] if len(messages) > 10 else messages
            
            formatted_messages = []
            for msg in recent_messages:
                sender = msg.get("sender")
                is_me = sender == avatar_id
                formatted_messages.append({
                    "sender": "me" if is_me else friend_display_name,
                    "message": msg.get("message", ""),
                    "timestamp": msg.get("timestamp")
                })
            
            return {
                "friend_name": friend_display_name,
                "has_conversation": True,
                "summary": conversation.get("conversation_summary", ""),
                "messages": formatted_messages,
                "total_messages": len(messages),
                "status": conversation.get("status", "active")
            }
            
        except Exception as e:
            logger.error(f"Error fetching specific conversation: {e}")
            return None
    
    # ===== Formatting Methods =====
    
    def _format_tier1_context(
        self,
        my_activities: List[Dict],
        my_posts: List[Dict],
        friends: List[Dict],
        friend_activity: List[Dict],
        conversations: List[Dict],
        unread: Dict
    ) -> str:
        """Format Tier 1 context into natural language for the prompt"""
        sections = []
        
        # My recent activity
        if my_activities:
            activity_lines = []
            for act in my_activities[:3]:
                desc = act.get("description", act.get("type", "something"))
                activity_lines.append(f"- {desc}")
            if activity_lines:
                sections.append("### What I've Been Doing\n" + "\n".join(activity_lines))
        
        # My posts and engagement
        if my_posts:
            post_lines = []
            for post in my_posts[:2]:
                content = post.get("content", "something")[:60]
                likes = post.get("likes", 0)
                comments = post.get("comments", 0)
                commenters = post.get("commenter_names", [])
                
                line = f"- Posted about \"{content}...\""
                if likes > 0 or comments > 0:
                    engagement = []
                    if likes > 0:
                        engagement.append(f"{likes} likes")
                    if comments > 0:
                        commenter_str = f" from {', '.join(commenters[:2])}" if commenters else ""
                        engagement.append(f"{comments} comments{commenter_str}")
                    line += f" — got {' and '.join(engagement)}"
                post_lines.append(line)
            if post_lines:
                sections.append("### My Recent Posts\n" + "\n".join(post_lines))
        
        # Friends
        if friends:
            friend_names = [f.get("name") for f in friends[:8]]
            sections.append(f"### My Friends\n{', '.join(friend_names)}")
        
        # Friend activity
        if friend_activity:
            activity_lines = []
            for act in friend_activity[:3]:
                name = act.get("friend_name", "A friend")
                content = act.get("content_preview", "something")[:50]
                likes = act.get("likes", 0)
                activity_lines.append(f"- {name} posted: \"{content}...\"" + (f" ({likes} likes)" if likes > 0 else ""))
            if activity_lines:
                sections.append("### What My Friends Are Doing\n" + "\n".join(activity_lines))
        
        # Conversations
        if conversations:
            conv_lines = []
            for conv in conversations[:2]:
                with_name = conv.get("with", "someone")
                summary = conv.get("summary", conv.get("last_message", ""))[:50]
                if summary:
                    conv_lines.append(f"- Chatting with {with_name}: {summary}...")
                else:
                    conv_lines.append(f"- Have been talking with {with_name}")
            if conv_lines:
                sections.append("### My Recent Conversations\n" + "\n".join(conv_lines))
        
        # Unread messages
        if unread.get("count", 0) > 0:
            from_names = [u.get("name") for u in unread.get("from", [])]
            if from_names:
                sections.append(f"### Unread Messages\n{unread['count']} unread messages from: {', '.join(from_names)}")
            else:
                sections.append(f"### Unread Messages\n{unread['count']} unread messages")
        
        if sections:
            return "## Your Social Life Right Now\n\n" + "\n\n".join(sections)
        else:
            return "## Your Social Life Right Now\nNothing specific to report - it's been quiet."
    
    def _format_activity_response(self, data: List[Dict]) -> Dict[str, Any]:
        """Format activity data for function response"""
        if not data:
            return {"summary": "I haven't been very active lately.", "data": []}
        
        lines = []
        for act in data:
            lines.append(f"- {act.get('description', act.get('type', 'Did something'))}")
        
        return {
            "summary": "Here's what I've been up to:\n" + "\n".join(lines),
            "data": data
        }
    
    def _format_posts_response(self, data: List[Dict]) -> Dict[str, Any]:
        """Format posts data for function response"""
        if not data:
            return {"summary": "I haven't posted anything recently.", "data": []}
        
        lines = []
        for post in data:
            content = post.get("content", "something")[:60]
            likes = post.get("likes", 0)
            comments = post.get("comments", 0)
            lines.append(f"- \"{content}...\" ({likes} likes, {comments} comments)")
        
        return {
            "summary": "My recent posts:\n" + "\n".join(lines),
            "data": data
        }
    
    def _format_friends_response(self, data: List[Dict]) -> Dict[str, Any]:
        """Format friends data for function response"""
        if not data:
            return {"summary": "I don't have any friends yet.", "data": []}
        
        names = [f.get("name") for f in data]
        return {
            "summary": f"My friends: {', '.join(names)}",
            "data": data
        }
    
    def _format_friend_activity_response(self, data: List[Dict]) -> Dict[str, Any]:
        """Format friend activity for function response"""
        if not data:
            return {"summary": "My friends have been quiet lately.", "data": []}
        
        lines = []
        for act in data:
            name = act.get("friend_name", "Someone")
            content = act.get("content_preview", "something")[:50]
            lines.append(f"- {name}: \"{content}...\"")
        
        return {
            "summary": "What my friends have been up to:\n" + "\n".join(lines),
            "data": data
        }
    
    def _format_conversations_response(self, data: List[Dict]) -> Dict[str, Any]:
        """Format conversations for function response"""
        if not data:
            return {"summary": "I haven't had any conversations recently.", "data": []}
        
        lines = []
        for conv in data:
            name = conv.get("with", "someone")
            summary = conv.get("summary", "chatting")[:40]
            lines.append(f"- With {name}: {summary}...")
        
        return {
            "summary": "My recent conversations:\n" + "\n".join(lines),
            "data": data
        }
    
    def _format_specific_friend_response(self, data: Optional[Dict], friend_name: str) -> Dict[str, Any]:
        """Format specific friend details"""
        if not data:
            return {"summary": f"I don't think I know anyone named {friend_name}.", "data": None}
        
        name = data.get("name", friend_name)
        bio = data.get("bio", "")
        interests = data.get("interests", [])
        recent_posts = data.get("recent_posts", [])
        
        lines = [f"About {name}:"]
        if bio:
            lines.append(f"- Bio: {bio[:100]}")
        if interests:
            lines.append(f"- Interests: {', '.join(interests[:5])}")
        if recent_posts:
            lines.append("- Recent posts:")
            for post in recent_posts[:2]:
                lines.append(f"  - \"{post.get('content', '')[:50]}...\"")
        if data.get("conversation_summary"):
            lines.append(f"- We've been talking about: {data['conversation_summary'][:50]}...")
        
        return {
            "summary": "\n".join(lines),
            "data": data
        }
    
    def _format_specific_conversation_response(self, data: Optional[Dict], friend_name: str) -> Dict[str, Any]:
        """Format specific conversation details"""
        if not data:
            return {"summary": f"I haven't had a conversation with {friend_name}.", "data": None}
        
        if not data.get("has_conversation"):
            return {"summary": f"I haven't chatted with {data.get('friend_name', friend_name)} yet.", "data": None}
        
        name = data.get("friend_name", friend_name)
        messages = data.get("messages", [])
        summary = data.get("summary", "")
        
        lines = [f"My conversation with {name}:"]
        if summary:
            lines.append(f"Topic: {summary[:80]}")
        if messages:
            lines.append("Recent messages:")
            for msg in messages[-5:]:
                sender = msg.get("sender", "?")
                message = msg.get("message", "")[:60]
                lines.append(f"  {sender}: \"{message}...\"")
        
        return {
            "summary": "\n".join(lines),
            "data": data
        }
    
    def _get_time_filter(self, time_range: str) -> Optional[datetime]:
        """Convert time range string to datetime filter"""
        now = datetime.now(timezone.utc)
        
        if time_range == "today":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == "yesterday":
            return now - timedelta(days=1)
        elif time_range == "this_week":
            return now - timedelta(days=7)
        elif time_range == "recent":
            return now - timedelta(hours=24)
        else:
            return None
