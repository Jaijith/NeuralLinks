"""
Memory Manager
Unified interface for all avatar memory systems
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.graph.rag import GraphRAG
from .action_memory import ActionMemory
from .episodic_memory import EpisodicMemory
import logging

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Unified memory manager for avatar agents
    
    Combines:
    - Knowledge Graph (long-term semantic memory)
    - Action Memory (procedural memory - what works)
    - Episodic Memory (experiential memory - what happened)
    
    Provides a unified interface for memory-informed decision making
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.graph_rag = GraphRAG(db)
        self.action_memory = ActionMemory(db)
        self.episodic_memory = EpisodicMemory(db)
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def get_full_memory_context(
        self, 
        avatar_id: str,
        include_graph: bool = True,
        include_actions: bool = True,
        include_episodes: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive memory context for decision making
        
        Returns unified memory context combining all memory systems
        """
        try:
            # Check cache
            cache_key = f"full_memory_{avatar_id}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if (datetime.now(timezone.utc) - cached_time).total_seconds() < self.cache_ttl:
                    return cached_data
            
            context = {
                "avatar_id": avatar_id,
                "retrieved_at": datetime.now(timezone.utc).isoformat()
            }
            
            # 1. Knowledge Graph (semantic memory - who am I, what do I like)
            if include_graph:
                graph_context = await self.graph_rag.get_user_context(avatar_id, max_nodes=30)
                context["semantic_memory"] = {
                    "interests": [i["label"] for i in graph_context.get("interests", [])[:10]],
                    "traits": [t["label"] for t in graph_context.get("traits", [])[:5]],
                    "values": [v["label"] for v in graph_context.get("values", [])[:5]],
                    "preferences": [p["label"] for p in graph_context.get("preferences", [])[:5]],
                    "interest_strengths": {
                        i["label"]: i.get("strength", 1.0) 
                        for i in graph_context.get("interests", [])[:10]
                    }
                }
            
            # 2. Action Memory (procedural memory - what works)
            if include_actions:
                action_patterns = await self.action_memory.get_action_patterns(avatar_id)
                recent_actions = await self.action_memory.get_recent_actions(avatar_id, limit=10, hours_ago=6)
                
                context["procedural_memory"] = {
                    "action_patterns": action_patterns,
                    "recent_actions": [
                        {"type": a["action_type"], "success": a.get("success", False)}
                        for a in recent_actions
                    ],
                    "best_performing_action": action_patterns.get("best_performing"),
                    "actions_to_avoid": [
                        action_type for action_type, rate 
                        in action_patterns.get("success_rates", {}).items()
                        if rate < 0.2
                    ]
                }
            
            # 3. Episodic Memory (experiential memory - what happened)
            if include_episodes:
                emotional_summary = await self.episodic_memory.get_emotional_summary(avatar_id, days=7)
                recent_experiences = await self.episodic_memory.recall_experiences(
                    avatar_id, limit=5, min_significance=0.5
                )
                
                context["episodic_memory"] = {
                    "emotional_state": emotional_summary,
                    "recent_significant_experiences": [
                        {
                            "type": e["experience_type"],
                            "valence": e.get("emotional_valence", 0),
                            "significance": e.get("significance", 0)
                        }
                        for e in recent_experiences
                    ],
                    "emotional_trend": emotional_summary.get("emotional_trend", "stable")
                }
            
            # Cache result
            self.cache[cache_key] = (context, datetime.now(timezone.utc))
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting full memory context: {e}")
            return {
                "avatar_id": avatar_id,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "semantic_memory": {"interests": [], "traits": [], "values": []},
                "procedural_memory": {"action_patterns": {}, "recent_actions": []},
                "episodic_memory": {"emotional_state": {}, "recent_significant_experiences": []}
            }
    
    async def get_context_for_action(
        self, 
        avatar_id: str, 
        action_type: str,
        target_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get memory context relevant to a specific action
        """
        try:
            context = {
                "action_type": action_type,
                "should_avoid": False,
                "avoid_reason": "",
                "relevant_interests": [],
                "relationship_context": None,
                "past_success_rate": 1.0
            }
            
            # Check if action should be avoided
            should_avoid, reason = await self.action_memory.should_avoid_action(avatar_id, action_type)
            context["should_avoid"] = should_avoid
            context["avoid_reason"] = reason
            
            # Get action success rate
            patterns = await self.action_memory.get_action_patterns(avatar_id)
            context["past_success_rate"] = patterns.get("success_rates", {}).get(action_type, 1.0)
            
            # Get relevant interests for content creation
            if action_type in ["create_post", "comment_on_post"]:
                graph_context = await self.graph_rag.get_user_context(avatar_id, max_nodes=10)
                context["relevant_interests"] = [
                    i["label"] for i in graph_context.get("interests", [])[:5]
                ]
                
                # Get successful topics
                successful_topics = await self.action_memory.get_successful_topics(avatar_id)
                context["successful_topics"] = successful_topics[:5]
            
            # Get relationship context for social actions
            if target_user_id and action_type in ["message_friend", "send_friend_request", "like_post", "comment_on_post"]:
                interaction_history = await self.action_memory.get_interaction_history(avatar_id, target_user_id)
                relationship_memories = await self.episodic_memory.get_relationship_memories(avatar_id, target_user_id)
                
                context["relationship_context"] = {
                    "interaction_history": interaction_history,
                    "relationship_sentiment": relationship_memories.get("overall_sentiment", 0),
                    "relationship_trend": interaction_history.get("relationship_trend", "neutral"),
                    "key_moments": relationship_memories.get("key_moments", [])
                }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context for action: {e}")
            return {
                "action_type": action_type,
                "should_avoid": False,
                "avoid_reason": "",
                "relevant_interests": [],
                "relationship_context": None,
                "past_success_rate": 1.0
            }
    
    async def record_action_outcome(
        self, 
        avatar_id: str, 
        action_type: str,
        action_details: Dict[str, Any],
        outcome: Dict[str, Any]
    ):
        """
        Record an action and its outcome across memory systems
        """
        try:
            # Record in action memory
            await self.action_memory.record_action(avatar_id, action_type, action_details, outcome)
            
            # Create episodic memory for significant outcomes
            significance = self._calculate_significance(action_type, outcome)
            if significance >= 0.4:
                emotional_valence = self._calculate_valence(outcome)
                
                await self.episodic_memory.store_experience(
                    avatar_id=avatar_id,
                    experience_type=f"action_{action_type}",
                    details={
                        "action_type": action_type,
                        **action_details,
                        "outcome_summary": outcome.get("success", False)
                    },
                    emotional_valence=emotional_valence,
                    significance=significance
                )
            
            # Invalidate cache
            cache_key = f"full_memory_{avatar_id}"
            if cache_key in self.cache:
                del self.cache[cache_key]
                
        except Exception as e:
            logger.error(f"Error recording action outcome: {e}")
    
    def _calculate_significance(self, action_type: str, outcome: Dict[str, Any]) -> float:
        """Calculate how significant an action outcome is"""
        base_significance = {
            "create_post": 0.5,
            "message_friend": 0.4,
            "send_friend_request": 0.6,
            "accept_friend_request": 0.5,
            "like_post": 0.2,
            "comment_on_post": 0.3,
            "browse_feed": 0.1,
            "discover_profiles": 0.3
        }
        
        significance = base_significance.get(action_type, 0.3)
        
        # Boost for successful outcomes
        if outcome.get("success"):
            significance += 0.1
        
        # Boost for high engagement
        if outcome.get("likes_received", 0) > 3:
            significance += 0.2
        if outcome.get("reply_received"):
            significance += 0.2
        if outcome.get("request_accepted"):
            significance += 0.3
        
        return min(significance, 1.0)
    
    def _calculate_valence(self, outcome: Dict[str, Any]) -> float:
        """Calculate emotional valence of an outcome"""
        valence = 0.0
        
        if outcome.get("success"):
            valence += 0.3
        else:
            valence -= 0.2
        
        if outcome.get("likes_received", 0) > 0:
            valence += min(outcome["likes_received"] * 0.1, 0.3)
        
        if outcome.get("reply_received"):
            valence += 0.3
        
        if outcome.get("request_accepted"):
            valence += 0.4
        elif outcome.get("request_rejected"):
            valence -= 0.4
        
        return max(-1.0, min(1.0, valence))
    
    async def get_interests_matching_content(
        self, 
        avatar_id: str, 
        content: str
    ) -> List[str]:
        """
        Find avatar interests that match given content
        """
        try:
            graph_context = await self.graph_rag.get_user_context(avatar_id, max_nodes=20)
            interests = [i["label"].lower() for i in graph_context.get("interests", [])]
            
            content_lower = content.lower()
            matching = [interest for interest in interests if interest in content_lower]
            
            return matching
            
        except Exception as e:
            logger.error(f"Error matching interests to content: {e}")
            return []
    
    async def maintenance(self, avatar_id: str):
        """
        Perform memory maintenance tasks
        """
        try:
            # Decay old episodic memories
            await self.episodic_memory.decay_old_memories(avatar_id)
            
            # Consolidate if needed
            await self.episodic_memory.consolidate_memories(avatar_id)
            
            logger.debug(f"Memory maintenance completed for {avatar_id}")
            
        except Exception as e:
            logger.error(f"Error in memory maintenance: {e}")

