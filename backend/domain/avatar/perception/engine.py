"""
Perception Engine
Orchestrates all perception modules with interest-aware filtering
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from .social_network import SocialNetworkPerception
from .relationship import RelationshipPerception
from .environment import EnvironmentPerception
import logging

logger = logging.getLogger(__name__)


class PerceptionEngine:
    """
    Orchestrates all perception modules with interest-aware filtering
    
    Provides unified perception data combining:
    - Social network activity
    - Relationship context
    - Environment state
    - Interest-filtered content (NEW)
    
    The avatar perceives the world through the lens of their interests,
    making content more relevant and decisions more personalized.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.social = SocialNetworkPerception(db)
        self.relationship = RelationshipPerception(db)
        self.environment = EnvironmentPerception()
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 minutes
        self._interests_cache: Dict[str, tuple] = {}  # avatar_id -> (interests, timestamp)
    
    async def perceive_all(self, avatar_id: str) -> Dict[str, Any]:
        """
        Perceive all environment data for avatar
        
        Returns comprehensive perception data combining all modules:
        - social_network: Friend activity, network trends, direct interactions
        - relationships: Relationship map, types, trends, social status
        - environment: Temporal context, content trends, platform state
        """
        try:
            # Check cache
            cache_key = f"perception_all_{avatar_id}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if (datetime.now(timezone.utc) - cached_time).total_seconds() < self.cache_ttl:
                    return cached_data
            
            # Perceive all aspects in parallel (where possible)
            # Note: Some perceptions depend on others, so we do them sequentially for now
            
            # 1. Social network perception
            social_data = await self.social.perceive_friend_activity(avatar_id)
            connection_circle = await self.social.perceive_connection_circle(avatar_id)
            direct_interactions = await self.social.perceive_direct_interactions(avatar_id)
            
            # 2. Relationship perception
            relationship_context = await self.relationship.perceive_relationship_context(avatar_id)
            social_status = await self.relationship.perceive_social_status(avatar_id)
            
            # 3. Environment perception
            temporal_context = await self.environment.perceive_temporal_context()
            content_trends = await self.environment.perceive_content_trends(avatar_id, self.db)
            platform_state = await self.environment.perceive_platform_state(self.db)
            
            # Combine all perception data
            perception_data = {
                "avatar_id": avatar_id,
                "perceived_at": datetime.now(timezone.utc).isoformat(),
                
                "social_network": {
                    "friend_activity": social_data,
                    "connection_circle": connection_circle,
                    "direct_interactions": direct_interactions
                },
                
                "relationships": {
                    "context": relationship_context,
                    "social_status": social_status
                },
                
                "environment": {
                    "temporal": temporal_context,
                    "content_trends": content_trends,
                    "platform_state": platform_state
                },
                
                # Convenience fields for easy access
                "friend_activity_level": social_data.get("friend_activity_level", 0.0),
                "unread_messages": direct_interactions.get("unread_messages", 0),
                "pending_friend_requests": direct_interactions.get("pending_friend_requests", 0),
                "recent_posts": social_data.get("recent_posts", []),
                "relationship_map": relationship_context.get("relationship_map", {}),
                "relationship_types": relationship_context.get("relationship_types", {}),
                "time_of_day": temporal_context.get("time_of_day", "unknown"),
                "is_weekend": temporal_context.get("is_weekend", False),
                "trending_topics": content_trends.get("trending_topics", []),
                "platform_activity_level": platform_state.get("overall_activity_level", 0.5)
            }
            
            # Cache result
            self.cache[cache_key] = (perception_data, datetime.now(timezone.utc))
            
            return perception_data
            
        except Exception as e:
            logger.error(f"Error in perception engine for {avatar_id}: {e}", exc_info=True)
            # Return minimal safe structure
            return {
                "avatar_id": avatar_id,
                "perceived_at": datetime.now(timezone.utc).isoformat(),
                "social_network": {
                    "friend_activity": {"friend_activity_level": 0.0, "recent_posts": []},
                    "connection_circle": {"extended_network_activity": 0.0},
                    "direct_interactions": {"unread_messages": 0, "pending_friend_requests": 0}
                },
                "relationships": {
                    "context": {"relationship_map": {}, "relationship_types": {}},
                    "social_status": {"social_standing": 0.0, "influence_score": 0.0}
                },
                "environment": {
                    "temporal": {"time_of_day": "unknown"},
                    "content_trends": {"trending_topics": []},
                    "platform_state": {"overall_activity_level": 0.5}
                },
                "friend_activity_level": 0.0,
                "unread_messages": 0,
                "pending_friend_requests": 0,
                "recent_posts": [],
                "relationship_map": {},
                "relationship_types": {},
                "time_of_day": "unknown",
                "is_weekend": False,
                "trending_topics": [],
                "platform_activity_level": 0.5
            }
    
    async def clear_cache(self, avatar_id: Optional[str] = None):
        """
        Clear perception cache
        
        Args:
            avatar_id: If provided, clear only for this avatar. Otherwise clear all.
        """
        if avatar_id:
            keys_to_remove = [k for k in self.cache.keys() if avatar_id in k]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.cache),
            "cache_keys": list(self.cache.keys())
        }
    
    async def _get_avatar_interests(self, avatar_id: str) -> List[str]:
        """
        Get avatar's interests from knowledge graph.

        Dual-Memory Architecture: sorts by salience (temporal relevance),
        falls back to strength, and excludes pending nodes.
        """
        try:
            if avatar_id in self._interests_cache:
                interests, cached_time = self._interests_cache[avatar_id]
                if (datetime.now(timezone.utc) - cached_time).total_seconds() < 600:
                    return interests

            nodes = await self.db.graph_nodes.find(
                {
                    "user_id": avatar_id,
                    "node_type": "interest",
                    "status": {"$ne": "pending"},
                },
                {"_id": 0, "label": 1, "salience": 1, "strength": 1,
                 "properties": 1}
            ).sort("salience", -1).limit(20).to_list(20)

            # Secondary sort: nodes without salience fall back to strength
            def sort_key(n):
                sal = n.get("salience")
                if sal is not None:
                    return sal
                s = n.get("strength")
                if s is not None:
                    return s
                return n.get("properties", {}).get("strength", 0.5)

            nodes.sort(key=sort_key, reverse=True)
            interests = [node["label"].lower() for node in nodes]

            self._interests_cache[avatar_id] = (interests, datetime.now(timezone.utc))
            return interests

        except Exception as e:
            logger.error(f"Error getting avatar interests: {e}")
            return []
    
    async def perceive_with_interests(self, avatar_id: str) -> Dict[str, Any]:
        """
        Perceive environment through the lens of avatar's interests
        
        This enhanced perception:
        - Scores posts by relevance to avatar's interests
        - Identifies interest-aligned opportunities
        - Highlights content the avatar would find engaging
        """
        try:
            # Get base perception
            base_perception = await self.perceive_all(avatar_id)
            
            # Get avatar's interests
            interests = await self._get_avatar_interests(avatar_id)
            
            if not interests:
                # No interests to filter by
                base_perception["interest_perception"] = {
                    "relevant_posts": [],
                    "interest_aligned_users": [],
                    "trending_interest_topics": [],
                    "interest_match_score": 0.0
                }
                return base_perception
            
            # Score recent posts by interest relevance
            recent_posts = base_perception.get("recent_posts", [])
            scored_posts = []
            
            for post in recent_posts:
                content = (post.get("content", "") or "").lower()
                
                # Calculate interest match score
                matching_interests = []
                for interest in interests:
                    if interest in content:
                        matching_interests.append(interest)
                
                relevance_score = len(matching_interests) / max(len(interests), 1)
                
                scored_posts.append({
                    "post_id": post.get("id"),
                    "user_id": post.get("user_id"),
                    "content_preview": content[:100],
                    "relevance_score": relevance_score,
                    "matching_interests": matching_interests
                })
            
            # Sort by relevance
            scored_posts.sort(key=lambda p: p["relevance_score"], reverse=True)
            
            # Find interest-aligned users (friends with shared interests)
            interest_aligned_users = await self._find_interest_aligned_users(avatar_id, interests)
            
            # Check if trending topics match interests
            trending = base_perception.get("trending_topics", [])
            trending_matches = [t for t in trending if t.lower() in interests]
            
            # Calculate overall interest match score for the environment
            env_interest_score = 0.0
            if scored_posts:
                avg_relevance = sum(p["relevance_score"] for p in scored_posts) / len(scored_posts)
                env_interest_score = avg_relevance
            if trending_matches:
                env_interest_score += 0.2 * len(trending_matches)
            
            # Add interest perception to base perception
            base_perception["interest_perception"] = {
                "avatar_interests": interests[:10],
                "relevant_posts": scored_posts[:10],  # Top 10 most relevant
                "interest_aligned_users": interest_aligned_users,
                "trending_interest_topics": trending_matches,
                "interest_match_score": min(env_interest_score, 1.0),
                "most_active_interest": self._find_most_active_interest(scored_posts, interests)
            }
            
            return base_perception
            
        except Exception as e:
            logger.error(f"Error in interest-aware perception: {e}")
            return await self.perceive_all(avatar_id)
    
    async def _find_interest_aligned_users(
        self, 
        avatar_id: str, 
        interests: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Find users who share interests with the avatar
        """
        try:
            # Get avatar's friends
            friendships = await self.db.friendships.find({
                "$or": [
                    {"user_id": avatar_id, "status": "accepted"},
                    {"friend_id": avatar_id, "status": "accepted"}
                ]
            }).to_list(100)
            
            friend_ids = []
            for f in friendships:
                if f["user_id"] == avatar_id:
                    friend_ids.append(f["friend_id"])
                else:
                    friend_ids.append(f["user_id"])
            
            if not friend_ids:
                return []
            
            # Check each friend's interests
            aligned_users = []
            for friend_id in friend_ids[:20]:  # Limit for performance
                friend_nodes = await self.db.graph_nodes.find(
                    {"user_id": friend_id, "node_type": "interest"},
                    {"_id": 0, "label": 1}
                ).limit(20).to_list(20)
                
                friend_interests = [n["label"].lower() for n in friend_nodes]
                shared = set(interests) & set(friend_interests)
                
                if shared:
                    aligned_users.append({
                        "user_id": friend_id,
                        "shared_interests": list(shared),
                        "alignment_score": len(shared) / max(len(interests), 1)
                    })
            
            # Sort by alignment
            aligned_users.sort(key=lambda u: u["alignment_score"], reverse=True)
            
            return aligned_users[:5]  # Top 5 aligned users
            
        except Exception as e:
            logger.error(f"Error finding interest-aligned users: {e}")
            return []
    
    def _find_most_active_interest(
        self, 
        scored_posts: List[Dict], 
        interests: List[str]
    ) -> Optional[str]:
        """
        Find a DIVERSE interest to focus on — not always the same one.
        
        Uses weighted random selection among the top interests so the avatar
        doesn't obsessively post about only the strongest interest.
        Interests that appear in the feed get a boost, but all interests
        have a chance to be selected.
        """
        import random
        
        if not interests:
            return None
        
        # Count feed appearances per interest
        interest_counts = {}
        for post in scored_posts:
            for interest in post.get("matching_interests", []):
                interest_counts[interest] = interest_counts.get(interest, 0) + 1
        
        # Build weighted pool: ALL interests get a base weight,
        # feed-active interests get a small bonus (not a dominating one)
        weighted_pool = []
        for i, interest in enumerate(interests):
            # Base weight: decreasing by position (but still meaningful for all)
            # Position 0 gets weight 1.0, position 19 gets weight 0.3
            base_weight = max(0.3, 1.0 - (i * 0.035))
            # Small bonus for feed presence (capped at 0.3)
            feed_bonus = min(interest_counts.get(interest, 0) * 0.1, 0.3)
            weighted_pool.append((interest, base_weight + feed_bonus))
        
        if not weighted_pool:
            return None
        
        # Weighted random selection
        interests_list, weights = zip(*weighted_pool)
        selected = random.choices(interests_list, weights=weights, k=1)[0]
        return selected

