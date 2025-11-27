"""
Action Memory
Remembers recent actions and learns from outcomes
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ActionMemory:
    """
    Remembers and learns from past actions
    
    Features:
    - Tracks recent actions with outcomes
    - Identifies action patterns (what works, what doesn't)
    - Prevents repetitive actions
    - Learns preferences from success/failure
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def record_action(
        self, 
        avatar_id: str, 
        action_type: str, 
        action_details: Dict[str, Any],
        outcome: Dict[str, Any]
    ):
        """
        Record an action with its outcome for learning
        
        Args:
            avatar_id: The avatar who performed the action
            action_type: Type of action (create_post, like_post, message_friend, etc.)
            action_details: Details of the action (target_user, content, etc.)
            outcome: Result of the action (success, engagement, etc.)
        """
        try:
            memory_record = {
                "avatar_id": avatar_id,
                "action_type": action_type,
                "action_details": action_details,
                "outcome": outcome,
                "success": outcome.get("success", False),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "engagement_score": self._calculate_engagement_score(outcome)
            }
            
            await self.db.avatar_action_memory.insert_one(memory_record)
            
            # Invalidate cache
            cache_key = f"action_memory_{avatar_id}"
            if cache_key in self.cache:
                del self.cache[cache_key]
                
            logger.debug(f"Recorded action memory: {action_type} for {avatar_id}")
            
        except Exception as e:
            logger.error(f"Error recording action memory: {e}")
    
    def _calculate_engagement_score(self, outcome: Dict[str, Any]) -> float:
        """Calculate engagement score from outcome"""
        score = 0.0
        
        if outcome.get("success"):
            score += 0.5
        
        # Post engagement
        if "likes_received" in outcome:
            score += min(outcome["likes_received"] * 0.1, 0.3)
        if "comments_received" in outcome:
            score += min(outcome["comments_received"] * 0.15, 0.3)
        
        # Message engagement
        if outcome.get("message_read"):
            score += 0.2
        if outcome.get("reply_received"):
            score += 0.4
        
        # Friend request
        if outcome.get("request_accepted"):
            score += 0.5
        
        return min(score, 1.0)
    
    async def get_recent_actions(
        self, 
        avatar_id: str, 
        limit: int = 20,
        action_type: Optional[str] = None,
        hours_ago: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get recent actions for an avatar
        
        Args:
            avatar_id: The avatar to query
            limit: Maximum number of actions to return
            action_type: Filter by action type (optional)
            hours_ago: How far back to look
        """
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
            
            query = {
                "avatar_id": avatar_id,
                "timestamp": {"$gte": cutoff}
            }
            
            if action_type:
                query["action_type"] = action_type
            
            actions = await self.db.avatar_action_memory.find(
                query,
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit).to_list(limit)
            
            return actions
            
        except Exception as e:
            logger.error(f"Error getting recent actions: {e}")
            return []
    
    async def get_action_patterns(self, avatar_id: str) -> Dict[str, Any]:
        """
        Analyze action patterns to understand what works
        
        Returns:
            Dictionary with action statistics and success rates
        """
        try:
            # Check cache
            cache_key = f"action_patterns_{avatar_id}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if (datetime.now(timezone.utc) - cached_time).total_seconds() < self.cache_ttl:
                    return cached_data
            
            # Get last 7 days of actions
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            
            actions = await self.db.avatar_action_memory.find(
                {"avatar_id": avatar_id, "timestamp": {"$gte": cutoff}},
                {"_id": 0}
            ).to_list(500)
            
            # Analyze patterns
            patterns = {
                "total_actions": len(actions),
                "action_counts": defaultdict(int),
                "success_rates": {},
                "avg_engagement": {},
                "best_performing": None,
                "worst_performing": None,
                "recent_repetition": {}
            }
            
            action_stats = defaultdict(lambda: {"count": 0, "successes": 0, "total_engagement": 0.0})
            
            for action in actions:
                action_type = action.get("action_type", "unknown")
                patterns["action_counts"][action_type] += 1
                
                stats = action_stats[action_type]
                stats["count"] += 1
                if action.get("success"):
                    stats["successes"] += 1
                stats["total_engagement"] += action.get("engagement_score", 0.0)
            
            # Calculate rates
            for action_type, stats in action_stats.items():
                if stats["count"] > 0:
                    patterns["success_rates"][action_type] = stats["successes"] / stats["count"]
                    patterns["avg_engagement"][action_type] = stats["total_engagement"] / stats["count"]
            
            # Find best/worst performing
            if patterns["avg_engagement"]:
                patterns["best_performing"] = max(
                    patterns["avg_engagement"].items(), 
                    key=lambda x: x[1]
                )[0]
                patterns["worst_performing"] = min(
                    patterns["avg_engagement"].items(), 
                    key=lambda x: x[1]
                )[0]
            
            # Check for recent repetition (last hour)
            hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            recent_actions = [a for a in actions if a.get("timestamp", "") >= hour_ago]
            for action in recent_actions:
                action_type = action.get("action_type", "unknown")
                patterns["recent_repetition"][action_type] = \
                    patterns["recent_repetition"].get(action_type, 0) + 1
            
            # Convert defaultdicts to regular dicts
            patterns["action_counts"] = dict(patterns["action_counts"])
            
            # Cache result
            self.cache[cache_key] = (patterns, datetime.now(timezone.utc))
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error getting action patterns: {e}")
            return {
                "total_actions": 0,
                "action_counts": {},
                "success_rates": {},
                "avg_engagement": {},
                "best_performing": None,
                "worst_performing": None,
                "recent_repetition": {}
            }
    
    async def should_avoid_action(
        self, 
        avatar_id: str, 
        action_type: str,
        cooldown_minutes: int = 30
    ) -> tuple[bool, str]:
        """
        Check if an action should be avoided
        
        Returns:
            Tuple of (should_avoid: bool, reason: str)
        """
        try:
            # Check if action was performed recently
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)).isoformat()
            
            recent_count = await self.db.avatar_action_memory.count_documents({
                "avatar_id": avatar_id,
                "action_type": action_type,
                "timestamp": {"$gte": cutoff}
            })
            
            if recent_count >= 3:
                return True, f"Already performed {action_type} {recent_count} times in last {cooldown_minutes} minutes"
            
            # Check if action has been failing
            patterns = await self.get_action_patterns(avatar_id)
            success_rate = patterns.get("success_rates", {}).get(action_type, 1.0)
            
            if success_rate < 0.2 and patterns.get("action_counts", {}).get(action_type, 0) >= 5:
                return True, f"{action_type} has very low success rate ({success_rate:.0%})"
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error checking action avoidance: {e}")
            return False, ""
    
    async def get_successful_topics(self, avatar_id: str, limit: int = 10) -> List[str]:
        """
        Get topics/themes from successful posts
        
        Returns list of topics that have performed well
        """
        try:
            # Get successful create_post actions
            successful_posts = await self.db.avatar_action_memory.find({
                "avatar_id": avatar_id,
                "action_type": "create_post",
                "success": True,
                "engagement_score": {"$gte": 0.3}
            }, {"_id": 0}).sort("engagement_score", -1).limit(limit).to_list(limit)
            
            topics = []
            for post in successful_posts:
                details = post.get("action_details", {})
                if "topic" in details:
                    topics.append(details["topic"])
                if "content" in details:
                    # Extract key words (simple approach)
                    content = details["content"][:100]
                    topics.append(content)
            
            return topics
            
        except Exception as e:
            logger.error(f"Error getting successful topics: {e}")
            return []
    
    async def get_interaction_history(
        self, 
        avatar_id: str, 
        target_user_id: str
    ) -> Dict[str, Any]:
        """
        Get history of interactions with a specific user
        """
        try:
            interactions = await self.db.avatar_action_memory.find({
                "avatar_id": avatar_id,
                "action_details.target_user_id": target_user_id
            }, {"_id": 0}).sort("timestamp", -1).limit(20).to_list(20)
            
            summary = {
                "total_interactions": len(interactions),
                "action_types": defaultdict(int),
                "last_interaction": None,
                "positive_outcomes": 0,
                "relationship_trend": "neutral"
            }
            
            for interaction in interactions:
                action_type = interaction.get("action_type", "unknown")
                summary["action_types"][action_type] += 1
                
                if interaction.get("engagement_score", 0) >= 0.3:
                    summary["positive_outcomes"] += 1
            
            if interactions:
                summary["last_interaction"] = interactions[0].get("timestamp")
            
            # Determine relationship trend
            if summary["total_interactions"] > 0:
                positive_ratio = summary["positive_outcomes"] / summary["total_interactions"]
                if positive_ratio >= 0.6:
                    summary["relationship_trend"] = "positive"
                elif positive_ratio <= 0.3:
                    summary["relationship_trend"] = "negative"
            
            summary["action_types"] = dict(summary["action_types"])
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting interaction history: {e}")
            return {
                "total_interactions": 0,
                "action_types": {},
                "last_interaction": None,
                "positive_outcomes": 0,
                "relationship_trend": "neutral"
            }

