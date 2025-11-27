"""
State Manager
Manages avatar internal and external states, including persistence
"""
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from .internal_state import InternalState
from .external_state import ExternalState
from .state_models import StateTransition, ActionOutcome, RelationshipSnapshot
import logging
import uuid

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages avatar states (internal and external)
    
    Responsibilities:
    - Initialize states for new avatars
    - Update states based on perception and actions
    - Persist states to database
    - Retrieve states from database
    - Track state history
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def initialize_state(
        self,
        avatar_id: str,
        initial_mood: Optional[str] = None,
        initial_energy: float = 0.5
    ) -> Tuple[InternalState, ExternalState]:
        """
        Initialize states for a new avatar
        
        Args:
            avatar_id: Avatar user ID
            initial_mood: Optional initial mood (defaults to NEUTRAL)
            initial_energy: Initial energy level (0.0-1.0, defaults to 0.5)
        
        Returns:
            Tuple of (InternalState, ExternalState)
        """
        try:
            # Check if states already exist
            existing_internal = await self.db.avatar_internal_states.find_one({"avatar_id": avatar_id})
            existing_external = await self.db.avatar_external_states.find_one({"avatar_id": avatar_id})
            
            if existing_internal and existing_external:
                # States exist, load them
                internal_state = InternalState.from_dict(existing_internal.get("state", {}))
                external_state = ExternalState.from_dict(existing_external.get("state", {}))
                return internal_state, external_state
            
            # Create new states
            from .state_models import MoodState
            
            internal_state = InternalState(
                mood=MoodState(initial_mood) if initial_mood else MoodState.NEUTRAL,
                energy_level=initial_energy,
                social_desire=0.5,
                creative_urge=0.5,
                focus_level=0.5
            )
            
            external_state = ExternalState()
            
            # Persist initial states
            await self.persist_state(avatar_id, internal_state, external_state)
            
            logger.info(f"Initialized states for avatar {avatar_id}")
            return internal_state, external_state
            
        except Exception as e:
            logger.error(f"Error initializing state for {avatar_id}: {e}")
            # Return default states on error
            return InternalState(), ExternalState()
    
    async def get_current_state(
        self,
        avatar_id: str
    ) -> Tuple[InternalState, ExternalState]:
        """
        Get current internal and external states for avatar
        
        Args:
            avatar_id: Avatar user ID
        
        Returns:
            Tuple of (InternalState, ExternalState)
        """
        try:
            # Load internal state
            internal_doc = await self.db.avatar_internal_states.find_one({"avatar_id": avatar_id})
            if internal_doc:
                internal_state = InternalState.from_dict(internal_doc.get("state", {}))
            else:
                # Initialize if doesn't exist
                internal_state, _ = await self.initialize_state(avatar_id)
                return await self.get_current_state(avatar_id)  # Recursive call after init
            
            # Load external state
            external_doc = await self.db.avatar_external_states.find_one({"avatar_id": avatar_id})
            if external_doc:
                external_state = ExternalState.from_dict(external_doc.get("state", {}))
            else:
                # Initialize if doesn't exist
                _, external_state = await self.initialize_state(avatar_id)
                return await self.get_current_state(avatar_id)  # Recursive call after init
            
            return internal_state, external_state
            
        except Exception as e:
            logger.error(f"Error getting current state for {avatar_id}: {e}")
            return InternalState(), ExternalState()
    
    async def update_internal_state(
        self,
        avatar_id: str,
        internal_state: InternalState
    ):
        """
        Update internal state
        
        Args:
            avatar_id: Avatar user ID
            internal_state: Updated InternalState object
        """
        try:
            internal_state.last_updated = datetime.now(timezone.utc)
            
            # Persist to database
            await self.db.avatar_internal_states.update_one(
                {"avatar_id": avatar_id},
                {
                    "$set": {
                        "avatar_id": avatar_id,
                        "state": internal_state.to_dict(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                },
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error updating internal state for {avatar_id}: {e}")
    
    async def update_external_state(
        self,
        avatar_id: str,
        external_state: ExternalState
    ):
        """
        Update external state
        
        Args:
            avatar_id: Avatar user ID
            external_state: Updated ExternalState object
        """
        try:
            external_state.last_updated = datetime.now(timezone.utc)
            
            # Persist to database
            await self.db.avatar_external_states.update_one(
                {"avatar_id": avatar_id},
                {
                    "$set": {
                        "avatar_id": avatar_id,
                        "state": external_state.to_dict(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                },
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error updating external state for {avatar_id}: {e}")
    
    async def persist_state(
        self,
        avatar_id: str,
        internal_state: InternalState,
        external_state: ExternalState
    ):
        """
        Persist both internal and external states
        
        Args:
            avatar_id: Avatar user ID
            internal_state: InternalState object
            external_state: ExternalState object
        """
        try:
            now = datetime.now(timezone.utc)
            
            # Persist internal state
            await self.db.avatar_internal_states.update_one(
                {"avatar_id": avatar_id},
                {
                    "$set": {
                        "avatar_id": avatar_id,
                        "state": internal_state.to_dict(),
                        "updated_at": now.isoformat()
                    }
                },
                upsert=True
            )
            
            # Persist external state
            await self.db.avatar_external_states.update_one(
                {"avatar_id": avatar_id},
                {
                    "$set": {
                        "avatar_id": avatar_id,
                        "state": external_state.to_dict(),
                        "updated_at": now.isoformat()
                    }
                },
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error persisting state for {avatar_id}: {e}")
    
    async def update_temporal_states(
        self,
        avatar_id: str
    ) -> InternalState:
        """
        Update temporal states (time since last actions) based on database
        
        Args:
            avatar_id: Avatar user ID
        
        Returns:
            Updated InternalState
        """
        try:
            internal_state, _ = await self.get_current_state(avatar_id)
            
            # Get last action times from autonomous_activities
            last_activity = await self.db.autonomous_activities.find_one(
                {"user_id": avatar_id},
                sort=[("timestamp", -1)]
            )
            
            # Get last post time
            last_post = await self.db.posts.find_one(
                {"user_id": avatar_id},
                sort=[("created_at", -1)]
            )
            
            # Get last conversation time (from messages)
            last_message = None
            conversations = await self.db.direct_messages.find({
                "$or": [
                    {"user1_id": avatar_id},
                    {"user2_id": avatar_id}
                ]
            }).sort([("updated_at", -1)]).limit(1).to_list(1)
            
            if conversations:
                messages = conversations[0].get("messages", [])
                if messages:
                    last_message = messages[-1]
            
            # Get last reaction time (from likes/comments)
            last_reaction = None
            # Check posts that avatar liked or commented on
            posts_with_reactions = await self.db.posts.find({
                "$or": [
                    {"liked_by": {"$elemMatch": {"user_id": avatar_id}}},
                    {"comments": {"$elemMatch": {"user_id": avatar_id}}}
                ]
            }).sort([("created_at", -1)]).limit(1).to_list(1)
            
            if posts_with_reactions:
                last_reaction_post = posts_with_reactions[0]
                # Get most recent like or comment
                liked_by = last_reaction_post.get("liked_by", [])
                comments = last_reaction_post.get("comments", [])
                
                last_like = None
                last_comment = None
                
                for like in liked_by:
                    if isinstance(like, dict) and like.get("user_id") == avatar_id:
                        last_like = like.get("timestamp") or like.get("created_at")
                        break
                
                for comment in comments:
                    if comment.get("user_id") == avatar_id:
                        last_comment = comment.get("timestamp") or comment.get("created_at")
                        break
                
                if last_like or last_comment:
                    # Use most recent
                    last_reaction = last_like if last_like else last_comment
            
            # Parse timestamps - ensure all are timezone-aware
            def parse_timestamp(ts):
                if not ts:
                    return None
                if isinstance(ts, datetime):
                    # Ensure timezone-aware
                    if ts.tzinfo is None:
                        # Naive datetime - assume UTC
                        return ts.replace(tzinfo=timezone.utc)
                    return ts
                if isinstance(ts, str):
                    try:
                        # Try ISO format first
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        # Ensure timezone-aware
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt
                    except Exception:
                        # Try other formats
                        try:
                            # Try old format: "2025-10-25 09:20:32.884000"
                            dt = datetime.strptime(ts.split('.')[0], '%Y-%m-%d %H:%M:%S')
                            return dt.replace(tzinfo=timezone.utc)
                        except Exception:
                            return None
                return None
            
            last_action_time = parse_timestamp(last_activity.get("timestamp") if last_activity else None)
            last_post_time = parse_timestamp(last_post.get("created_at") if last_post else None)
            last_conversation_time = parse_timestamp(
                last_message.get("timestamp") or last_message.get("created_at") if last_message else None
            )
            last_reaction_time = parse_timestamp(last_reaction)
            
            # Update temporal states
            internal_state.update_temporal_states(
                last_action_time=last_action_time,
                last_post_time=last_post_time,
                last_conversation_time=last_conversation_time,
                last_reaction_time=last_reaction_time
            )
            
            # Persist updated state
            await self.update_internal_state(avatar_id, internal_state)
            
            return internal_state
            
        except Exception as e:
            logger.error(f"Error updating temporal states for {avatar_id}: {e}")
            internal_state, _ = await self.get_current_state(avatar_id)
            return internal_state
    
    async def log_state_transition(
        self,
        avatar_id: str,
        from_state: str,
        to_state: str,
        reason: str,
        triggered_by: str = "system",
        context: Optional[Dict[str, Any]] = None
    ):
        """Log a state transition to history"""
        try:
            transition = StateTransition(
                from_state=from_state,
                to_state=to_state,
                timestamp=datetime.now(timezone.utc),
                reason=reason,
                triggered_by=triggered_by,
                context=context or {}
            )
            
            await self.db.avatar_state_history.insert_one({
                "avatar_id": avatar_id,
                "type": "state_transition",
                "data": transition.model_dump(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error logging state transition for {avatar_id}: {e}")
    
    async def log_action_outcome(
        self,
        avatar_id: str,
        action_id: str,
        action_type: str,
        success: bool,
        outcome_data: Optional[Dict[str, Any]] = None,
        state_before: Optional[str] = None,
        state_after: Optional[str] = None
    ):
        """Log an action outcome to history"""
        try:
            outcome = ActionOutcome(
                action_id=action_id,
                action_type=action_type,
                timestamp=datetime.now(timezone.utc),
                success=success,
                outcome_data=outcome_data or {},
                state_before=state_before,
                state_after=state_after
            )
            
            await self.db.avatar_state_history.insert_one({
                "avatar_id": avatar_id,
                "type": "action_outcome",
                "data": outcome.model_dump(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error logging action outcome for {avatar_id}: {e}")

