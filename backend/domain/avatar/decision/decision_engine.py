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
            
            # Log available actions by type for debugging
            action_types_available = [a.get("type") for a in available_actions] if available_actions else []
            unique_action_types = list(set(action_types_available))
            logger.info(f"Decision Engine for {avatar_id}: {len(available_actions) if available_actions else 0} available actions in state {current_state.value}")
            logger.info(f"Decision Engine for {avatar_id}: Action types available: {unique_action_types}")
            
            if not available_actions:
                logger.warning(f"No available actions for {avatar_id} in state {current_state.value}")
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
            
            # Log eligible actions by type for debugging
            eligible_action_types = [a.get("type") for a in eligible_actions] if eligible_actions else []
            unique_eligible_types = list(set(eligible_action_types))
            logger.info(f"Decision Engine for {avatar_id}: {len(eligible_actions) if eligible_actions else 0} eligible actions after filtering")
            logger.info(f"Decision Engine for {avatar_id}: Eligible action types: {unique_eligible_types}")
            
            if not eligible_actions:
                logger.warning(f"No eligible actions for {avatar_id} after filtering (available: {len(available_actions) if available_actions else 0})")
                logger.warning(f"Decision Engine for {avatar_id}: Available action types were: {unique_action_types}")
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
                # Log top 3 actions for debugging
                top_3 = [(a.get("type"), u) for a, u in action_scores[:3]]
                logger.info(f"Decision Engine for {avatar_id}: Top 3 actions by utility: {top_3}")
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
        
        logger.info(f"📝 Memory filter for {avatar_id}: {len(eligible_actions)} actions passed eligibility")
        
        # If no memory context or memory manager, return standard filtered actions
        if not memory_context or not self.memory_manager:
            logger.info(f"📝 No memory context/manager, returning {len(eligible_actions)} eligible actions")
            return eligible_actions
        
        # Apply memory-based filtering
        memory_filtered = []
        procedural_memory = memory_context.get("procedural_memory", {})
        actions_to_avoid = procedural_memory.get("actions_to_avoid", [])
        recent_repetition = procedural_memory.get("action_patterns", {}).get("recent_repetition", {})
        
        logger.info(f"📝 Memory context: actions_to_avoid={actions_to_avoid}, recent_repetition keys={list(recent_repetition.keys())}")
        
        for action in eligible_actions:
            action_type = action.get("type")
            
            # Skip actions that have been failing
            if action_type in actions_to_avoid:
                logger.warning(f"📝 Skipping {action_type} - in actions_to_avoid list")
                continue
            
            # Reduce priority of recently repeated actions (but don't skip entirely)
            repetition_count = recent_repetition.get(action_type, 0)
            if repetition_count >= 3:
                # Mark as lower priority but don't skip
                action["memory_penalty"] = 0.3 * repetition_count
                logger.info(f"📝 Action {action_type} penalized by {action['memory_penalty']} for repetition")
            
            memory_filtered.append(action)
        
        logger.info(f"📝 After memory filter: {len(memory_filtered)} actions remain (types: {[a.get('type') for a in memory_filtered]})")
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
            
            # ============================================================
            # MESSAGING: Prioritize responses, then rotate through friends
            # ============================================================
            relationship_map = external_state.get_relationship_map()
            
            # 1. PRIORITY: Respond to friends who messaged us (check unread)
            friends_who_messaged = await self._get_friends_awaiting_response(avatar_id, relationship_map)
            for friend_id in friends_who_messaged[:2]:  # Respond to up to 2 friends
                actions.append({
                    "type": "message_friend",
                    "description": f"Respond to {friend_id}'s message",
                    "friend_id": friend_id,
                    "is_response": True,  # Mark as response (higher priority)
                    "priority": "high"
                })
            
            # 2. Proactive messaging - rotate through friends (not always the same one)
            if relationship_map and internal_state.social_desire > 0.4:
                # Get recently messaged friends to avoid
                recently_messaged = await self._get_recently_messaged_friends(avatar_id, hours=24)
                
                # Get all friends and shuffle for variety
                import random
                friend_list = list(relationship_map.items())
                random.shuffle(friend_list)  # Randomize to avoid always picking same friend
                
                # Pick a friend we haven't messaged recently
                for friend_id, rel_data in friend_list:
                    if friend_id not in recently_messaged and friend_id not in friends_who_messaged:
                        actions.append({
                            "type": "message_friend",
                            "description": f"Reach out to friend",
                            "friend_id": friend_id,
                            "relationship_strength": rel_data.get("strength_score", 0.5),
                            "proactive": True
                        })
                        break  # Only add one proactive message action
            
            # ============================================================
            # NEW: CREATE POST IN ACTIVE STATE - when creative urge is building
            # This allows posting without needing to transition to CREATIVE
            # ============================================================
            if internal_state.creative_urge > 0.5 and internal_state.time_since_last_post > timedelta(hours=2):
                most_active_interest = interest_perception.get("most_active_interest")
                actions.append({
                    "type": "create_post",
                    "description": "Share a thought or update",
                    "post_type": "spontaneous",
                    "topic": most_active_interest,
                    "interest_aligned": bool(most_active_interest)
                })
            
            # Discover profiles
            actions.append({
                "type": "discover_profiles",
                "description": "Discover new profiles"
            })
        
        elif current_state == TopLevelState.SOCIAL:
            # ============================================================
            # SOCIAL STATE: Prioritize responses, then rotate through friends
            # ============================================================
            relationship_map = external_state.get_relationship_map()
            aligned_users = interest_perception.get("interest_aligned_users", [])
            aligned_user_ids = {u.get("user_id") for u in aligned_users}
            
            # 1. PRIORITY: Respond to friends who messaged us
            friends_who_messaged = await self._get_friends_awaiting_response(avatar_id, relationship_map)
            for friend_id in friends_who_messaged[:2]:
                actions.append({
                    "type": "message_friend",
                    "description": f"Respond to {friend_id}'s message",
                    "friend_id": friend_id,
                    "is_response": True,
                    "priority": "high"
                })
            
            # 2. Proactive messaging - rotate through friends
            recently_messaged = await self._get_recently_messaged_friends(avatar_id, hours=12)
            import random
            friend_list = list(relationship_map.keys())
            random.shuffle(friend_list)
            
            proactive_count = 0
            for friend_id in friend_list:
                if friend_id not in recently_messaged and friend_id not in friends_who_messaged:
                    is_aligned = friend_id in aligned_user_ids
                    actions.append({
                        "type": "message_friend",
                        "description": f"Message {friend_id}",
                        "friend_id": friend_id,
                        "interest_aligned": is_aligned
                })
                    proactive_count += 1
                    if proactive_count >= 2:  # Limit to 2 proactive messages
                        break
            
            # Review friend requests
            if external_state.pending_friend_requests > 0:
                actions.append({
                    "type": "accept_friend_request",
                    "description": "Review friend requests"
                })
            
            # NEW: Add create_post to SOCIAL state - share thoughts with friends
            most_active_interest = interest_perception.get("most_active_interest")
            actions.append({
                "type": "create_post",
                "description": "Share a thought with friends",
                "post_type": "social",
                "topic": most_active_interest,
                "interest_aligned": bool(most_active_interest)
            })
            
            # NEW: Add like/comment actions for SOCIAL state
            recent_posts = external_state.get_recent_posts(limit=5)
            for post in recent_posts[:2]:
                post_id = post.get("id")
                actions.append({
                    "type": "like_post",
                    "description": f"Like friend's post",
                    "post_id": post_id,
                    "target_friend_id": post.get("user_id")
                })
                actions.append({
                    "type": "comment_on_post",
                    "description": f"Comment on friend's post",
                    "post_id": post_id,
                    "target_friend_id": post.get("user_id")
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
            # LOWERED threshold from 0.5 to 0.4 to make posting more likely
            if internal_state.creative_urge > 0.4:
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
            
            # ============================================================
            # NEW: PROACTIVE MESSAGING while exploring
            # Sometimes want to share discoveries with friends
            # ============================================================
            relationship_map = external_state.get_relationship_map()
            if relationship_map and internal_state.social_desire > 0.4:
                # Rotate through friends instead of always picking the same ones
                import random
                recently_messaged = await self._get_recently_messaged_friends(avatar_id, hours=12)
                friend_list = list(relationship_map.keys())
                random.shuffle(friend_list)
                
                for friend_id in friend_list:
                    if friend_id not in recently_messaged:
                        actions.append({
                            "type": "message_friend",
                            "description": "Share discovery with friend",
                            "friend_id": friend_id,
                            "proactive": True
                        })
                        break  # Only share with one friend at a time

        
        return base_actions + actions
    
    async def _get_friends_awaiting_response(
        self,
        avatar_id: str,
        relationship_map: Dict[str, Any]
    ) -> List[str]:
        """
        Get list of friends who have sent messages we haven't responded to.
        These friends should be prioritized for messaging.
        """
        friends_awaiting = []
        
        try:
            from core.database import get_database
            db = get_database()
            
            for friend_id in relationship_map.keys():
                # Get the conversation between avatar and friend
                user_ids = sorted([avatar_id, friend_id])
                conversation = await db.agent_conversations.find_one({
                    "agent1_user_id": user_ids[0],
                    "agent2_user_id": user_ids[1]
                })
                
                if conversation and conversation.get("messages"):
                    messages = conversation["messages"]
                    if messages:
                        last_message = messages[-1]
                        # If the last message was from the friend (not us), we should respond
                        if last_message.get("sender") == friend_id:
                            friends_awaiting.append(friend_id)
        except Exception as e:
            logger.warning(f"Error getting friends awaiting response: {e}")
        
        return friends_awaiting
    
    async def _get_recently_messaged_friends(
        self,
        avatar_id: str,
        hours: int = 24
    ) -> set:
        """
        Get set of friend IDs we've messaged recently (to avoid messaging same person)
        """
        recently_messaged = set()
        
        try:
            from core.database import get_database
            from datetime import timedelta
            db = get_database()
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Find all conversations where we sent a message recently
            conversations = await db.agent_conversations.find({
                "$or": [
                    {"agent1_user_id": avatar_id},
                    {"agent2_user_id": avatar_id}
                ]
            }).to_list(100)
            
            for conv in conversations:
                # Get the friend's ID
                if conv.get("agent1_user_id") == avatar_id:
                    friend_id = conv.get("agent2_user_id")
                else:
                    friend_id = conv.get("agent1_user_id")
                
                # Check if we sent a message recently
                for msg in reversed(conv.get("messages", [])):
                    if msg.get("sender") == avatar_id:
                        msg_time = msg.get("timestamp")
                        if msg_time:
                            if isinstance(msg_time, str):
                                msg_time = datetime.fromisoformat(msg_time.replace('Z', '+00:00'))
                            if msg_time > cutoff_time:
                                recently_messaged.add(friend_id)
                        break  # Only check the most recent message from us
        except Exception as e:
            logger.warning(f"Error getting recently messaged friends: {e}")
        
        return recently_messaged
    
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
from datetime import datetime, timezone, timedelta
from domain.avatar.behavior_tree import NodeStatus

