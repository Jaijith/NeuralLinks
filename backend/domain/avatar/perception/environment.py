"""
Environment Perception
Perceives broader environment variables
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


class EnvironmentPerception:
    """
    Perceives environment context
    
    Provides:
    - Temporal context (time of day, day of week, events)
    - Content trends
    - Platform state
    """
    
    def __init__(self):
        # No database needed for basic environment perception
        pass
    
    async def perceive_temporal_context(self) -> Dict[str, Any]:
        """
        Get temporal context
        
        Returns:
        - time_of_day: str (morning, afternoon, evening, night)
        - day_of_week: str (monday, tuesday, etc.)
        - hour: int (0-23)
        - is_weekend: bool
        - special_events: List of special events/holidays
        """
        try:
            now = datetime.now(timezone.utc)
            hour = now.hour
            day_of_week = now.strftime('%A').lower()
            
            # Determine time of day
            if 5 <= hour < 12:
                time_of_day = "morning"
            elif 12 <= hour < 17:
                time_of_day = "afternoon"
            elif 17 <= hour < 22:
                time_of_day = "evening"
            else:
                time_of_day = "night"
            
            # Check if weekend
            is_weekend = day_of_week in ['saturday', 'sunday']
            
            # Check for special events/holidays (simplified)
            special_events = self._detect_special_events(now)
            
            return {
                "time_of_day": time_of_day,
                "day_of_week": day_of_week,
                "hour": hour,
                "is_weekend": is_weekend,
                "special_events": special_events,
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error perceiving temporal context: {e}")
            return {
                "time_of_day": "unknown",
                "day_of_week": "unknown",
                "hour": 12,
                "is_weekend": False,
                "special_events": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def perceive_content_trends(
        self,
        avatar_id: str,
        db: Any  # AsyncIOMotorDatabase - passed from engine
    ) -> Dict[str, Any]:
        """
        Detect content trends in the network
        
        Returns:
        - trending_topics: List of trending topics
        - popular_content_types: List of popular content types
        - content_engagement_patterns: Dict of engagement patterns
        - topic_lifecycle: Dict of topic -> lifecycle stage
        """
        try:
            # Get recent posts from network (last 7 days)
            since_time = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Get posts from friends and extended network
            from services.friend_service import FriendService
            friend_service = FriendService(db)
            friends = await friend_service.get_friends(avatar_id)
            friend_ids = [f['id'] for f in friends]
            
            if not friend_ids:
                return {
                    "trending_topics": [],
                    "popular_content_types": [],
                    "content_engagement_patterns": {},
                    "topic_lifecycle": {}
                }
            
            # Get recent posts
            posts_cursor = db.posts.find({
                "user_id": {"$in": friend_ids},
                "created_at": {"$gte": since_time.isoformat()}
            }).sort([("created_at", -1)])
            
            recent_posts = await posts_cursor.to_list(500)
            
            # Extract trending topics
            trending_topics = self._extract_trending_topics(recent_posts)
            
            # Analyze content types
            content_types = {}
            for post in recent_posts:
                post_type = post.get('post_type', 'general')
                has_image = post.get('has_image', False) or post.get('image_url')
                
                if has_image:
                    content_type = "image"
                elif len(post.get('text', '') or post.get('content', '')) > 200:
                    content_type = "long_text"
                else:
                    content_type = "short_text"
                
                content_types[content_type] = content_types.get(content_type, 0) + 1
            
            # Sort by frequency
            popular_content_types = sorted(
                content_types.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            popular_content_types = [ct[0] for ct in popular_content_types]
            
            # Engagement patterns
            engagement_by_type = {}
            for post in recent_posts:
                post_type = post.get('post_type', 'general')
                engagement = post.get('likes', 0) + post.get('comment_count', 0)
                
                if post_type not in engagement_by_type:
                    engagement_by_type[post_type] = []
                engagement_by_type[post_type].append(engagement)
            
            content_engagement_patterns = {
                post_type: {
                    "avg_engagement": sum(engagements) / len(engagements) if engagements else 0,
                    "max_engagement": max(engagements) if engagements else 0,
                    "post_count": len(engagements)
                }
                for post_type, engagements in engagement_by_type.items()
            }
            
            # Topic lifecycle (simplified - would need time-series analysis)
            topic_lifecycle = {}
            for topic in trending_topics[:10]:  # Top 10 topics
                # Simple heuristic: if topic appears in recent posts, it's "emerging" or "peak"
                topic_lifecycle[topic] = "peak"  # TODO: Implement proper lifecycle detection
            
            return {
                "trending_topics": trending_topics,
                "popular_content_types": popular_content_types,
                "content_engagement_patterns": content_engagement_patterns,
                "topic_lifecycle": topic_lifecycle,
                "total_posts_analyzed": len(recent_posts)
            }
            
        except Exception as e:
            logger.error(f"Error perceiving content trends for {avatar_id}: {e}")
            return {
                "trending_topics": [],
                "popular_content_types": [],
                "content_engagement_patterns": {},
                "topic_lifecycle": {}
            }
    
    async def perceive_platform_state(
        self,
        db: Any  # AsyncIOMotorDatabase
    ) -> Dict[str, Any]:
        """
        Perceive overall platform state
        
        Returns:
        - overall_activity_level: Float (0.0-1.0)
        - network_health_metrics: Dict of health metrics
        - system_wide_trends: Dict of system trends
        """
        try:
            # Get activity in last 24 hours
            since_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Count recent posts
            recent_posts_count = await db.posts.count_documents({
                "created_at": {"$gte": since_time.isoformat()}
            })
            
            # Count active users (users who posted in last 24h)
            active_users = await db.posts.distinct(
                "user_id",
                {"created_at": {"$gte": since_time.isoformat()}}
            )
            active_user_count = len(active_users)
            
            # Count total users
            total_users = await db.users.count_documents({})
            
            # Calculate activity level
            # Assume max 1000 posts per day = high activity
            activity_from_posts = min(recent_posts_count / 1000.0, 1.0)
            # Assume 50% active users = high activity
            activity_from_users = min(active_user_count / max(total_users * 0.5, 1), 1.0)
            
            overall_activity_level = (activity_from_posts * 0.6 + activity_from_users * 0.4)
            
            # Network health metrics
            # Calculate average engagement
            recent_posts = await db.posts.find({
                "created_at": {"$gte": since_time.isoformat()}
            }).limit(1000).to_list(1000)
            
            if recent_posts:
                avg_engagement = sum(
                    p.get('likes', 0) + p.get('comment_count', 0)
                    for p in recent_posts
                ) / len(recent_posts)
            else:
                avg_engagement = 0
            
            # Calculate friendship growth
            new_friendships = await db.friendships.count_documents({
                "created_at": {"$gte": since_time.isoformat()}
            })
            
            network_health_metrics = {
                "avg_engagement_per_post": round(avg_engagement, 2),
                "new_friendships_24h": new_friendships,
                "active_users_24h": active_user_count,
                "total_posts_24h": recent_posts_count
            }
            
            # System-wide trends (simplified)
            system_wide_trends = {
                "activity_trend": "stable",  # TODO: Compare with previous period
                "engagement_trend": "stable",
                "growth_trend": "stable"
            }
            
            return {
                "overall_activity_level": round(overall_activity_level, 3),
                "network_health_metrics": network_health_metrics,
                "system_wide_trends": system_wide_trends
            }
            
        except Exception as e:
            logger.error(f"Error perceiving platform state: {e}")
            return {
                "overall_activity_level": 0.5,
                "network_health_metrics": {},
                "system_wide_trends": {}
            }
    
    def _detect_special_events(self, now: datetime) -> List[str]:
        """
        Detect special events/holidays (simplified)
        
        TODO: Can be enhanced with holiday calendar
        """
        events = []
        
        # Check for common holidays (simplified)
        month = now.month
        day = now.day
        
        # New Year
        if month == 1 and day == 1:
            events.append("new_year")
        
        # Valentine's Day
        if month == 2 and day == 14:
            events.append("valentines_day")
        
        # Christmas
        if month == 12 and day == 25:
            events.append("christmas")
        
        # Add more holidays as needed
        
        return events
    
    def _extract_trending_topics(self, posts: List[Dict]) -> List[str]:
        """
        Extract trending topics from posts
        Simple keyword-based approach
        """
        word_count = {}
        
        for post in posts:
            text = post.get('text', '') or post.get('content', '')
            if not text:
                continue
            
            words = text.lower().split()
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
                'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
                'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his',
                'her', 'its', 'our', 'their', 'what', 'when', 'where', 'why', 'how'
            }
            
            for word in words:
                word = word.strip('.,!?;:()[]{}"\'-')
                if len(word) > 3 and word not in stop_words:
                    word_count[word] = word_count.get(word, 0) + 1
        
        trending = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]
        return [word for word, count in trending]

