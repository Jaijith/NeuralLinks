"""
Action Utility Calculator
Calculates utility scores for potential actions with MEMORY integration
"""
from typing import Dict, Any, Optional, List
from domain.avatar.state import InternalState, ExternalState
import logging

logger = logging.getLogger(__name__)


class ActionUtility:
    """
    Calculates utility score for each available action with MEMORY integration
    
    Utility factors:
    1. Character alignment (does action match personality?)
    2. State alignment (does action match current state?)
    3. Relationship context (does action strengthen relationships?)
    4. Opportunity cost (what else could be done?)
    5. Recent history (has this been done too much?)
    6. Expected outcome (predicted engagement/response)
    7. MEMORY alignment (does action align with interests/past success?) [NEW]
    """
    
    def __init__(self):
        self.action_history: Dict[str, List[float]] = {}  # action_type -> [recent utilities]
    
    async def calculate_utility(
        self,
        action: Dict[str, Any],
        internal_state: InternalState,
        external_state: ExternalState,
        character_profile: Optional[Dict[str, Any]] = None,
        memory_context: Optional[Dict[str, Any]] = None  # NEW: Memory context
    ) -> float:
        """
        Calculate utility score (0.0 - 1.0) for an action with MEMORY integration
        
        Args:
            action: Action dictionary with type, parameters, etc.
            internal_state: Current internal state
            external_state: Current external state
            character_profile: Optional character profile
            memory_context: Optional memory context (interests, past actions, experiences)
        
        Returns:
            Utility score (0.0 - 1.0)
        """
        try:
            action_type = action.get("type", "unknown")
            
            # Base utility components
            character_alignment = self._calculate_character_alignment(
                action_type, character_profile, internal_state
            )
            
            state_alignment = self._calculate_state_alignment(
                action_type, internal_state, external_state
            )
            
            relationship_context = self._calculate_relationship_context(
                action, external_state
            )
            
            opportunity_cost = self._calculate_opportunity_cost(
                action_type, external_state
            )
            
            recent_history = self._calculate_recent_history(
                action_type, internal_state
            )
            
            expected_outcome = self._calculate_expected_outcome(
                action_type, external_state
            )
            
            # NEW: Memory alignment score
            memory_alignment = self._calculate_memory_alignment(
                action, memory_context
            )
            
            # Weighted combination (adjusted weights to include memory)
            utility = (
                character_alignment * 0.20 +
                state_alignment * 0.15 +
                relationship_context * 0.15 +
                opportunity_cost * 0.10 +
                recent_history * 0.10 +
                expected_outcome * 0.10 +
                memory_alignment * 0.20  # NEW: Memory has significant weight
            )
            
            # Apply memory penalty if action was marked as repetitive
            memory_penalty = action.get("memory_penalty", 0.0)
            utility = utility * (1.0 - memory_penalty)
            
            # Boost for interest-aligned actions
            if action.get("interest_aligned"):
                utility *= 1.15  # 15% boost for interest-aligned actions
            
            # Store in history
            if action_type not in self.action_history:
                self.action_history[action_type] = []
            self.action_history[action_type].append(utility)
            
            # Keep only last 10 utilities
            if len(self.action_history[action_type]) > 10:
                self.action_history[action_type] = self.action_history[action_type][-10:]
            
            return max(0.0, min(1.0, utility))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.error(f"Error calculating utility for action {action.get('type')}: {e}")
            return 0.0
    
    def _calculate_memory_alignment(
        self,
        action: Dict[str, Any],
        memory_context: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate how well action aligns with memory (interests, past success, experiences)
        
        NEW: This is the key integration point for memory-informed decisions
        """
        if not memory_context:
            return 0.5  # Neutral if no memory context
        
        action_type = action.get("type", "unknown")
        alignment = 0.5  # Base alignment
        
        # Get memory components
        semantic_memory = memory_context.get("semantic_memory", {})
        procedural_memory = memory_context.get("procedural_memory", {})
        episodic_memory = memory_context.get("episodic_memory", {})
        
        # 1. Interest alignment (semantic memory)
        interests = semantic_memory.get("interests", [])
        if action.get("topic") and interests:
            topic = action.get("topic", "").lower()
            if topic in [i.lower() for i in interests]:
                alignment += 0.3  # Topic matches interests
        
        if action.get("interest_aligned"):
            alignment += 0.2  # Already marked as interest-aligned
        
        # 2. Past success alignment (procedural memory)
        success_rates = procedural_memory.get("action_patterns", {}).get("success_rates", {})
        action_success_rate = success_rates.get(action_type, 0.5)
        
        if action_success_rate > 0.7:
            alignment += 0.2  # This action type has been successful
        elif action_success_rate < 0.3:
            alignment -= 0.2  # This action type has been failing
        
        # Check if this is the best performing action
        best_performing = procedural_memory.get("best_performing_action")
        if best_performing == action_type:
            alignment += 0.15  # This is the avatar's best action
        
        # 3. Emotional alignment (episodic memory)
        emotional_state = episodic_memory.get("emotional_state", {})
        emotional_trend = emotional_state.get("emotional_trend", "stable")
        
        # If emotional trend is declining, prefer social actions (to improve mood)
        if emotional_trend == "declining":
            if action_type in ["message_friend", "like_post", "comment_on_post"]:
                alignment += 0.1  # Social actions might improve mood
        
        # If emotional trend is improving, continue with current patterns
        if emotional_trend == "improving":
            alignment += 0.05  # Keep doing what's working
        
        # 4. Relationship memory alignment
        if action.get("friend_id") or action.get("target_friend_id"):
            target_id = action.get("friend_id") or action.get("target_friend_id")
            # Check if we have shared interests with this person
            if action.get("shared_interests"):
                alignment += 0.15 * min(len(action.get("shared_interests", [])), 3) / 3
        
        return max(0.0, min(1.0, alignment))
    
    def _calculate_character_alignment(
        self,
        action_type: str,
        character_profile: Optional[Dict[str, Any]],
        internal_state: InternalState
    ) -> float:
        """Calculate how well action aligns with character"""
        if not character_profile:
            return 0.5  # Neutral if no character profile
        
        # Support both Dict and CharacterProfile object
        if hasattr(character_profile, 'get_action_modifier'):
            # It's a CharacterProfile object
            base_preference = character_profile.get_action_modifier(action_type) / 2.0  # Convert modifier to 0-1
        else:
            # It's a dictionary
            archetype = character_profile.get("archetype", "general")
            action_preferences = character_profile.get("action_preferences", {})
            base_preference = action_preferences.get(action_type, 0.5)
        
        # Adjust based on current mood/state
        mood_modifier = 1.0
        if action_type == "create_post" and internal_state.creative_urge > 0.7:
            mood_modifier = 1.2
        elif action_type in ["like_post", "comment_on_post"] and internal_state.social_desire > 0.7:
            mood_modifier = 1.2
        elif action_type == "message_friend" and internal_state.social_desire > 0.8:
            mood_modifier = 1.3
        
        return min(1.0, base_preference * mood_modifier)
    
    def _calculate_state_alignment(
        self,
        action_type: str,
        internal_state: InternalState,
        external_state: ExternalState
    ) -> float:
        """Calculate how well action aligns with current state"""
        alignment = 0.5  # Base alignment
        
        # Check energy level
        if internal_state.energy_level < 0.3:
            # Low energy - prefer passive actions
            if action_type in ["create_post", "discover_profiles"]:
                alignment -= 0.3
            elif action_type in ["like_post", "read_messages"]:
                alignment += 0.2
        
        # Check social desire
        if internal_state.social_desire > 0.7:
            if action_type in ["message_friend", "like_post", "comment_on_post"]:
                alignment += 0.3
        elif internal_state.social_desire < 0.3:
            if action_type in ["message_friend", "send_friend_request"]:
                alignment -= 0.3
        
        # Check creative urge
        if internal_state.creative_urge > 0.7:
            if action_type == "create_post":
                alignment += 0.4
        elif internal_state.creative_urge < 0.3:
            if action_type == "create_post":
                alignment -= 0.3
        
        # Check external state
        if external_state.has_unread_interactions():
            if action_type == "message_friend":
                alignment += 0.3
        
        return max(0.0, min(1.0, alignment))
    
    def _calculate_relationship_context(
        self,
        action: Dict[str, Any],
        external_state: ExternalState
    ) -> float:
        """Calculate relationship benefit of action"""
        action_type = action.get("type", "unknown")
        target_friend_id = action.get("friend_id") or action.get("target_id")
        
        if not target_friend_id:
            # No specific friend target
            if action_type == "create_post":
                # Creating posts can strengthen all relationships
                return 0.6
            return 0.5
        
        # Get relationship strength
        relationship_map = external_state.get_relationship_map()
        relationship_data = relationship_map.get(target_friend_id, {})
        strength = relationship_data.get("strength_score", 0.5)
        
        # Actions that strengthen relationships
        if action_type in ["message_friend", "comment_on_post", "like_post"]:
            # Higher utility for stronger relationships (maintain them)
            # But also utility for weaker relationships (strengthen them)
            if strength > 0.7:
                return 0.8  # Maintain strong relationships
            elif strength < 0.3:
                return 0.7  # Strengthen weak relationships
            else:
                return 0.6
        
        return 0.5
    
    def _calculate_opportunity_cost(
        self,
        action_type: str,
        external_state: ExternalState
    ) -> float:
        """Calculate opportunity cost (inverse - higher means better opportunity)"""
        # If there are many opportunities, cost is lower (higher utility)
        if action_type == "like_post" or action_type == "comment_on_post":
            opportunities = external_state.get_content_opportunities()
            if len(opportunities) > 5:
                return 0.8  # Many opportunities
            elif len(opportunities) > 0:
                return 0.6
            else:
                return 0.3  # No opportunities
        
        elif action_type == "message_friend":
            if external_state.unread_messages > 0:
                return 0.8  # High opportunity (unread messages)
            else:
                return 0.4
        
        elif action_type == "create_post":
            # Check if it's a good time to post
            if external_state.friend_activity_level > 0.5:
                return 0.7  # Good time (friends are active)
            else:
                return 0.5
        
        return 0.5
    
    def _calculate_recent_history(
        self,
        action_type: str,
        internal_state: InternalState
    ) -> float:
        """Calculate utility based on recent action history"""
        # Check temporal states
        if action_type == "create_post":
            # Prefer if enough time has passed
            hours_since = internal_state.time_since_last_post.total_seconds() / 3600
            if hours_since > 12:
                return 0.8  # Good time to post
            elif hours_since > 6:
                return 0.6
            else:
                return 0.3  # Too soon
        
        elif action_type == "message_friend":
            hours_since = internal_state.time_since_last_conversation.total_seconds() / 3600
            if hours_since > 24:
                return 0.7  # Good time to message
            elif hours_since > 6:
                return 0.5
            else:
                return 0.3  # Too soon
        
        elif action_type in ["like_post", "comment_on_post"]:
            hours_since = internal_state.time_since_last_reaction.total_seconds() / 3600
            if hours_since > 2:
                return 0.7  # Good time to react
            elif hours_since > 1:
                return 0.5
            else:
                return 0.4  # Can react more frequently
        
        elif action_type == "browse_feed":
            # Heavy penalty if browsed recently to prevent spamming
            # Browse feed should be a filler action, not the main activity
            if action_type in self.action_history and len(self.action_history[action_type]) > 0:
                # If we just did it, utility drops significantly
                return 0.1
            return 0.4
        
        return 0.5
    
    def _calculate_expected_outcome(
        self,
        action_type: str,
        external_state: ExternalState
    ) -> float:
        """Calculate expected outcome/engagement"""
        if action_type == "create_post":
            # Expected engagement based on friend activity
            if external_state.friend_activity_level > 0.5:
                return 0.7  # Friends are active, likely to engage
            else:
                return 0.5
        
        elif action_type in ["like_post", "comment_on_post"]:
            # Expected response based on content opportunities
            opportunities = external_state.get_content_opportunities()
            if len(opportunities) > 0:
                # Posts with engagement are more likely to respond
                return 0.7
            else:
                return 0.4
        
        elif action_type == "message_friend":
            # Expected response based on relationship strength
            if external_state.unread_messages > 0:
                return 0.8  # High chance of response (they messaged first)
            else:
                return 0.5
        
        return 0.5
    
    def get_average_utility(self, action_type: str) -> float:
        """Get average utility for an action type"""
        if action_type not in self.action_history or not self.action_history[action_type]:
            return 0.5
        
        utilities = self.action_history[action_type]
        return sum(utilities) / len(utilities)

