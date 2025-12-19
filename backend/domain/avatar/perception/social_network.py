"""
Social Network Perception
Perceives activity in the avatar's social network
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


class SocialNetworkPerception:
    """
    Perceives activity in the avatar's social network
    
    Provides:
    - Recent posts from friends (last 24h)
    - Friend activity patterns
    - Trending topics in friend network
    - Friend interactions (likes, comments, shares)
    - Extended network activity (friends of friends)
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def perceive_friend_activity(self, avatar_id: str) -> Dict[str, Any]:
        """
        Perceive friend activity in the last 24 hours
        
        Returns:
        - recent_posts: List of posts from friends (last 24h)
        - friend_activity_level: Float (0.0-1.0) indicating activity level
        - posting_frequencies: Dict of friend_id -> posts_per_day
        - trending_topics: List of trending topics in friend network
        - friend_interactions: Dict of interaction counts
        """
        try:
            # Check cache first
            cache_key = f"friend_activity_{avatar_id}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if (datetime.now(timezone.utc) - cached_time).total_seconds() < self.cache_ttl:
                    return cached_data
            
            # Get friends list
            from services.friend_service import FriendService
            friend_service = FriendService(self.db)
            friends = await friend_service.get_friends(avatar_id)
            friend_ids = [f['id'] for f in friends]
            
            if not friend_ids:
                result = {
                    "recent_posts": [],
                    "friend_activity_level": 0.0,
                    "posting_frequencies": {},
                    "trending_topics": [],
                    "friend_interactions": {}
                }
                self.cache[cache_key] = (result, datetime.now(timezone.utc))
                return result
            
            # Get posts from friends in last 24 hours
            since_time = datetime.now(timezone.utc) - timedelta(hours=24)
            since_time_str = since_time.isoformat()
            
            # Query posts from friends with date filter - limit to 10 posts for performance
            # Use both string and datetime comparison for compatibility
            posts_cursor = self.db.posts.find({
                "user_id": {"$in": friend_ids},
                "$or": [
                    {"created_at": {"$gte": since_time_str}},
                    {"created_at": {"$gte": since_time}}
                ]
            }).sort([("created_at", -1)]).limit(10)  # Reduced to 10 posts for performance testing
            
            all_posts = await posts_cursor.to_list(10)
            
            # Filter posts by date in Python (handles mixed date formats) - but most should already be filtered
            recent_posts = []
            for post in all_posts:
                post_time = self._parse_post_time(post)
                if post_time and post_time >= since_time:
                    recent_posts.append(post)
            
            # Calculate friend activity level (0.0-1.0)
            # Based on number of posts and engagement
            total_posts = len(recent_posts)
            max_expected_posts = len(friend_ids) * 5  # Assume max 5 posts per friend per day
            friend_activity_level = min(total_posts / max_expected_posts if max_expected_posts > 0 else 0, 1.0)
            
            # Calculate posting frequencies
            posting_frequencies = {}
            for post in recent_posts:
                friend_id = post.get('user_id')
                if friend_id:
                    posting_frequencies[friend_id] = posting_frequencies.get(friend_id, 0) + 1
            
            # Detect trending topics (simple keyword extraction from posts)
            trending_topics = self._extract_trending_topics(recent_posts)
            
            # Count friend interactions
            friend_interactions = {
                "likes": sum(post.get('likes', 0) for post in recent_posts),
                "comments": sum(post.get('comment_count', 0) for post in recent_posts),
                "total_engagement": sum(
                    post.get('likes', 0) + post.get('comment_count', 0)
                    for post in recent_posts
                )
            }
            
            # Get relationship info for friends (add to social network perception)
            relationship_info = {}
            if friend_ids:
                from services.friend_service import FriendService
                friend_service = FriendService(self.db)
                friends = await friend_service.get_friends(avatar_id)
                
                # Create relationship map for friends
                for friend in friends:
                    friend_id = friend['id']
                    relationship_info[friend_id] = {
                        "friend_name": friend.get('avatar_name') or friend.get('name', 'Unknown'),
                        "friend_interests": friend.get('avatar_interests') or friend.get('interests', []),
                        "is_bot": friend.get('is_bot', False)
                    }
            
            result = {
                "recent_posts": recent_posts[:50],  # Return top 50 for performance
                "friend_activity_level": friend_activity_level,
                "posting_frequencies": posting_frequencies,
                "trending_topics": trending_topics,
                "friend_interactions": friend_interactions,
                "total_friend_posts": total_posts,
                "friend_count": len(friend_ids),
                "friend_relationships": relationship_info  # Add relationship info
            }
            
            # Cache result
            self.cache[cache_key] = (result, datetime.now(timezone.utc))
            
            return result
            
        except Exception as e:
            logger.error(f"Error perceiving friend activity for {avatar_id}: {e}")
            return {
                "recent_posts": [],
                "friend_activity_level": 0.0,
                "posting_frequencies": {},
                "trending_topics": [],
                "friend_interactions": {}
            }
    
    async def perceive_connection_circle(self, avatar_id: str) -> Dict[str, Any]:
        """
        Perceive extended network activity (friends of friends)
        
        Returns:
        - extended_network_activity: Activity level in extended network
        - viral_content: Content going viral in network
        - network_trends: Trends across extended network
        - network_events: Notable events in network
        """
        try:
            cache_key = f"connection_circle_{avatar_id}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if (datetime.now(timezone.utc) - cached_time).total_seconds() < self.cache_ttl:
                    return cached_data
            
            # Get friends
            from services.friend_service import FriendService
            friend_service = FriendService(self.db)
            friends = await friend_service.get_friends(avatar_id)
            friend_ids = [f['id'] for f in friends]
            
            if not friend_ids:
                result = {
                    "extended_network_activity": 0.0,
                    "viral_content": [],
                    "network_trends": [],
                    "network_events": []
                }
                self.cache[cache_key] = (result, datetime.now(timezone.utc))
                return result
            
            # Get friends of friends (extended network)
            extended_friend_ids = set(friend_ids)
            for friend_id in friend_ids:
                friend_friends = await friend_service.get_friends(friend_id)
                for ff in friend_friends:
                    if ff['id'] != avatar_id:  # Don't include self
                        extended_friend_ids.add(ff['id'])
            
            extended_friend_ids = list(extended_friend_ids)
            
            # Get posts from extended network in last 48 hours
            since_time = datetime.now(timezone.utc) - timedelta(hours=48)
            
            # Fetch all posts and filter by date
            posts_cursor = self.db.posts.find({
                "user_id": {"$in": extended_friend_ids}
            }).sort([("created_at", -1)])
            
            all_extended_posts = await posts_cursor.to_list(10)  # Reduced for performance
            
            # Filter by date
            extended_posts = []
            for post in all_extended_posts:
                post_time = self._parse_post_time(post)
                if post_time and post_time >= since_time:
                    extended_posts.append(post)
            
            # Calculate extended network activity
            total_extended_posts = len(extended_posts)
            max_expected = len(extended_friend_ids) * 3
            extended_network_activity = min(
                total_extended_posts / max_expected if max_expected > 0 else 0,
                1.0
            )
            
            # Find viral content (posts with high engagement)
            viral_content = []
            for post in extended_posts:
                engagement = post.get('likes', 0) + post.get('comment_count', 0)
                if engagement > 10:  # Threshold for "viral"
                    viral_content.append({
                        "post_id": post.get('id'),
                        "user_id": post.get('user_id'),
                        "engagement": engagement,
                        "created_at": post.get('created_at')
                    })
            
            # Sort by engagement
            viral_content.sort(key=lambda x: x['engagement'], reverse=True)
            viral_content = viral_content[:10]  # Top 10 viral posts
            
            # Extract network trends
            network_trends = self._extract_trending_topics(extended_posts)
            
            # Network events (simplified - can be enhanced)
            network_events = []
            # Could detect: new friendships, major posts, etc.
            
            result = {
                "extended_network_activity": extended_network_activity,
                "viral_content": viral_content,
                "network_trends": network_trends,
                "network_events": network_events,
                "extended_network_size": len(extended_friend_ids)
            }
            
            self.cache[cache_key] = (result, datetime.now(timezone.utc))
            return result
            
        except Exception as e:
            logger.error(f"Error perceiving connection circle for {avatar_id}: {e}")
            return {
                "extended_network_activity": 0.0,
                "viral_content": [],
                "network_trends": [],
                "network_events": []
            }
    
    async def perceive_direct_interactions(self, avatar_id: str) -> Dict[str, Any]:
        """
        Perceive direct interactions with the avatar
        
        Returns:
        - unread_messages: Count of unread messages
        - pending_friend_requests: Count of pending requests
        - comments_on_posts: Comments on avatar's posts
        - reactions_to_content: Reactions to avatar's content
        - mentions: Mentions of the avatar
        """
        try:
            cache_key = f"direct_interactions_{avatar_id}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if (datetime.now(timezone.utc) - cached_time).total_seconds() < self.cache_ttl:
                    return cached_data
            
            # Get unread messages
            # Messages are stored in direct_messages collection (conversations)
            # and agent_conversations collection (avatar world)
            unread_messages = 0
            
            # Check direct_messages (real world)
            conversations = await self.db.direct_messages.find({
                "$or": [
                    {"user1_id": avatar_id},
                    {"user2_id": avatar_id}
                ]
            }).sort([("updated_at", -1)]).limit(10).to_list(10)  # Reduced for performance
            
            for conv in conversations:
                messages = conv.get('messages', [])
                for msg in messages:
                    # Check if message is unread and not from self
                    if (msg.get('read', True) == False and 
                        msg.get('sender_id') != avatar_id):
                        unread_messages += 1
            
            # Check agent_conversations (avatar world)
            # Find conversations where avatar is agent1 or agent2
            user_id_list = [avatar_id]
            agent_conversations = await self.db.agent_conversations.find({
                "$or": [
                    {"agent1_user_id": avatar_id},
                    {"agent2_user_id": avatar_id}
                ]
            }).sort([("updated_at", -1)]).limit(10).to_list(10)  # Reduced for performance
            
            for conv in agent_conversations:
                messages = conv.get('messages', [])
                for msg in messages:
                    # Check if message is unread and not from self
                    sender = msg.get('sender')
                    if sender and sender != avatar_id:
                        # Assume unread if no read flag (simplified)
                        if not msg.get('read', False):
                            unread_messages += 1
            
            # Get pending friend requests
            pending_friend_requests = await self.db.friendships.count_documents({
                "friend_id": avatar_id,
                "status": "pending"
            })
            
            # Get comments on avatar's posts (recent)
            since_time = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Fetch all avatar posts and filter by date
            all_avatar_posts = await self.db.posts.find({
                "user_id": avatar_id
            }).sort([("created_at", -1)]).limit(10).to_list(10)  # Reduced for performance
            
            avatar_posts = []
            for post in all_avatar_posts:
                post_time = self._parse_post_time(post)
                if post_time and post_time >= since_time:
                    avatar_posts.append(post)
            
            comments_on_posts = []
            for post in avatar_posts:
                post_comments = post.get('comments', [])
                for comment in post_comments:
                    if comment.get('user_id') != avatar_id:  # Exclude own comments
                        comments_on_posts.append({
                            "post_id": post.get('id'),
                            "comment": comment,
                            "created_at": comment.get('created_at')
                        })
            
            # Sort by recency
            comments_on_posts.sort(
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )
            comments_on_posts = comments_on_posts[:20]  # Recent 20 comments
            
            # Get reactions (likes) on avatar's posts
            reactions_to_content = {
                "total_likes": 0,
                "recent_likes": []
            }
            
            for post in avatar_posts:
                likes = post.get('likes', 0)
                reactions_to_content["total_likes"] += likes
                
                liked_by = post.get('liked_by', [])
                for like in liked_by[-10:]:  # Recent 10 likes
                    reactions_to_content["recent_likes"].append({
                        "post_id": post.get('id'),
                        "user_id": like.get('user_id') if isinstance(like, dict) else like,
                        "created_at": like.get('created_at') if isinstance(like, dict) else None
                    })
            
            # Mentions (simplified - would need to parse post text)
            mentions = []  # TODO: Implement mention detection
            
            result = {
                "unread_messages": unread_messages,
                "pending_friend_requests": pending_friend_requests,
                "comments_on_posts": comments_on_posts,
                "reactions_to_content": reactions_to_content,
                "mentions": mentions,
                "total_interactions": (
                    unread_messages +
                    pending_friend_requests +
                    len(comments_on_posts) +
                    reactions_to_content["total_likes"]
                )
            }
            
            self.cache[cache_key] = (result, datetime.now(timezone.utc))
            return result
            
        except Exception as e:
            logger.error(f"Error perceiving direct interactions for {avatar_id}: {e}")
            return {
                "unread_messages": 0,
                "pending_friend_requests": 0,
                "comments_on_posts": [],
                "reactions_to_content": {"total_likes": 0, "recent_likes": []},
                "mentions": [],
                "total_interactions": 0
            }
    
    def _parse_post_time(self, post: Dict) -> Optional[datetime]:
        """Parse post timestamp, handling various formats"""
        try:
            # Try created_at first
            time_str = post.get('created_at') or post.get('timestamp')
            if not time_str:
                return None
            
            if isinstance(time_str, datetime):
                if time_str.tzinfo is None:
                    return time_str.replace(tzinfo=timezone.utc)
                return time_str
            
            if isinstance(time_str, str):
                # Try ISO format
                if 'T' in time_str:
                    try:
                        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt
                    except Exception:
                        pass
                
                # Try old format: "2025-10-25 09:20:32.884000"
                try:
                    dt = datetime.strptime(time_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                    return dt.replace(tzinfo=timezone.utc)
                except Exception:
                    pass
            
            return None
        except Exception:
            return None
    
    def _extract_trending_topics(self, posts: List[Dict]) -> List[str]:
        """
        Extract trending topics from posts (simple keyword-based)
        
        TODO: Can be enhanced with NLP/topic modeling
        """
        # Simple implementation: count common words
        word_count = {}
        
        for post in posts:
            text = post.get('text', '') or post.get('content', '')
            if not text:
                continue
            
            # Simple word extraction (can be improved)
            words = text.lower().split()
            # Filter out common words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their'}
            
            for word in words:
                # Remove punctuation
                word = word.strip('.,!?;:()[]{}"\'-')
                if len(word) > 3 and word not in stop_words:
                    word_count[word] = word_count.get(word, 0) + 1
        
        # Get top 10 trending words
        trending = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]
        return [word for word, count in trending]

