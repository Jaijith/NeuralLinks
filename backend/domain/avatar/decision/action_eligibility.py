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
        # Define action cooldowns (minimum time between actions)
        self.cooldowns = {
            "create_post": timedelta(hours=6),
            "like_post": timedelta(minutes=5),
            "comment_on_post": timedelta(minutes=10),
            "message_friend": timedelta(hours=1),
            "send_friend_request": timedelta(hours=24),
            "discover_profiles": timedelta(hours=12)
        }
        
        # Define state-based action availability
        self.state_action_map = {
            TopLevelState.ACTIVE: [
                "like_post", "comment_on_post", "react_to_post",
                "message_friend", "read_messages", "discover_profiles"
            ],
            TopLevelState.SOCIAL: [
                "message_friend", "read_messages", "respond_to_messages",
                "send_friend_request", "review_friend_requests"
            ],
            TopLevelState.CREATIVE: [
                "create_post", "share_content", "create_topic_post"
            ],
            TopLevelState.EXPLORING: [
                "discover_profiles", "discover_content", "browse_feed"
            ],
            TopLevelState.PASSIVE: [
                "read_messages", "browse_feed"  # Passive actions only
            ],
            TopLevelState.RESTING: []  # No actions during rest
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
            
            for action in available_actions:
                action_type = action.get("type", "unknown")
                
                # Check 1: State-based eligibility
                if not self._is_eligible_for_state(action_type, current_state):
                    continue
                
                # Check 2: Permissions
                if permissions and not permissions.get(action_type, True):
                    continue
                
                # Check 3: Cooldowns
                if not self._is_off_cooldown(action_type, internal_state):
                    continue
                
                # Check 4: Prerequisites
                if not self._has_prerequisites(action_type, external_state):
                    continue
                
                # Check 5: Context availability
                if not self._has_context(action_type, external_state):
                    continue
                
                # Action is eligible
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
        if action_type == "create_post":
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
            # Can always create posts
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
        if action_type == "create_post":
            time_since = internal_state.time_since_last_post
        elif action_type == "message_friend":
            time_since = internal_state.time_since_last_conversation
        elif action_type in ["like_post", "comment_on_post"]:
            time_since = internal_state.time_since_last_reaction
        else:
            time_since = internal_state.time_since_last_action
        
        remaining = cooldown - time_since
        return remaining if remaining > timedelta(0) else None

