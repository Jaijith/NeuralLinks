"""
Episodic Memory
Stores and retrieves significant experiences and events
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging
import uuid

logger = logging.getLogger(__name__)


class EpisodicMemory:
    """
    Stores and retrieves significant experiences
    
    Features:
    - Stores meaningful events/experiences
    - Recalls relevant memories for context
    - Tracks relationship history
    - Enables learning from past experiences
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def store_experience(
        self, 
        avatar_id: str, 
        experience_type: str,
        details: Dict[str, Any],
        emotional_valence: float = 0.0,  # -1 (negative) to 1 (positive)
        significance: float = 0.5  # 0 to 1, how important this memory is
    ):
        """
        Store a significant experience/event
        
        Args:
            avatar_id: The avatar who had this experience
            experience_type: Type of experience (conversation, discovery, creation, rejection, etc.)
            details: Details of the experience
            emotional_valence: How positive/negative (-1 to 1)
            significance: How important (0 to 1)
        """
        try:
            memory = {
                "id": str(uuid.uuid4()),
                "avatar_id": avatar_id,
                "experience_type": experience_type,
                "details": details,
                "emotional_valence": emotional_valence,
                "significance": significance,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recall_count": 0,  # How many times this memory was recalled
                "last_recalled": None,
                "decay_factor": 1.0  # Memory strength (decays over time if not recalled)
            }
            
            await self.db.avatar_episodic_memory.insert_one(memory)
            logger.debug(f"Stored experience: {experience_type} for {avatar_id}")
            
        except Exception as e:
            logger.error(f"Error storing experience: {e}")
    
    async def recall_experiences(
        self, 
        avatar_id: str, 
        context: Optional[str] = None,
        experience_types: Optional[List[str]] = None,
        limit: int = 10,
        min_significance: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Recall relevant experiences for current context
        
        Args:
            avatar_id: The avatar to query
            context: Optional context to filter by (e.g., topic, user_id)
            experience_types: Filter by experience types
            limit: Maximum memories to return
            min_significance: Minimum significance threshold
        """
        try:
            query = {
                "avatar_id": avatar_id,
                "significance": {"$gte": min_significance}
            }
            
            if experience_types:
                query["experience_type"] = {"$in": experience_types}
            
            if context:
                # Search in details for context match
                query["$or"] = [
                    {"details.topic": {"$regex": context, "$options": "i"}},
                    {"details.user_id": context},
                    {"details.content": {"$regex": context, "$options": "i"}}
                ]
            
            memories = await self.db.avatar_episodic_memory.find(
                query,
                {"_id": 0}
            ).sort([
                ("significance", -1),
                ("timestamp", -1)
            ]).limit(limit).to_list(limit)
            
            # Update recall count for retrieved memories
            for memory in memories:
                await self.db.avatar_episodic_memory.update_one(
                    {"id": memory["id"]},
                    {
                        "$inc": {"recall_count": 1},
                        "$set": {"last_recalled": datetime.now(timezone.utc).isoformat()}
                    }
                )
            
            return memories
            
        except Exception as e:
            logger.error(f"Error recalling experiences: {e}")
            return []
    
    async def get_relationship_memories(
        self, 
        avatar_id: str, 
        other_user_id: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get all memories related to a specific user/relationship
        """
        try:
            memories = await self.db.avatar_episodic_memory.find({
                "avatar_id": avatar_id,
                "details.other_user_id": other_user_id
            }, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
            
            # Analyze relationship
            summary = {
                "total_memories": len(memories),
                "positive_memories": 0,
                "negative_memories": 0,
                "neutral_memories": 0,
                "first_interaction": None,
                "last_interaction": None,
                "key_moments": [],
                "overall_sentiment": 0.0
            }
            
            total_valence = 0.0
            for memory in memories:
                valence = memory.get("emotional_valence", 0)
                total_valence += valence
                
                if valence > 0.2:
                    summary["positive_memories"] += 1
                elif valence < -0.2:
                    summary["negative_memories"] += 1
                else:
                    summary["neutral_memories"] += 1
                
                # Track significant moments
                if memory.get("significance", 0) >= 0.7:
                    summary["key_moments"].append({
                        "type": memory.get("experience_type"),
                        "timestamp": memory.get("timestamp"),
                        "valence": valence
                    })
            
            if memories:
                summary["first_interaction"] = memories[-1].get("timestamp")
                summary["last_interaction"] = memories[0].get("timestamp")
                summary["overall_sentiment"] = total_valence / len(memories)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting relationship memories: {e}")
            return {
                "total_memories": 0,
                "positive_memories": 0,
                "negative_memories": 0,
                "neutral_memories": 0,
                "first_interaction": None,
                "last_interaction": None,
                "key_moments": [],
                "overall_sentiment": 0.0
            }
    
    async def get_emotional_summary(self, avatar_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get emotional summary of recent experiences
        """
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            memories = await self.db.avatar_episodic_memory.find({
                "avatar_id": avatar_id,
                "timestamp": {"$gte": cutoff}
            }, {"_id": 0}).to_list(500)
            
            summary = {
                "total_experiences": len(memories),
                "avg_emotional_valence": 0.0,
                "experience_breakdown": {},
                "emotional_trend": "stable",
                "most_significant": None,
                "recent_highlights": []
            }
            
            if not memories:
                return summary
            
            # Calculate averages
            total_valence = 0.0
            experience_counts = {}
            
            for memory in memories:
                valence = memory.get("emotional_valence", 0)
                total_valence += valence
                
                exp_type = memory.get("experience_type", "unknown")
                experience_counts[exp_type] = experience_counts.get(exp_type, 0) + 1
                
                # Track most significant
                if memory.get("significance", 0) >= 0.8:
                    if not summary["most_significant"] or \
                       memory.get("significance", 0) > summary["most_significant"].get("significance", 0):
                        summary["most_significant"] = {
                            "type": exp_type,
                            "timestamp": memory.get("timestamp"),
                            "valence": valence
                        }
            
            summary["avg_emotional_valence"] = total_valence / len(memories)
            summary["experience_breakdown"] = experience_counts
            
            # Determine trend (compare first half vs second half)
            mid = len(memories) // 2
            if mid > 0:
                first_half_avg = sum(m.get("emotional_valence", 0) for m in memories[mid:]) / (len(memories) - mid)
                second_half_avg = sum(m.get("emotional_valence", 0) for m in memories[:mid]) / mid
                
                if second_half_avg > first_half_avg + 0.2:
                    summary["emotional_trend"] = "improving"
                elif second_half_avg < first_half_avg - 0.2:
                    summary["emotional_trend"] = "declining"
            
            # Get recent highlights (positive, significant)
            highlights = [m for m in memories if m.get("emotional_valence", 0) > 0.3 and m.get("significance", 0) > 0.5]
            summary["recent_highlights"] = [
                {"type": h.get("experience_type"), "timestamp": h.get("timestamp")}
                for h in highlights[:5]
            ]
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting emotional summary: {e}")
            return {
                "total_experiences": 0,
                "avg_emotional_valence": 0.0,
                "experience_breakdown": {},
                "emotional_trend": "stable",
                "most_significant": None,
                "recent_highlights": []
            }
    
    async def decay_old_memories(self, avatar_id: str, decay_rate: float = 0.1):
        """
        Apply decay to old, unrecalled memories
        
        Memories that haven't been recalled decay over time,
        but significant memories decay slower
        """
        try:
            # Get memories older than 7 days that haven't been recalled recently
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            
            old_memories = await self.db.avatar_episodic_memory.find({
                "avatar_id": avatar_id,
                "timestamp": {"$lt": week_ago},
                "$or": [
                    {"last_recalled": None},
                    {"last_recalled": {"$lt": week_ago}}
                ]
            }).to_list(100)
            
            for memory in old_memories:
                current_decay = memory.get("decay_factor", 1.0)
                significance = memory.get("significance", 0.5)
                
                # Higher significance = slower decay
                adjusted_decay_rate = decay_rate * (1 - significance * 0.5)
                new_decay = max(0.1, current_decay - adjusted_decay_rate)
                
                await self.db.avatar_episodic_memory.update_one(
                    {"id": memory["id"]},
                    {"$set": {"decay_factor": new_decay}}
                )
            
            logger.debug(f"Applied decay to {len(old_memories)} memories for {avatar_id}")
            
        except Exception as e:
            logger.error(f"Error decaying memories: {e}")
    
    async def consolidate_memories(self, avatar_id: str):
        """
        Consolidate similar memories to prevent memory bloat
        
        Groups similar experiences and creates summary memories
        """
        try:
            # Get memories from last 30 days
            month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            
            memories = await self.db.avatar_episodic_memory.find({
                "avatar_id": avatar_id,
                "timestamp": {"$gte": month_ago},
                "significance": {"$lt": 0.5}  # Only consolidate less significant memories
            }).to_list(500)
            
            # Group by experience type and week
            # This is a simplified consolidation - could be more sophisticated
            
            if len(memories) > 100:
                # Keep only the most significant 100 from low-significance memories
                sorted_memories = sorted(memories, key=lambda m: m.get("significance", 0), reverse=True)
                to_remove = sorted_memories[100:]
                
                for memory in to_remove:
                    await self.db.avatar_episodic_memory.delete_one({"id": memory["id"]})
                
                logger.info(f"Consolidated {len(to_remove)} memories for {avatar_id}")
            
        except Exception as e:
            logger.error(f"Error consolidating memories: {e}")

