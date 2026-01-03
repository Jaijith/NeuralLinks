"""
Evaluation MCP Tools
Tools for scoring and analyzing profile compatibility
"""

import logging
from typing import Dict, List, Any
from .tools import WorkflowBaseTool

logger = logging.getLogger(__name__)


class ScoreCompatibilityTool(WorkflowBaseTool):
    """Calculate compatibility score between two users"""
    
    name = "score_compatibility"
    description = "Calculate detailed compatibility score between two users"
    
    schema = {
        "type": "object",
        "properties": {
            "target_user_id": {
                "type": "string",
                "description": "User to score compatibility with"
            },
            "weights": {
                "type": "object",
                "description": "Custom weights for scoring factors",
                "properties": {
                    "interest_overlap": {"type": "number"},
                    "trait_compatibility": {"type": "number"},
                    "activity_alignment": {"type": "number"},
                    "mutual_connections": {"type": "number"}
                }
            }
        },
        "required": ["target_user_id"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        target_id = kwargs.get("target_user_id")
        weights = kwargs.get("weights", {
            "interest_overlap": 0.40,
            "trait_compatibility": 0.25,
            "activity_alignment": 0.15,
            "mutual_connections": 0.20
        })
        
        logger.info(f"📊 Scoring compatibility: {avatar_id[:8]} vs {target_id[:8]}")
        
        # Calculate each factor
        interest_score = await self._calculate_interest_overlap(avatar_id, target_id)
        trait_score = await self._calculate_trait_compatibility(avatar_id, target_id)
        activity_score = await self._calculate_activity_alignment(avatar_id, target_id)
        connection_score = await self._calculate_mutual_connections(avatar_id, target_id)
        
        # Weighted total
        total_score = (
            interest_score * weights["interest_overlap"] +
            trait_score * weights["trait_compatibility"] +
            activity_score * weights["activity_alignment"] +
            connection_score * weights["mutual_connections"]
        )
        
        # Calculate confidence (higher when we have more data)
        confidence = self._calculate_confidence(interest_score, trait_score, activity_score)
        
        return {
            "success": True,
            "target_user_id": target_id,
            "total_score": round(total_score * 100),
            "breakdown": {
                "interest_overlap": round(interest_score, 3),
                "trait_compatibility": round(trait_score, 3),
                "activity_alignment": round(activity_score, 3),
                "mutual_connections": round(connection_score, 3)
            },
            "confidence": round(confidence, 2)
        }
    
    async def _calculate_interest_overlap(self, user1: str, user2: str) -> float:
        interests1 = set(await self._get_interests(user1))
        interests2 = set(await self._get_interests(user2))
        
        if not interests1 or not interests2:
            return 0.5  # Neutral if no data
        
        overlap = interests1 & interests2
        union = interests1 | interests2
        
        return len(overlap) / len(union) if union else 0
    
    async def _calculate_trait_compatibility(self, user1: str, user2: str) -> float:
        traits1 = await self._get_traits(user1)
        traits2 = await self._get_traits(user2)
        
        if not traits1 or not traits2:
            return 0.5
        
        overlap = set(traits1) & set(traits2)
        return len(overlap) / max(len(traits1), len(traits2))
    
    async def _calculate_activity_alignment(self, user1: str, user2: str) -> float:
        user1_data = await self.db.users.find_one({"id": user1})
        user2_data = await self.db.users.find_one({"id": user2})
        
        if not user1_data or not user2_data:
            return 0.5
        
        level1 = user1_data.get("avatar_activity_level", "medium")
        level2 = user2_data.get("avatar_activity_level", "medium")
        
        levels = {"low": 1, "hypo": 1, "medium": 2, "high": 3}
        diff = abs(levels.get(level1, 2) - levels.get(level2, 2))
        
        return 1.0 - (diff * 0.3)
    
    async def _calculate_mutual_connections(self, user1: str, user2: str) -> float:
        friends1 = set(await self._get_friend_ids(user1))
        friends2 = set(await self._get_friend_ids(user2))
        
        mutual = friends1 & friends2
        
        if not friends1 and not friends2:
            return 0.5
        
        return min(1.0, len(mutual) / 10)  # Cap at 10 mutual friends = 1.0
    
    def _calculate_confidence(self, interest_score: float, trait_score: float, activity_score: float) -> float:
        # Higher confidence when we have good data (not default 0.5 values)
        non_default_scores = sum(1 for s in [interest_score, trait_score, activity_score] if s != 0.5)
        return 0.3 + (non_default_scores * 0.2)


class AnalyzeProfileTool(WorkflowBaseTool):
    """Get detailed analysis of a user profile"""
    
    name = "analyze_profile"
    description = "Analyze a user profile for matchmaking insights"
    
    schema = {
        "type": "object",
        "properties": {
            "target_user_id": {
                "type": "string",
                "description": "User ID to analyze"
            }
        },
        "required": ["target_user_id"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        target_id = kwargs.get("target_user_id")
        
        # Get user data
        user = await self.db.users.find_one({"id": target_id})
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Get interests and traits from knowledge graph
        interests = await self._get_interests(target_id)
        traits = await self._get_traits(target_id)
        
        # Get recent activity
        recent_posts = await self.db.posts.find(
            {"user_id": target_id}
        ).sort("created_at", -1).limit(5).to_list(5)
        
        # Get friend count
        friend_count = await self.db.friendships.count_documents({
            "$or": [
                {"user_id": target_id, "status": "accepted"},
                {"friend_id": target_id, "status": "accepted"}
            ]
        })
        
        return {
            "success": True,
            "profile": {
                "user_id": target_id,
                "avatar_name": user.get("avatar_name"),
                "real_name": user.get("name"),
                "archetype": user.get("avatar_archetype"),
                "activity_level": user.get("avatar_activity_level", "medium"),
                "bio": user.get("avatar_bio", "")[:200],
                "interests": interests[:15],
                "traits": traits[:10],
                "friend_count": friend_count,
                "recent_activity": {
                    "post_count": len(recent_posts),
                    "last_post_date": recent_posts[0].get("created_at") if recent_posts else None
                }
            }
        }


class GetSharedInterestsTool(WorkflowBaseTool):
    """Get shared interests between two users"""
    
    name = "get_shared_interests"
    description = "Find interests shared between the avatar and a target user"
    
    schema = {
        "type": "object",
        "properties": {
            "target_user_id": {
                "type": "string",
                "description": "User to compare interests with"
            }
        },
        "required": ["target_user_id"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        target_id = kwargs.get("target_user_id")
        
        avatar_interests = set(await self._get_interests(avatar_id))
        target_interests = set(await self._get_interests(target_id))
        
        shared = avatar_interests & target_interests
        avatar_unique = avatar_interests - target_interests
        target_unique = target_interests - avatar_interests
        
        union = avatar_interests | target_interests
        overlap_percentage = (len(shared) / len(union) * 100) if union else 0
        
        return {
            "success": True,
            "shared_interests": list(shared),
            "avatar_unique": list(avatar_unique)[:10],
            "target_unique": list(target_unique)[:10],
            "overlap_percentage": round(overlap_percentage, 1)
        }

