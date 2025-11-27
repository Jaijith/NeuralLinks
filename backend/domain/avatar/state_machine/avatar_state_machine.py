"""
Avatar State Machine
Hierarchical State Machine for avatar behavior
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.avatar.state import InternalState, ExternalState, StateManager
from domain.avatar.perception.engine import PerceptionEngine
from domain.avatar.state_machine import (
    TopLevelState,
    ActiveSubState,
    SocialSubState,
    CreativeSubState,
    evaluate_state_transitions
)
import logging

logger = logging.getLogger(__name__)


class AvatarStateMachine:
    """
    Hierarchical State Machine for avatar behavior
    
    Manages:
    - Top-level states (ACTIVE, PASSIVE, CREATIVE, SOCIAL, EXPLORING, RESTING)
    - Sub-states within each top-level state
    - State transitions based on conditions
    - State entry/exit actions
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        perception_engine: Optional[PerceptionEngine] = None,
        state_manager: Optional[StateManager] = None
    ):
        self.db = db
        self.perception_engine = perception_engine or PerceptionEngine(db)
        self.state_manager = state_manager or StateManager(db)
        
        # Current state
        self.current_top_level_state: Optional[TopLevelState] = None
        self.current_sub_states: List[str] = []
        
        # State history (in-memory cache)
        self.state_history: List[Dict[str, Any]] = []
    
    async def initialize(self, avatar_id: str) -> TopLevelState:
        """
        Initialize state machine for avatar
        
        Args:
            avatar_id: Avatar user ID
        
        Returns:
            Initial top-level state
        """
        try:
            # Get current state from database or default to PASSIVE
            user = await self.db.users.find_one({"id": avatar_id})
            
            if user and user.get("current_top_level_state"):
                # Load from database
                self.current_top_level_state = TopLevelState(user["current_top_level_state"])
                self.current_sub_states = user.get("current_sub_states", [])
            else:
                # Default to PASSIVE
                self.current_top_level_state = TopLevelState.PASSIVE
                self.current_sub_states = []
            
            # Update database
            await self.db.users.update_one(
                {"id": avatar_id},
                {
                    "$set": {
                        "current_top_level_state": self.current_top_level_state.value,
                        "current_sub_states": self.current_sub_states
                    }
                }
            )
            
            logger.info(f"State machine initialized for {avatar_id}: {self.current_top_level_state.value}")
            return self.current_top_level_state
            
        except Exception as e:
            logger.error(f"Error initializing state machine for {avatar_id}: {e}")
            self.current_top_level_state = TopLevelState.PASSIVE
            return self.current_top_level_state
    
    async def get_current_state(
        self,
        avatar_id: str
    ) -> Tuple[TopLevelState, List[str]]:
        """
        Get current state for avatar
        
        Args:
            avatar_id: Avatar user ID
        
        Returns:
            Tuple of (top_level_state, sub_states)
        """
        if self.current_top_level_state is None:
            await self.initialize(avatar_id)
        
        return self.current_top_level_state, self.current_sub_states
    
    async def evaluate_transitions(
        self,
        avatar_id: str,
        archetype: str = "general"
    ) -> Optional[TopLevelState]:
        """
        Evaluate if state should transition based on current conditions
        
        Args:
            avatar_id: Avatar user ID
            archetype: Avatar archetype (for probability modifiers)
        
        Returns:
            New state to transition to, or None if no transition
        """
        try:
            # Get current states
            internal_state, external_state = await self.state_manager.get_current_state(avatar_id)
            
            # Update external state from perception
            perception_data = await self.perception_engine.perceive_all(avatar_id)
            external_state.update_from_perception(perception_data)
            await self.state_manager.update_external_state(avatar_id, external_state)
            
            # Update temporal states
            internal_state = await self.state_manager.update_temporal_states(avatar_id)
            
            # Get current top-level state
            current_state, _ = await self.get_current_state(avatar_id)
            
            # Evaluate transitions
            new_state = evaluate_state_transitions(
                current_state,
                internal_state,
                external_state,
                archetype
            )
            
            return new_state
            
        except Exception as e:
            logger.error(f"Error evaluating transitions for {avatar_id}: {e}")
            return None
    
    async def transition_to(
        self,
        avatar_id: str,
        new_top_level_state: TopLevelState,
        new_sub_states: Optional[List[str]] = None,
        reason: str = "State transition",
        triggered_by: str = "system"
    ):
        """
        Transition to a new state
        
        Args:
            avatar_id: Avatar user ID
            new_top_level_state: New top-level state
            new_sub_states: Optional new sub-states
            reason: Reason for transition
            triggered_by: What triggered the transition
        """
        try:
            old_state = self.current_top_level_state
            
            # Execute on_exit actions for old state
            if old_state:
                await self._execute_exit_actions(avatar_id, old_state)
            
            # Update current state
            self.current_top_level_state = new_top_level_state
            self.current_sub_states = new_sub_states or []
            
            # Execute on_enter actions for new state
            await self._execute_enter_actions(avatar_id, new_top_level_state)
            
            # Persist state to database
            await self.db.users.update_one(
                {"id": avatar_id},
                {
                    "$set": {
                        "current_top_level_state": new_top_level_state.value,
                        "current_sub_states": self.current_sub_states,
                        "last_state_change": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            # Log transition
            if old_state:
                await self.state_manager.log_state_transition(
                    avatar_id,
                    old_state.value,
                    new_top_level_state.value,
                    reason=reason,
                    triggered_by=triggered_by,
                    context={
                        "sub_states": self.current_sub_states,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            
            # Add to history
            self.state_history.append({
                "from_state": old_state.value if old_state else None,
                "to_state": new_top_level_state.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason
            })
            
            # Keep only last 100 transitions in memory
            if len(self.state_history) > 100:
                self.state_history = self.state_history[-100:]
            
            logger.info(f"State transition for {avatar_id}: {old_state.value if old_state else 'None'} -> {new_top_level_state.value}")
            
        except Exception as e:
            logger.error(f"Error transitioning state for {avatar_id}: {e}")
    
    async def run_current_state_actions(
        self,
        avatar_id: str
    ) -> List[str]:
        """
        Run actions appropriate for current state
        
        This will be used by behavior trees and decision engine
        
        Args:
            avatar_id: Avatar user ID
        
        Returns:
            List of actions to execute
        """
        try:
            current_state, sub_states = await self.get_current_state(avatar_id)
            
            # Get actions based on current state
            actions = []
            
            if current_state == TopLevelState.ACTIVE:
                # Active state actions
                actions.extend(await self._get_active_state_actions(avatar_id, sub_states))
            elif current_state == TopLevelState.SOCIAL:
                # Social state actions
                actions.extend(await self._get_social_state_actions(avatar_id, sub_states))
            elif current_state == TopLevelState.CREATIVE:
                # Creative state actions
                actions.extend(await self._get_creative_state_actions(avatar_id, sub_states))
            elif current_state == TopLevelState.EXPLORING:
                # Exploring state actions
                actions.extend(await self._get_exploring_state_actions(avatar_id))
            elif current_state == TopLevelState.RESTING:
                # Resting state actions (usually none, just cooldown)
                pass
            elif current_state == TopLevelState.PASSIVE:
                # Passive state actions (observation)
                pass
            
            return actions
            
        except Exception as e:
            logger.error(f"Error running current state actions for {avatar_id}: {e}")
            return []
    
    async def _execute_enter_actions(
        self,
        avatar_id: str,
        state: TopLevelState
    ):
        """Execute actions when entering a state"""
        try:
            # Update internal state based on state entered
            internal_state, _ = await self.state_manager.get_current_state(avatar_id)
            
            if state == TopLevelState.ACTIVE:
                # Boost energy slightly when becoming active
                internal_state.boost_energy(0.1)
            elif state == TopLevelState.CREATIVE:
                # Set creative focus
                internal_state.focus_level = 0.8
            elif state == TopLevelState.SOCIAL:
                # Increase social desire
                internal_state.social_desire = min(1.0, internal_state.social_desire + 0.2)
            elif state == TopLevelState.RESTING:
                # Start energy restoration
                internal_state.energy_level = min(1.0, internal_state.energy_level + 0.1)
            
            await self.state_manager.update_internal_state(avatar_id, internal_state)
            
        except Exception as e:
            logger.error(f"Error executing enter actions for {avatar_id}: {e}")
    
    async def _execute_exit_actions(
        self,
        avatar_id: str,
        state: TopLevelState
    ):
        """Execute actions when exiting a state"""
        try:
            # Update internal state based on state exited
            internal_state, _ = await self.state_manager.get_current_state(avatar_id)
            
            if state == TopLevelState.CREATIVE:
                # Reset creative urge after creating
                internal_state.creative_urge = max(0.0, internal_state.creative_urge - 0.3)
            elif state == TopLevelState.SOCIAL:
                # Update social timestamp
                internal_state.time_since_last_conversation = timedelta(0)
            
            await self.state_manager.update_internal_state(avatar_id, internal_state)
            
        except Exception as e:
            logger.error(f"Error executing exit actions for {avatar_id}: {e}")
    
    async def _get_active_state_actions(
        self,
        avatar_id: str,
        sub_states: List[str]
    ) -> List[str]:
        """Get actions for ACTIVE state"""
        actions = []
        
        # Get external state to check for opportunities
        _, external_state = await self.state_manager.get_current_state(avatar_id)
        
        if external_state.has_unread_interactions():
            actions.append("respond_to_messages")
        
        if external_state.friend_activity_level > 0.5:
            actions.append("react_to_friend_posts")
        
        if len(external_state.get_content_opportunities()) > 0:
            actions.append("engage_with_content")
        
        return actions
    
    async def _get_social_state_actions(
        self,
        avatar_id: str,
        sub_states: List[str]
    ) -> List[str]:
        """Get actions for SOCIAL state"""
        actions = []
        
        _, external_state = await self.state_manager.get_current_state(avatar_id)
        
        if external_state.unread_messages > 0:
            actions.append("read_and_respond_messages")
        
        if external_state.pending_friend_requests > 0:
            actions.append("review_friend_requests")
        
        # Check relationship context for maintenance actions
        relationship_map = external_state.get_relationship_map()
        if relationship_map:
            # Find relationships that need attention
            for friend_id, rel_data in list(relationship_map.items())[:3]:
                strength = rel_data.get("strength_score", 0.0)
                if strength < 0.3:
                    actions.append(f"strengthen_relationship_{friend_id}")
        
        return actions
    
    async def _get_creative_state_actions(
        self,
        avatar_id: str,
        sub_states: List[str]
    ) -> List[str]:
        """Get actions for CREATIVE state"""
        actions = []
        
        internal_state, external_state = await self.state_manager.get_current_state(avatar_id)
        
        # Check if it's time to post
        if internal_state.time_since_last_post > timedelta(hours=6):
            actions.append("create_post")
        
        # Check for content to share
        trending_topics = external_state.get_trending_topics(limit=5)
        if trending_topics:
            actions.append("create_topic_post")
        
        return actions
    
    async def _get_exploring_state_actions(
        self,
        avatar_id: str
    ) -> List[str]:
        """Get actions for EXPLORING state"""
        actions = []
        
        _, external_state = await self.state_manager.get_current_state(avatar_id)
        
        # Explore new content
        actions.append("discover_new_content")
        
        # Explore new profiles
        actions.append("discover_profiles")
        
        return actions
    
    def get_state_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent state history"""
        return self.state_history[-limit:]
    
    async def get_state_summary(self, avatar_id: str) -> Dict[str, Any]:
        """Get comprehensive state summary"""
        try:
            top_level_state, sub_states = await self.get_current_state(avatar_id)
            internal_state, external_state = await self.state_manager.get_current_state(avatar_id)
            
            return {
                "avatar_id": avatar_id,
                "current_state": {
                    "top_level": top_level_state.value if top_level_state else None,
                    "sub_states": sub_states
                },
                "internal_state": {
                    "mood": internal_state.mood.value,
                    "energy_level": internal_state.energy_level,
                    "social_desire": internal_state.social_desire,
                    "creative_urge": internal_state.creative_urge,
                    "focus_level": internal_state.focus_level,
                    "time_since_last_action": str(internal_state.time_since_last_action),
                    "time_since_last_post": str(internal_state.time_since_last_post),
                    "active_goals": len(internal_state.get_active_goals())
                },
                "external_state": {
                    "friend_activity_level": external_state.friend_activity_level,
                    "unread_messages": external_state.unread_messages,
                    "pending_friend_requests": external_state.pending_friend_requests,
                    "time_of_day": external_state.time_of_day,
                    "is_weekend": external_state.is_weekend,
                    "platform_activity_level": external_state.platform_activity_level
                },
                "state_history": self.get_state_history(limit=10),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting state summary for {avatar_id}: {e}")
            return {}
    
    async def get_state_history_from_db(
        self,
        avatar_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get state transition history from database
        
        Args:
            avatar_id: Avatar user ID
            limit: Maximum number of transitions to return
        
        Returns:
            List of state transition records
        """
        try:
            history = await self.db.avatar_state_history.find(
                {"avatar_id": avatar_id, "type": "state_transition"}
            ).sort([("timestamp", -1)]).limit(limit).to_list(limit)
            
            return [
                {
                    "from_state": h.get("data", {}).get("from_state"),
                    "to_state": h.get("data", {}).get("to_state"),
                    "timestamp": h.get("timestamp"),
                    "reason": h.get("data", {}).get("reason"),
                    "triggered_by": h.get("data", {}).get("triggered_by")
                }
                for h in history
            ]
            
        except Exception as e:
            logger.error(f"Error getting state history from DB for {avatar_id}: {e}")
            return []
    
    async def get_debug_info(self, avatar_id: str) -> Dict[str, Any]:
        """
        Get comprehensive debug information about avatar state
        
        Args:
            avatar_id: Avatar user ID
        
        Returns:
            Dictionary with debug information
        """
        try:
            # Get current state
            top_level_state, sub_states = await self.get_current_state(avatar_id)
            
            # Get internal and external states
            internal_state, external_state = await self.state_manager.get_current_state(avatar_id)
            
            # Get perception data
            perception_data = await self.perception_engine.perceive_all(avatar_id)
            
            # Get state history
            db_history = await self.get_state_history_from_db(avatar_id, limit=20)
            
            # Evaluate potential transitions
            user = await self.db.users.find_one({"id": avatar_id})
            archetype = user.get("avatar_archetype", "general") if user else "general"
            potential_transition = await self.evaluate_transitions(avatar_id, archetype)
            
            return {
                "avatar_id": avatar_id,
                "current_state": {
                    "top_level": top_level_state.value if top_level_state else None,
                    "sub_states": sub_states
                },
                "internal_state": {
                    "mood": internal_state.mood.value,
                    "energy_level": round(internal_state.energy_level, 3),
                    "social_desire": round(internal_state.social_desire, 3),
                    "creative_urge": round(internal_state.creative_urge, 3),
                    "focus_level": round(internal_state.focus_level, 3),
                    "time_since_last_action": str(internal_state.time_since_last_action),
                    "time_since_last_post": str(internal_state.time_since_last_post),
                    "time_since_last_conversation": str(internal_state.time_since_last_conversation),
                    "active_goals_count": len(internal_state.get_active_goals()),
                    "goals": [g.model_dump() for g in internal_state.get_active_goals()[:5]]
                },
                "external_state": {
                    "friend_activity_level": round(external_state.friend_activity_level, 3),
                    "unread_messages": external_state.unread_messages,
                    "pending_friend_requests": external_state.pending_friend_requests,
                    "time_of_day": external_state.time_of_day,
                    "is_weekend": external_state.is_weekend,
                    "platform_activity_level": round(external_state.platform_activity_level, 3),
                    "has_unread_interactions": external_state.has_unread_interactions(),
                    "is_high_activity_period": external_state.is_high_activity_period(),
                    "recent_posts_count": len(external_state.get_recent_posts()),
                    "content_opportunities_count": len(external_state.get_content_opportunities()),
                    "trending_topics": external_state.get_trending_topics(limit=5)
                },
                "perception": {
                    "perceived_at": perception_data.get("perceived_at"),
                    "friend_activity_level": perception_data.get("friend_activity_level", 0),
                    "relationships_count": len(perception_data.get("relationship_map", {})),
                    "trending_topics": perception_data.get("trending_topics", [])[:5]
                },
                "state_transitions": {
                    "potential_transition": potential_transition.value if potential_transition else None,
                    "recent_transitions": db_history[:10]
                },
                "state_history": {
                    "in_memory_count": len(self.state_history),
                    "recent_transitions": self.get_state_history(limit=10)
                },
                "debug_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting debug info for {avatar_id}: {e}", exc_info=True)
            return {"error": str(e)}


# Import timedelta for time comparisons
from datetime import timedelta

