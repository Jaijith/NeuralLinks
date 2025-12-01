"""
Decision Engine
Orchestrates action selection using utility-based selection, behavior trees, state machine,
and MEMORY-INFORMED decision making
"""
from typing import List, Dict, Any, Optional
from domain.avatar.state import InternalState, ExternalState, StateManager
from domain.avatar.state_machine import AvatarStateMachine, TopLevelState
from domain.avatar.behavior_tree import BehaviorTreeEngine, BehaviorTreeContext
from domain.avatar.perception.engine import PerceptionEngine
from domain.avatar.mcp.client import AvatarMCPClient
from domain.avatar.decision.action_utility import ActionUtility
from domain.avatar.decision.action_eligibility import ActionEligibility
from domain.avatar.decision.action_planner import ActionPlanner
from domain.avatar.character import CharacterProfile
import logging

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Orchestrates intelligent action selection with MEMORY integration
    
    Integrates:
    - State Machine (for state-based action filtering)
    - Behavior Trees (for complex decision-making)
    - Utility-Based Selection (for action scoring)
    - Action Eligibility (for filtering)
    - Action Planning (for sequences)
    - Memory Manager (for memory-informed decisions) [NEW]
    
    Memory Integration:
    - Uses semantic memory (knowledge graph) for interest-aligned actions
    - Uses procedural memory (action history) to avoid repetition
    - Uses episodic memory (experiences) for relationship-aware decisions
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        state_machine: AvatarStateMachine,
        perception_engine: PerceptionEngine,
        mcp_client: Optional[AvatarMCPClient] = None,
        memory_manager = None  # Optional MemoryManager for memory-informed decisions
    ):
        self.state_manager = state_manager
        self.state_machine = state_machine
        self.perception_engine = perception_engine
        self.mcp_client = mcp_client
        self.memory_manager = memory_manager  # NEW: Memory integration
        
        self.action_utility = ActionUtility()
        self.action_eligibility = ActionEligibility()
        self.action_planner = ActionPlanner()
        self.bt_engine = BehaviorTreeEngine()
    
    async def select_action(
        self,
        avatar_id: str,
        character_profile: Optional[Any] = None,  # Can be Dict or CharacterProfile
        permissions: Optional[Dict[str, bool]] = None,
        goal: Optional[str] = None,
        memory_context: Optional[Dict[str, Any]] = None  # NEW: Memory context for informed decisions
    ) -> Optional[Dict[str, Any]]:
        """
        Select the best action to execute with MEMORY-INFORMED decision making
        
        Args:
            avatar_id: Avatar user ID
            character_profile: Optional character profile
            permissions: Optional permission flags
            goal: Optional goal to achieve
            memory_context: Optional memory context (interests, past actions, experiences)
        
        Returns:
            Selected action dictionary, or None if no action should be taken
        """
        try:
            # Get current states
            internal_state, external_state = await self.state_manager.get_current_state(avatar_id)
            
            # Update external state from perception (use interest-aware perception if available)
            if hasattr(self.perception_engine, 'perceive_with_interests'):
                perception_data = await self.perception_engine.perceive_with_interests(avatar_id)
            else:
                perception_data = await self.perception_engine.perceive_all(avatar_id)
            external_state.update_from_perception(perception_data)
            await self.state_manager.update_external_state(avatar_id, external_state)
            
            # Get current state
            current_state, _ = await self.state_machine.get_current_state(avatar_id)
            
            # Get memory context if not provided and memory manager is available
            if memory_context is None and self.memory_manager:
                memory_context = await self.memory_manager.get_full_memory_context(avatar_id)
            
            # If there's a goal, use action planner
            if goal:
                plan = await self.action_planner.plan_action_sequence(
                    goal,
                    current_state,
                    internal_state,
                    external_state,
                    character_profile
                )
                if plan:
                    return plan[0]  # Return first action in plan
            
            # Get available actions based on current state
            available_actions = await self._get_available_actions(
                avatar_id,
                current_state,
                internal_state,
                external_state,
                perception_data=perception_data,  # NEW: Pass perception for interest-aware actions
                memory_context=memory_context  # NEW: Pass memory for context-aware actions
            )
            
            if not available_actions:
                return None
            
            # Filter eligible actions (with memory-based filtering)
            eligible_actions = await self._filter_with_memory(
                available_actions,
                avatar_id,
                current_state,
                internal_state,
                external_state,
                permissions,
                memory_context
            )
            
            if not eligible_actions:
                return None
            
            # Convert CharacterProfile to dict if needed
            char_profile_dict = character_profile
            if character_profile and hasattr(character_profile, 'to_dict'):
                char_profile_dict = character_profile.to_dict()
            
            # Calculate utility for each eligible action (with memory boost)
            action_scores = []
            for action in eligible_actions:
                utility = await self.action_utility.calculate_utility(
                    action,
                    internal_state,
                    external_state,
                    char_profile_dict,
                    memory_context=memory_context  # NEW: Pass memory for utility calculation
                )
                action_scores.append((action, utility))
            
            # Sort by utility (highest first)
            action_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return highest utility action
            if action_scores:
                best_action, utility = action_scores[0]
                logger.info(f"Selected action for {avatar_id}: {best_action.get('type')} (utility: {utility:.3f})")
                return best_action
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting action for {avatar_id}: {e}", exc_info=True)
            return None
    
    async def _filter_with_memory(
        self,
        actions: List[Dict[str, Any]],
        avatar_id: str,
        current_state: TopLevelState,
        internal_state: InternalState,
        external_state: ExternalState,
        permissions: Optional[Dict[str, bool]],
        memory_context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter actions using both eligibility rules and memory-based filtering
        """
        # First, apply standard eligibility filtering
        eligible_actions = await self.action_eligibility.get_eligible_actions(
            actions,
            current_state,
            internal_state,
            external_state,
            permissions
        )
        
        # If no memory context or memory manager, return standard filtered actions
        if not memory_context or not self.memory_manager:
            return eligible_actions
        
        # Apply memory-based filtering
        memory_filtered = []
        procedural_memory = memory_context.get("procedural_memory", {})
        actions_to_avoid = procedural_memory.get("actions_to_avoid", [])
        recent_repetition = procedural_memory.get("action_patterns", {}).get("recent_repetition", {})
        
        for action in eligible_actions:
            action_type = action.get("type")
            
            # Skip actions that have been failing
            if action_type in actions_to_avoid:
                logger.debug(f"Skipping {action_type} - in actions_to_avoid list")
                continue
            
            # Reduce priority of recently repeated actions (but don't skip entirely)
            repetition_count = recent_repetition.get(action_type, 0)
            if repetition_count >= 3:
                # Mark as lower priority but don't skip
                action["memory_penalty"] = 0.3 * repetition_count
            
            memory_filtered.append(action)
        
        return memory_filtered if memory_filtered else eligible_actions
    
    async def select_and_execute_action(
        self,
        avatar_id: str,
        character_profile: Optional[Dict[str, Any]] = None,
        permissions: Optional[Dict[str, bool]] = None,
        goal: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Select and execute an action
        
        Returns:
            Result dictionary with success status and details
        """
        try:
            # Select action
            action = await self.select_action(
                avatar_id,
                character_profile,
                permissions,
                goal
            )
            
            if not action:
                return {
                    "success": False,
                    "reason": "No eligible action found"
                }
            
            # Execute action using MCP client
            if not self.mcp_client:
                return {
                    "success": False,
                    "reason": "MCP client not available",
                    "action": action
                }
            
            action_type = action.get("type")
            action_args = {k: v for k, v in action.items() if k != "type" and k != "description"}
            
            result = await self.mcp_client.call_tool(
                action_type,
                avatar_id,
                **action_args
            )
            
            # Plan follow-up actions if successful
            if result.get("success"):
                followups = self.action_planner.plan_followup_actions(
                    action,
                    result,
                    await self.state_manager.get_current_state(avatar_id)[0],
                    await self.state_manager.get_current_state(avatar_id)[1]
                )
                if followups:
                    result["followup_actions"] = followups
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing action for {avatar_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_behavior_tree(
        self,
        avatar_id: str,
        behavior_tree,
        character_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a behavior tree
        
        Args:
            avatar_id: Avatar user ID
            behavior_tree: Behavior tree to execute
            character_profile: Optional character profile
        
        Returns:
            Execution result
        """
        try:
            # Create context
            context = BehaviorTreeContext(
                avatar_id=avatar_id,
                perception_engine=self.perception_engine,
                state_manager=self.state_manager,
                state_machine=self.state_machine,
                mcp_client=self.mcp_client,
                character_profile=character_profile,
                additional_data={"timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
            # Execute tree
            result = await self.bt_engine.execute_tree(behavior_tree, context)
            
            return {
                "success": result == NodeStatus.SUCCESS,
                "status": result.value,
                "tree_name": behavior_tree.name
            }
            
        except Exception as e:
            logger.error(f"Error executing behavior tree for {avatar_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_available_actions(
        self,
        avatar_id: str,
        current_state: TopLevelState,
        internal_state: InternalState,
        external_state: ExternalState,
        perception_data: Optional[Dict[str, Any]] = None,
        memory_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available actions based on current state, context, and MEMORY
        
        NEW: Uses interest perception and memory to suggest more relevant actions
        """
        actions = []
        
        # Base actions available to all states
        base_actions = [
            {"type": "read_messages", "description": "Read messages"}
        ]
        
        # Get interest perception data if available
        interest_perception = {}
        if perception_data:
            interest_perception = perception_data.get("interest_perception", {})
        
        # Get semantic memory (interests) if available
        interests = []
        if memory_context:
            semantic = memory_context.get("semantic_memory", {})
            interests = semantic.get("interests", [])
        
        # State-specific actions
        if current_state == TopLevelState.ACTIVE:
            # Get posts to react to - prioritize interest-relevant posts
            recent_posts = external_state.get_recent_posts(limit=10)
            relevant_posts = interest_perception.get("relevant_posts", [])
            
            # Create a set of relevant post IDs for quick lookup
            relevant_post_ids = {p.get("post_id") for p in relevant_posts}
            
            for post in recent_posts:
                post_id = post.get("id")
                is_relevant = post_id in relevant_post_ids
                
                actions.append({
                    "type": "like_post",
                    "description": f"Like post by {post.get('user_id')}",
                    "post_id": post_id,
                    "target_friend_id": post.get("user_id"),
                    "interest_aligned": is_relevant  # NEW: Mark interest alignment
                })
                actions.append({
                    "type": "comment_on_post",
                    "description": f"Comment on post by {post.get('user_id')}",
                    "post_id": post_id,
                    "target_friend_id": post.get("user_id"),
                    "interest_aligned": is_relevant  # NEW: Mark interest alignment
                })
            
            # Message friends - prioritize interest-aligned friends
            if external_state.has_unread_interactions():
                actions.append({
                    "type": "message_friend",
                    "description": "Respond to messages"
                })
            
            # Message interest-aligned friends proactively
            aligned_users = interest_perception.get("interest_aligned_users", [])
            for user in aligned_users[:3]:
                actions.append({
                    "type": "message_friend",
                    "description": f"Message friend with shared interests",
                    "friend_id": user.get("user_id"),
                    "shared_interests": user.get("shared_interests", []),
                    "interest_aligned": True
                })
            
            # Discover profiles
            actions.append({
                "type": "discover_profiles",
                "description": "Discover new profiles"
            })
        
        elif current_state == TopLevelState.SOCIAL:
            # Message friends - prioritize interest-aligned ones
            relationship_map = external_state.get_relationship_map()
            aligned_users = interest_perception.get("interest_aligned_users", [])
            aligned_user_ids = {u.get("user_id") for u in aligned_users}
            
            for friend_id in list(relationship_map.keys())[:5]:
                is_aligned = friend_id in aligned_user_ids
                actions.append({
                    "type": "message_friend",
                    "description": f"Message {friend_id}",
                    "friend_id": friend_id,
                    "interest_aligned": is_aligned
                })
            
            # Review friend requests
            if external_state.pending_friend_requests > 0:
                actions.append({
                    "type": "accept_friend_request",
                    "description": "Review friend requests"
                })
        
        elif current_state == TopLevelState.CREATIVE:
            # Create posts - suggest topics based on interests
            most_active_interest = interest_perception.get("most_active_interest")
            trending_interests = interest_perception.get("trending_interest_topics", [])
            
            # General post
            actions.append({
                "type": "create_post",
                "description": "Create a post",
                "post_type": "general"
            })
            
            # Interest-based post (if we have interests)
            if most_active_interest:
                actions.append({
                    "type": "create_post",
                    "description": f"Create post about {most_active_interest}",
                    "post_type": "interest",
                    "topic": most_active_interest,
                    "interest_aligned": True
                })
            
            # Trending interest post
            if trending_interests:
                actions.append({
                    "type": "create_post",
                    "description": f"Create post about trending topic: {trending_interests[0]}",
                    "post_type": "trending",
                    "topic": trending_interests[0],
                    "interest_aligned": True
            })
            
            # Share content
            actions.append({
                "type": "share_post",
                "description": "Share a post"
            })
        
        elif current_state == TopLevelState.EXPLORING:
            # Discover content
            actions.append({
                "type": "discover_profiles",
                "description": "Discover new profiles"
            })
            
            # Browse feed
            actions.append({
                "type": "browse_feed",
                "description": "Browse feed"
            })

            # If we found something interesting, we might want to share it (Create Post)
            # This allows transition to CREATIVE or ACTIVE indirectly by changing internal state/needs
            if internal_state.creative_urge > 0.5:
                # Use most active interest for the post topic
                most_active_interest = interest_perception.get("most_active_interest")
                actions.append({
                    "type": "create_post",
                    "description": "Share discovery",
                    "post_type": "observation",
                    "topic": most_active_interest,
                    "interest_aligned": bool(most_active_interest)
                })
            
            # If we found someone interesting
            if external_state.pending_friend_requests > 0:
                 actions.append({
                    "type": "accept_friend_request",
                    "description": "Accept friend request found while exploring"
                })

        
        return base_actions + actions
    
    async def get_action_recommendations(
        self,
        avatar_id: str,
        limit: int = 5,
        character_profile: Optional[Dict[str, Any]] = None,
        permissions: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ranked action recommendations
        
        Returns:
            List of actions sorted by utility score
        """
        try:
            internal_state, external_state = await self.state_manager.get_current_state(avatar_id)
            current_state, _ = await self.state_machine.get_current_state(avatar_id)
            
            # Get available actions
            available_actions = await self._get_available_actions(
                avatar_id,
                current_state,
                internal_state,
                external_state
            )
            
            # Filter eligible
            eligible_actions = await self.action_eligibility.get_eligible_actions(
                available_actions,
                current_state,
                internal_state,
                external_state,
                permissions
            )
            
            # Calculate utilities
            recommendations = []
            for action in eligible_actions:
                utility = await self.action_utility.calculate_utility(
                    action,
                    internal_state,
                    external_state,
                    character_profile
                )
                recommendations.append({
                    "action": action,
                    "utility": utility,
                    "cooldown_remaining": self.action_eligibility.get_cooldown_remaining(
                        action.get("type"),
                        internal_state
                    )
                })
            
            # Sort by utility
            recommendations.sort(key=lambda x: x["utility"], reverse=True)
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting action recommendations for {avatar_id}: {e}")
            return []


# Import required modules
from datetime import datetime, timezone
from domain.avatar.behavior_tree import NodeStatus

