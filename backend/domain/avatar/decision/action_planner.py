"""
Action Planner
Plans sequences of actions to achieve goals
"""
from typing import List, Dict, Any, Optional
from domain.avatar.state import InternalState, ExternalState
from domain.avatar.state_machine import TopLevelState
import logging

logger = logging.getLogger(__name__)


class ActionPlanner:
    """
    Plans sequences of actions to achieve goals
    
    Can plan:
    - Single actions
    - Action sequences for goals
    - Follow-up actions
    """
    
    def __init__(self):
        # Define action sequences for common goals
        self.goal_sequences = {
            "strengthen_relationship": [
                {"type": "like_post", "description": "Like friend's recent post"},
                {"type": "comment_on_post", "description": "Comment on the post"},
                {"type": "message_friend", "description": "Send a message referencing the post"}
            ],
            "create_engagement": [
                {"type": "create_post", "description": "Create an engaging post"},
                {"type": "wait", "duration": 3600, "description": "Wait for responses"},
                {"type": "respond_to_messages", "description": "Respond to comments/messages"}
            ],
            "build_network": [
                {"type": "discover_profiles", "description": "Discover new profiles"},
                {"type": "send_friend_request", "description": "Send friend request to compatible users"},
                {"type": "message_friend", "description": "Message new friends"}
            ],
            "maintain_social_presence": [
                {"type": "create_post", "description": "Create a post"},
                {"type": "like_post", "description": "Like friend posts"},
                {"type": "comment_on_post", "description": "Comment on interesting posts"}
            ]
        }
    
    async def plan_action_sequence(
        self,
        goal: str,
        current_state: TopLevelState,
        internal_state: InternalState,
        external_state: ExternalState,
        character_profile: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Plan a sequence of actions to achieve a goal
        
        Args:
            goal: Goal description or goal type
            current_state: Current top-level state
            internal_state: Current internal state
            external_state: Current external state
            character_profile: Optional character profile
        
        Returns:
            List of planned actions
        """
        try:
            # Check if goal matches a predefined sequence
            goal_type = self._identify_goal_type(goal)
            
            if goal_type in self.goal_sequences:
                sequence = self.goal_sequences[goal_type].copy()
                
                # Customize sequence based on context
                customized = self._customize_sequence(
                    sequence,
                    current_state,
                    internal_state,
                    external_state,
                    character_profile
                )
                
                return customized
            
            # For custom goals, create a simple plan
            return self._create_custom_plan(
                goal,
                current_state,
                internal_state,
                external_state
            )
            
        except Exception as e:
            logger.error(f"Error planning action sequence for goal '{goal}': {e}")
            return []
    
    def _identify_goal_type(self, goal: str) -> Optional[str]:
        """Identify goal type from goal description"""
        goal_lower = goal.lower()
        
        if "relationship" in goal_lower or "friend" in goal_lower:
            return "strengthen_relationship"
        elif "engagement" in goal_lower or "interaction" in goal_lower:
            return "create_engagement"
        elif "network" in goal_lower or "discover" in goal_lower:
            return "build_network"
        elif "presence" in goal_lower or "active" in goal_lower:
            return "maintain_social_presence"
        
        return None
    
    def _customize_sequence(
        self,
        sequence: List[Dict[str, Any]],
        current_state: TopLevelState,
        internal_state: InternalState,
        external_state: ExternalState,
        character_profile: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Customize sequence based on context"""
        customized = []
        
        for action_template in sequence:
            action = action_template.copy()
            action_type = action.get("type")
            
            # Add context-specific parameters
            if action_type == "like_post" or action_type == "comment_on_post":
                # Find a post to react to
                recent_posts = external_state.get_recent_posts(limit=5)
                if recent_posts:
                    action["post_id"] = recent_posts[0].get("id")
                    action["target_friend_id"] = recent_posts[0].get("user_id")
            
            elif action_type == "message_friend":
                # Find a friend to message
                relationship_map = external_state.get_relationship_map()
                if relationship_map:
                    # Prioritize friends with unread messages or weak relationships
                    target_friend = None
                    for friend_id, rel_data in relationship_map.items():
                        strength = rel_data.get("strength_score", 0.5)
                        if strength < 0.4:  # Weak relationship - strengthen it
                            target_friend = friend_id
                            break
                    
                    if not target_friend:
                        # Use first friend
                        target_friend = list(relationship_map.keys())[0]
                    
                    action["friend_id"] = target_friend
            
            elif action_type == "create_post":
                # Add post type based on creative urge
                if internal_state.creative_urge > 0.7:
                    action["post_type"] = "thought"
                else:
                    action["post_type"] = "general"
            
            customized.append(action)
        
        return customized
    
    def _create_custom_plan(
        self,
        goal: str,
        current_state: TopLevelState,
        internal_state: InternalState,
        external_state: ExternalState
    ) -> List[Dict[str, Any]]:
        """Create a custom plan for a goal"""
        plan = []
        
        # Simple heuristic-based planning
        if "post" in goal.lower():
            plan.append({
                "type": "create_post",
                "description": "Create a post",
                "post_type": "general"
            })
        
        elif "message" in goal.lower() or "chat" in goal.lower():
            relationship_map = external_state.get_relationship_map()
            if relationship_map:
                plan.append({
                    "type": "message_friend",
                    "description": "Send a message",
                    "friend_id": list(relationship_map.keys())[0]
                })
        
        elif "friend" in goal.lower() or "connect" in goal.lower():
            plan.append({
                "type": "discover_profiles",
                "description": "Discover new profiles"
            })
            plan.append({
                "type": "send_friend_request",
                "description": "Send friend request"
            })
        
        return plan
    
    def plan_followup_actions(
        self,
        completed_action: Dict[str, Any],
        action_result: Dict[str, Any],
        internal_state: InternalState,
        external_state: ExternalState
    ) -> List[Dict[str, Any]]:
        """
        Plan follow-up actions based on completed action result
        
        Args:
            completed_action: The action that was just completed
            action_result: Result of the action
            internal_state: Current internal state
            external_state: Current external state
        
        Returns:
            List of follow-up actions
        """
        followups = []
        action_type = completed_action.get("type")
        
        if action_type == "create_post" and action_result.get("success"):
            # After creating a post, might want to engage with responses
            followups.append({
                "type": "wait",
                "duration": 3600,  # Wait 1 hour
                "description": "Wait for post responses"
            })
            followups.append({
                "type": "respond_to_messages",
                "description": "Respond to comments on the post"
            })
        
        elif action_type == "like_post" and action_result.get("success"):
            # After liking, might want to comment
            post_id = completed_action.get("post_id")
            if post_id:
                followups.append({
                    "type": "comment_on_post",
                    "description": "Comment on the liked post",
                    "post_id": post_id
                })
        
        elif action_type == "send_friend_request" and action_result.get("success"):
            # After sending request, wait and then message if accepted
            target_id = completed_action.get("target_user_id")
            if target_id:
                followups.append({
                    "type": "wait",
                    "duration": 86400,  # Wait 1 day
                    "description": "Wait for friend request response"
                })
                followups.append({
                    "type": "message_friend",
                    "description": "Message the new friend",
                    "friend_id": target_id
                })
        
        return followups

