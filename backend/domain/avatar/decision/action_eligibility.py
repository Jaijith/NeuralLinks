"""
Action Eligibility Filter
Filters actions based on current state, permissions, and cooldowns
"""
from typing import List, Dict, Any, Optional
from datetime import timedelta
from domain.avatar.state import InternalState, ExternalState
from domain.avatar.state_machine import TopLevelState
import logging

logger = logging.getLogger(__name__)


class ActionEligibility:
    """
    Determines which actions are eligible given current state
    
    Filters based on:
    1. Current state (some actions only available in certain states)
    2. Permissions (user settings)
    3. Cooldowns (rate limiting)
    4. Prerequisites (e.g., need friends to message)
    5. Context (e.g., need posts to react to)
    """
    
    def __init__(self):
        # Define action cooldowns (minimum time between SAME action type)
        # Note: These are per-action cooldowns, separate from activity level rate limiting
        # The effective cooldown is MAX(activity_level_interval, action_cooldown)
        # UPDATED: LOWERED cooldowns to allow more frequent posting/messaging
        self.cooldowns = {
            "create_post": timedelta(minutes=8),      # Can post every 8 mins (was 10)
            "like_post": timedelta(minutes=1),        # Can like every 1 min
            "comment_on_post": timedelta(minutes=3),  # Can comment every 3 mins (was 5)
            "message_friend": timedelta(minutes=3),   # Can message every 3 mins (was 5) - now tracking SENT messages only
            "send_friend_request": timedelta(minutes=20),  # Friend request every 20 mins (was 30)
            "discover_profiles": timedelta(minutes=15),    # Discover every 15 mins (was 10 - INCREASED to reduce spam)
            "browse_and_share_news": timedelta(minutes=30), # News curation every 30 mins
        }
        
        # Define state-based action availability
        # Note: Action names should match what comes from the decision engine
        # UPDATED: Added create_post to ACTIVE state - avatars can post without 
        # needing to be in CREATIVE state. Also added message_friend to more states.
        # like_post and comment_on_post are allowed in ALL states — engagement
        # should never be blocked by the state machine.
        _engagement = ["like_post", "comment_on_post"]
        self.state_action_map = {
            TopLevelState.ACTIVE: [
                *_engagement, "react_to_post",
                "message_friend", "read_messages", "discover_profiles",
                "create_post", "browse_and_share_news",
            ],
            TopLevelState.SOCIAL: [
                "message_friend", "read_messages", "respond_to_messages",
                "send_friend_request", "review_friend_requests", "accept_friend_request",
                "create_post", *_engagement,
                "browse_and_share_news",
            ],
            TopLevelState.CREATIVE: [
                "create_post", "message_friend",
                "browse_and_share_news", *_engagement,
            ],
            TopLevelState.EXPLORING: [
                "discover_profiles", "discover_content", "browse_feed",
                "create_post", "browse_and_share_news", *_engagement,
            ],
            TopLevelState.PASSIVE: [
                "read_messages", "browse_feed", "message_friend",
                "browse_and_share_news", *_engagement,
            ],
            TopLevelState.RESTING: [
                "browse_and_share_news", *_engagement,
            ]
        }
        
        # Map action types to permission keys
        # Action names are singular (message_friend) but permission keys are plural (message_friends)
        self.action_to_permission = {
            "message_friend": "message_friends",
            "create_post": "create_posts",
            "like_post": "like_posts",
            "comment_on_post": "comment_posts",
            "send_friend_request": "send_friend_requests",
            "accept_friend_request": "accept_friend_requests",
            "discover_profiles": "discover_profiles",
            "share_post": "share_posts",
            "browse_and_share_news": "browse_and_share_news",
        }
    
    async def get_eligible_actions(
        self,
        available_actions: List[Dict[str, Any]],
        current_state: TopLevelState,
        internal_state: InternalState,
        external_state: ExternalState,
        permissions: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter actions based on eligibility criteria
        
        Args:
            available_actions: List of potential actions
            current_state: Current top-level state
            internal_state: Current internal state
            external_state: Current external state
            permissions: Optional permission flags (action_type -> allowed)
        
        Returns:
            List of eligible actions
        """
        try:
            eligible = []
            
            # Log temporal state for debugging cooldowns
            logger.info(f"⏱️ Temporal states - last_action: {internal_state.time_since_last_action}, last_post: {internal_state.time_since_last_post}, last_conversation: {internal_state.time_since_last_conversation}")
            
            for action in available_actions:
                action_type = action.get("type", "unknown")
                logger.info(f"Checking eligibility for action: {action_type}")
                
                # Check 1: State-based eligibility
                if not self._is_eligible_for_state(action_type, current_state):
                    logger.warning(f"❌ Action {action_type} filtered: not eligible for state {current_state.value}")
                    continue
                
                # Check 2: Permissions (map action type to permission key)
                permission_key = self.action_to_permission.get(action_type, action_type)
                if permissions and not permissions.get(permission_key, True):
                    logger.warning(f"❌ Action {action_type} filtered: permission '{permission_key}' denied")
                    continue
                
                # Check 3: Cooldowns
                if not self._is_off_cooldown(action_type, internal_state):
                    cooldown = self.cooldowns.get(action_type)
                    remaining = self.get_cooldown_remaining(action_type, internal_state)
                    logger.warning(f"❌ Action {action_type} filtered: on cooldown (required={cooldown}, remaining={remaining})")
                    continue
                
                # Check 4: Prerequisites
                if not self._has_prerequisites(action_type, external_state):
                    logger.warning(f"❌ Action {action_type} filtered: missing prerequisites")
                    continue
                
                # Check 5: Context availability
                if not self._has_context(action_type, external_state):
                    logger.warning(f"❌ Action {action_type} filtered: missing context")
                    continue
                
                # Action is eligible
                logger.info(f"✅ Action {action_type} is eligible")
                eligible.append(action)
            
            return eligible
            
        except Exception as e:
            logger.error(f"Error filtering eligible actions: {e}")
            return []
    
    def _is_eligible_for_state(
        self,
        action_type: str,
        current_state: TopLevelState
    ) -> bool:
        """Check if action is available in current state"""
        available_actions = self.state_action_map.get(current_state, [])
        return action_type in available_actions
    
    def _is_off_cooldown(
        self,
        action_type: str,
        internal_state: InternalState
    ) -> bool:
        """Check if action is off cooldown"""
        if action_type not in self.cooldowns:
            return True  # No cooldown defined
        
        cooldown = self.cooldowns[action_type]
        
        # Check appropriate temporal state
        if action_type in ["create_post", "browse_and_share_news"]:
            time_since = internal_state.time_since_last_post
        elif action_type == "message_friend":
            time_since = internal_state.time_since_last_conversation
        elif action_type in ["like_post", "comment_on_post"]:
            time_since = internal_state.time_since_last_reaction
        else:
            time_since = internal_state.time_since_last_action
        
        return time_since >= cooldown
    
    def _has_prerequisites(
        self,
        action_type: str,
        external_state: ExternalState
    ) -> bool:
        """Check if prerequisites are met"""
        if action_type == "message_friend":
            # Need at least one friend
            relationship_map = external_state.get_relationship_map()
            return len(relationship_map) > 0
        
        elif action_type == "send_friend_request":
            # Can always send friend requests (if not at limit)
            return True
        
        elif action_type in ["like_post", "comment_on_post"]:
            # Need posts to react to
            recent_posts = external_state.get_recent_posts(limit=10)
            return len(recent_posts) > 0
        
        elif action_type == "create_post":
            return True
        
        elif action_type == "browse_and_share_news":
            return True
        
        return True
    
    def _has_context(
        self,
        action_type: str,
        external_state: ExternalState
    ) -> bool:
        """Check if required context is available"""
        if action_type == "message_friend":
            # Check if there are friends to message
            relationship_map = external_state.get_relationship_map()
            return len(relationship_map) > 0
        
        elif action_type in ["like_post", "comment_on_post"]:
            # Check if there are posts to react to
            recent_posts = external_state.get_recent_posts(limit=10)
            return len(recent_posts) > 0
        
        elif action_type == "respond_to_messages":
            # Check if there are unread messages
            return external_state.has_unread_interactions()
        
        elif action_type == "create_post":
            # Can create posts anytime
            return True
        
        return True
    
    def get_cooldown_remaining(
        self,
        action_type: str,
        internal_state: InternalState
    ) -> Optional[timedelta]:
        """Get remaining cooldown time for an action"""
        if action_type not in self.cooldowns:
            return None
        
        cooldown = self.cooldowns[action_type]
        
        # Get time since last action
        if action_type in ["create_post", "browse_and_share_news"]:
            time_since = internal_state.time_since_last_post
        elif action_type == "message_friend":
            time_since = internal_state.time_since_last_conversation
        elif action_type in ["like_post", "comment_on_post"]:
            time_since = internal_state.time_since_last_reaction
        else:
            time_since = internal_state.time_since_last_action
        
        remaining = cooldown - time_since
        return remaining if remaining > timedelta(0) else None

