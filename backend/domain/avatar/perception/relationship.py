"""
Relationship Perception
Understands relationship dynamics with connections
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


class RelationshipPerception:
    """
    Perceives relationship context and dynamics
    
    Provides:
    - Relationship strength scores
    - Relationship types (close_friend, friend, acquaintance, new_connection)
    - Relationship trends (strengthening, weakening, stable)
    - Social status metrics
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 600  # 10 minutes (relationships change less frequently)
    
    async def perceive_relationship_strength(
        self,
        avatar_id: str,
        friend_id: str
    ) -> Dict[str, Any]:
        """
        Calculate relationship strength between avatar and friend
        
        Returns:
        - strength_score: Float (0.0-1.0) indicating relationship strength
        - interaction_frequency: Float (0.0-1.0)
        - mutual_interests: Float (0.0-1.0) - overlap in interests
        - conversation_depth: Float (0.0-1.0) - depth of conversations
        - recency_score: Float (0.0-1.0) - how recent interactions are
        - engagement_quality: Float (0.0-1.0) - quality of engagement
        """
        try:
            cache_key = f"relationship_strength_{avatar_id}_{friend_id}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if (datetime.now(timezone.utc) - cached_time).total_seconds() < self.cache_ttl:
                    return cached_data
            
            # 1. Calculate interaction frequency
            # Count interactions in last 30 days
            since_time = datetime.now(timezone.utc) - timedelta(days=30)
            
            # Count messages exchanged
            messages_count = 0
            # Check direct_messages
            conversations = await self.db.direct_messages.find({
                "$or": [
                    {"user1_id": avatar_id, "user2_id": friend_id},
                    {"user1_id": friend_id, "user2_id": avatar_id}
                ]
            }).to_list(10)
            
            for conv in conversations:
                messages = conv.get('messages', [])
                for msg in messages:
                    msg_time = msg.get('timestamp') or msg.get('created_at')
                    if msg_time:
                        try:
                            if isinstance(msg_time, str):
                                msg_dt = datetime.fromisoformat(msg_time.replace('Z', '+00:00'))
                            else:
                                msg_dt = msg_time
                            
                            if msg_dt >= since_time:
                                messages_count += 1
                        except Exception:
                            pass
            
            # Count posts interactions (likes, comments)
            posts_interactions = 0
            # Get avatar's posts that friend interacted with
            avatar_posts = await self.db.posts.find({
                "user_id": avatar_id,
                "created_at": {"$gte": since_time.isoformat()}
            }).sort([("created_at", -1)]).limit(10).to_list(10)  # Reduced for performance
            
            for post in avatar_posts:
                # Check if friend liked
                liked_by = post.get('liked_by', [])
                for like in liked_by:
                    like_user_id = like.get('user_id') if isinstance(like, dict) else like
                    if like_user_id == friend_id:
                        posts_interactions += 1
                        break
                
                # Check if friend commented
                comments = post.get('comments', [])
                for comment in comments:
                    if comment.get('user_id') == friend_id:
                        posts_interactions += 1
                        break
            
            # Get friend's posts that avatar interacted with
            friend_posts = await self.db.posts.find({
                "user_id": friend_id,
                "created_at": {"$gte": since_time.isoformat()}
            }).sort([("created_at", -1)]).limit(10).to_list(10)  # Reduced for performance
            
            for post in friend_posts:
                # Check if avatar liked
                liked_by = post.get('liked_by', [])
                for like in liked_by:
                    like_user_id = like.get('user_id') if isinstance(like, dict) else like
                    if like_user_id == avatar_id:
                        posts_interactions += 1
                        break
                
                # Check if avatar commented
                comments = post.get('comments', [])
                for comment in comments:
                    if comment.get('user_id') == avatar_id:
                        posts_interactions += 1
                        break
            
            total_interactions = messages_count + posts_interactions
            # Normalize: assume max 50 interactions per month = 1.0
            interaction_frequency = min(total_interactions / 50.0, 1.0)
            
            # 2. Calculate mutual interests
            # Get avatar's interests from knowledge graph or user profile
            avatar_user = await self.db.users.find_one(
                {"id": avatar_id},
                {"interests": 1, "avatar_interests": 1}
            )
            friend_user = await self.db.users.find_one(
                {"id": friend_id},
                {"interests": 1, "avatar_interests": 1}
            )
            
            avatar_interests = set()
            if avatar_user:
                avatar_interests.update(avatar_user.get('interests', []))
                avatar_interests.update(avatar_user.get('avatar_interests', []))
            
            friend_interests = set()
            if friend_user:
                friend_interests.update(friend_user.get('interests', []))
                friend_interests.update(friend_user.get('avatar_interests', []))
            
            # Calculate overlap
            if avatar_interests and friend_interests:
                mutual = avatar_interests.intersection(friend_interests)
                total_unique = avatar_interests.union(friend_interests)
                mutual_interests = len(mutual) / len(total_unique) if total_unique else 0.0
            else:
                mutual_interests = 0.0
            
            # 3. Calculate conversation depth
            # Average message length and conversation length
            total_message_length = 0
            total_messages = 0
            conversation_count = 0
            
            for conv in conversations:
                messages = conv.get('messages', [])
                if messages:
                    conversation_count += 1
                    for msg in messages:
                        content = msg.get('content') or msg.get('message', '')
                        if content:
                            total_message_length += len(content)
                            total_messages += 1
            
            if total_messages > 0:
                avg_message_length = total_message_length / total_messages
                # Normalize: assume 100+ chars = deep conversation
                conversation_depth = min(avg_message_length / 100.0, 1.0)
            else:
                conversation_depth = 0.0
            
            # 4. Calculate recency score
            # How recent was the last interaction?
            last_interaction_time = None
            
            # Check last message
            for conv in conversations:
                messages = conv.get('messages', [])
                if messages:
                    last_msg = messages[-1]
                    msg_time = last_msg.get('timestamp') or last_msg.get('created_at')
                    if msg_time:
                        try:
                            if isinstance(msg_time, str):
                                msg_dt = datetime.fromisoformat(msg_time.replace('Z', '+00:00'))
                            else:
                                msg_dt = msg_time
                            
                            if not last_interaction_time or msg_dt > last_interaction_time:
                                last_interaction_time = msg_dt
                        except Exception:
                            pass
            
            if last_interaction_time:
                days_since = (datetime.now(timezone.utc) - last_interaction_time).days
                # Normalize: 0 days = 1.0, 30+ days = 0.0
                recency_score = max(1.0 - (days_since / 30.0), 0.0)
            else:
                recency_score = 0.0
            
            # 5. Calculate engagement quality
            # Based on meaningful interactions (comments > likes, longer messages)
            meaningful_interactions = 0
            total_interactions_for_quality = messages_count + posts_interactions
            
            # Comments are more meaningful than likes
            for post in avatar_posts + friend_posts:
                comments = post.get('comments', [])
                for comment in comments:
                    commenter_id = comment.get('user_id')
                    if (commenter_id == friend_id and post.get('user_id') == avatar_id) or \
                       (commenter_id == avatar_id and post.get('user_id') == friend_id):
                        meaningful_interactions += 2  # Comments worth 2x
            
            # Messages are meaningful
            meaningful_interactions += messages_count
            
            if total_interactions_for_quality > 0:
                engagement_quality = min(meaningful_interactions / total_interactions_for_quality, 1.0)
            else:
                engagement_quality = 0.0
            
            # 6. Calculate overall strength score
            # Weighted combination
            strength_score = (
                interaction_frequency * 0.3 +
                mutual_interests * 0.25 +
                conversation_depth * 0.2 +
                recency_score * 0.15 +
                engagement_quality * 0.1
            )
            
            result = {
                "strength_score": round(strength_score, 3),
                "interaction_frequency": round(interaction_frequency, 3),
                "mutual_interests": round(mutual_interests, 3),
                "conversation_depth": round(conversation_depth, 3),
                "recency_score": round(recency_score, 3),
                "engagement_quality": round(engagement_quality, 3),
                "total_interactions": total_interactions,
                "last_interaction_days_ago": (
                    (datetime.now(timezone.utc) - last_interaction_time).days
                    if last_interaction_time else None
                )
            }
            
            self.cache[cache_key] = (result, datetime.now(timezone.utc))
            return result
            
        except Exception as e:
            logger.error(f"Error calculating relationship strength {avatar_id}-{friend_id}: {e}")
            return {
                "strength_score": 0.0,
                "interaction_frequency": 0.0,
                "mutual_interests": 0.0,
                "conversation_depth": 0.0,
                "recency_score": 0.0,
                "engagement_quality": 0.0,
                "total_interactions": 0,
                "last_interaction_days_ago": None
            }
    
    async def perceive_relationship_context(self, avatar_id: str) -> Dict[str, Any]:
        """
        Get comprehensive relationship context for avatar
        
        Returns:
        - relationship_map: Dict of friend_id -> relationship_data
        - relationship_types: Dict of friend_id -> type (close_friend, friend, etc.)
        - relationship_trends: Dict of friend_id -> trend (strengthening, weakening, stable)
        - relationship_history: Dict of friend_id -> history snapshots
        """
        try:
            cache_key = f"relationship_context_{avatar_id}"
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
                    "relationship_map": {},
                    "relationship_types": {},
                    "relationship_trends": {},
                    "relationship_history": {}
                }
                self.cache[cache_key] = (result, datetime.now(timezone.utc))
                return result
            
            # Calculate relationship data for each friend
            relationship_map = {}
            relationship_types = {}
            
            for friend_id in friend_ids:
                # Get relationship strength
                strength_data = await self.perceive_relationship_strength(avatar_id, friend_id)
                relationship_map[friend_id] = strength_data
                
                # Classify relationship type
                strength = strength_data.get('strength_score', 0.0)
                if strength > 0.7:
                    relationship_types[friend_id] = "close_friend"
                elif strength > 0.4:
                    relationship_types[friend_id] = "friend"
                elif strength > 0.2:
                    relationship_types[friend_id] = "acquaintance"
                else:
                    relationship_types[friend_id] = "new_connection"
            
            # Calculate relationship trends (simplified - would need history)
            # For now, assume stable if recent interactions, weakening if not
            relationship_trends = {}
            for friend_id, rel_data in relationship_map.items():
                days_ago = rel_data.get('last_interaction_days_ago')
                if days_ago is None:
                    relationship_trends[friend_id] = "new"
                elif days_ago <= 7:
                    relationship_trends[friend_id] = "strengthening"
                elif days_ago <= 30:
                    relationship_trends[friend_id] = "stable"
                else:
                    relationship_trends[friend_id] = "weakening"
            
            # Relationship history (simplified - would need to track over time)
            relationship_history = {}  # TODO: Implement history tracking
            
            result = {
                "relationship_map": relationship_map,
                "relationship_types": relationship_types,
                "relationship_trends": relationship_trends,
                "relationship_history": relationship_history,
                "total_relationships": len(friend_ids),
                "close_friends_count": sum(1 for t in relationship_types.values() if t == "close_friend"),
                "friends_count": sum(1 for t in relationship_types.values() if t == "friend")
            }
            
            self.cache[cache_key] = (result, datetime.now(timezone.utc))
            return result
            
        except Exception as e:
            logger.error(f"Error perceiving relationship context for {avatar_id}: {e}")
            return {
                "relationship_map": {},
                "relationship_types": {},
                "relationship_trends": {},
                "relationship_history": {},
                "total_relationships": 0,
                "close_friends_count": 0,
                "friends_count": 0
            }
    
    async def perceive_social_status(self, avatar_id: str) -> Dict[str, Any]:
        """
        Perceive avatar's social status in the network
        
        Returns:
        - social_standing: Float (0.0-1.0) - overall social standing
        - influence_score: Float (0.0-1.0) - influence in network
        - engagement_metrics: Dict of engagement statistics
        - popularity_trends: Dict of popularity trends
        """
        try:
            cache_key = f"social_status_{avatar_id}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if (datetime.now(timezone.utc) - cached_time).total_seconds() < self.cache_ttl:
                    return cached_data
            
            # Get avatar's posts
            since_time = datetime.now(timezone.utc) - timedelta(days=30)
            avatar_posts = await self.db.posts.find({
                "user_id": avatar_id,
                "created_at": {"$gte": since_time.isoformat()}
            }).sort([("created_at", -1)]).limit(10).to_list(10)  # Reduced for performance
            
            # Calculate engagement metrics
            total_likes = sum(post.get('likes', 0) for post in avatar_posts)
            total_comments = sum(post.get('comment_count', 0) for post in avatar_posts)
            total_posts = len(avatar_posts)
            
            avg_likes_per_post = total_likes / total_posts if total_posts > 0 else 0
            avg_comments_per_post = total_comments / total_posts if total_posts > 0 else 0
            
            # Get friends count
            from services.friend_service import FriendService
            friend_service = FriendService(self.db)
            friends = await friend_service.get_friends(avatar_id)
            friend_count = len(friends)
            
            # Calculate influence score
            # Based on engagement rate and network size
            engagement_rate = (total_likes + total_comments) / total_posts if total_posts > 0 else 0
            # Normalize: assume 20+ engagement per post = high influence
            influence_from_engagement = min(engagement_rate / 20.0, 1.0)
            
            # Network size factor (normalized)
            influence_from_network = min(friend_count / 100.0, 1.0)  # 100+ friends = max
            
            influence_score = (influence_from_engagement * 0.7 + influence_from_network * 0.3)
            
            # Calculate social standing
            # Combination of influence, engagement, and network position
            social_standing = (
                influence_score * 0.5 +
                min(engagement_rate / 10.0, 1.0) * 0.3 +
                min(friend_count / 50.0, 1.0) * 0.2
            )
            
            # Popularity trends (simplified - compare last 7 days vs previous 7 days)
            recent_posts = [p for p in avatar_posts if self._is_recent(p.get('created_at'), days=7)]
            older_posts = [p for p in avatar_posts if not self._is_recent(p.get('created_at'), days=7)]
            
            recent_engagement = sum(p.get('likes', 0) + p.get('comment_count', 0) for p in recent_posts)
            older_engagement = sum(p.get('likes', 0) + p.get('comment_count', 0) for p in older_posts)
            
            if older_engagement > 0:
                trend_ratio = recent_engagement / older_engagement
                if trend_ratio > 1.2:
                    popularity_trend = "rising"
                elif trend_ratio < 0.8:
                    popularity_trend = "declining"
                else:
                    popularity_trend = "stable"
            else:
                popularity_trend = "new" if recent_engagement > 0 else "inactive"
            
            result = {
                "social_standing": round(social_standing, 3),
                "influence_score": round(influence_score, 3),
                "engagement_metrics": {
                    "total_likes": total_likes,
                    "total_comments": total_comments,
                    "total_posts": total_posts,
                    "avg_likes_per_post": round(avg_likes_per_post, 2),
                    "avg_comments_per_post": round(avg_comments_per_post, 2),
                    "engagement_rate": round(engagement_rate, 2)
                },
                "popularity_trends": {
                    "trend": popularity_trend,
                    "recent_engagement": recent_engagement,
                    "older_engagement": older_engagement
                },
                "friend_count": friend_count
            }
            
            self.cache[cache_key] = (result, datetime.now(timezone.utc))
            return result
            
        except Exception as e:
            logger.error(f"Error perceiving social status for {avatar_id}: {e}")
            return {
                "social_standing": 0.0,
                "influence_score": 0.0,
                "engagement_metrics": {},
                "popularity_trends": {},
                "friend_count": 0
            }
    
    def _is_recent(self, timestamp: Any, days: int = 7) -> bool:
        """Check if timestamp is within last N days"""
        if not timestamp:
            return False
        
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            days_ago = (datetime.now(timezone.utc) - dt).days
            return days_ago <= days
        except Exception:
            return False

