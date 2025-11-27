"""
State Transition Logic
Defines rules and conditions for state transitions
"""
import random
from typing import Callable, List, Dict, Any, Optional
from datetime import timedelta
from enum import Enum
from pydantic import BaseModel, Field
from domain.avatar.state import InternalState, ExternalState


class TopLevelState(str, Enum):
    """Top-level states for avatar behavior"""
    ACTIVE = "active"           # Avatar is actively engaging
    PASSIVE = "passive"         # Avatar is observing/reflecting
    CREATIVE = "creative"       # Avatar is creating content
    SOCIAL = "social"          # Avatar is socializing
    EXPLORING = "exploring"     # Avatar is discovering new content/people
    RESTING = "resting"        # Avatar is inactive (cooldown)


class ActiveSubState(str, Enum):
    """Sub-states within ACTIVE state"""
    REACTING = "reacting"       # Reacting to friend activity
    RESPONDING = "responding"   # Responding to direct interactions
    INITIATING = "initiating"   # Initiating new interactions
    ENGAGING = "engaging"       # Engaging with content


class SocialSubState(str, Enum):
    """Sub-states within SOCIAL state"""
    MESSAGING = "messaging"              # Having conversations
    FRIEND_BUILDING = "friend_building"  # Building new relationships
    MAINTAINING = "maintaining"          # Maintaining existing relationships


class CreativeSubState(str, Enum):
    """Sub-states within CREATIVE state"""
    POSTING = "posting"         # Creating posts
    SHARING = "sharing"         # Sharing content
    COMMENTING = "commenting"   # Writing thoughtful comments


class StateTransitionRule(BaseModel):
    """
    Defines a state transition rule
    
    A transition rule specifies:
    - When to transition (conditions)
    - What state to transition to
    - What actions to take on enter/exit
    - Probability modifiers based on character
    - Epsilon-greedy probability for exploratory transitions
    """
    
    from_state: TopLevelState
    to_state: TopLevelState
    conditions: List[str] = Field(default_factory=list)  # Condition descriptions
    condition_functions: List[Callable] = Field(default_factory=list)  # Actual condition checks
    probability_modifiers: Dict[str, float] = Field(default_factory=dict)  # archetype -> modifier
    on_enter_actions: List[str] = Field(default_factory=list)  # Actions to take on entering state
    on_exit_actions: List[str] = Field(default_factory=list)  # Actions to take on exiting state
    during_actions: List[str] = Field(default_factory=list)  # Actions while in state
    priority: int = Field(default=0)  # Higher priority transitions are evaluated first
    epsilon_probability: float = Field(default=0.0)  # Epsilon-greedy: probability to transition even if conditions not fully met (0.0-1.0)
    epsilon_mood_modifiers: Dict[str, float] = Field(default_factory=dict)  # mood -> probability multiplier for epsilon
    
    def evaluate_conditions(
        self,
        internal_state: InternalState,
        external_state: ExternalState
    ) -> bool:
        """
        Evaluate if transition conditions are met
        
        Returns:
            True if all conditions are met, False otherwise
        """
        if not self.condition_functions:
            return False
        
        # All conditions must be true
        for condition_func in self.condition_functions:
            try:
                if not condition_func(internal_state, external_state):
                    return False
            except Exception as e:
                # If condition evaluation fails, don't transition
                return False
        
        return True
    
    def get_probability_modifier(self, archetype: str) -> float:
        """Get probability modifier for given archetype"""
        return self.probability_modifiers.get(archetype, 1.0)


# Define transition rules
def create_transition_rules() -> List[StateTransitionRule]:
    """
    Create all state transition rules
    
    Returns:
        List of StateTransitionRule objects
    """
    rules = []
    
    # Transition: PASSIVE -> ACTIVE (Epsilon-Greedy)
    # Epsilon-greedy: Low probability to transition even when conditions not fully met
    # Based on mood and character - creates diversity and breaks deadlocks
    rules.append(StateTransitionRule(
        from_state=TopLevelState.PASSIVE,
        to_state=TopLevelState.ACTIVE,
        conditions=[
            "epsilon-greedy: mood-based probabilistic transition",
            "energy_level > 0.3"  # Only requirement: some energy
        ],
        condition_functions=[
            lambda i, e: i.energy_level > 0.3  # Minimal requirement
        ],
        probability_modifiers={
            "social_butterfly": 1.5,
            "enthusiastic_newcomer": 1.4,
            "introvert": 0.6,
            "thinker": 0.8,
            "thoughtful_contributor": 0.9
        },
        epsilon_probability=0.15,  # 15% base chance to explore (transition even if conditions not met)
        epsilon_mood_modifiers={
            "curious": 1.5,          # Curious avatars more likely to explore
            "excited": 1.8,          # Excited avatars very likely
            "restless": 1.6,         # Restless avatars want action
            "bored": 1.4,            # Bored avatars seek activity
            "happy": 1.3,            # Happy avatars more active
            "neutral": 1.0,          # Neutral: base probability
            "contemplative": 0.7,    # Contemplative: less likely to act impulsively
            "calm": 0.8,             # Calm: slightly less likely
            "social": 1.4,           # Social mood: more likely to engage
            "creative": 1.2          # Creative mood: more likely to explore
        },
        on_enter_actions=["update_activity_timestamp"],
        priority=6  # Higher priority than regular transition
    ))
    
    # Transition: PASSIVE -> ACTIVE (Regular - when conditions fully met)
    # Condition: High friend activity, high social desire, sufficient energy
    rules.append(StateTransitionRule(
        from_state=TopLevelState.PASSIVE,
        to_state=TopLevelState.ACTIVE,
        conditions=[
            "friend_activity_level > 0.5",
            "social_desire > 0.6",
            "energy_level > 0.4"
        ],
        condition_functions=[
            lambda i, e: e.friend_activity_level > 0.5,
            lambda i, e: i.social_desire > 0.6,
            lambda i, e: i.energy_level > 0.4
        ],
        probability_modifiers={
            "social_butterfly": 1.5,
            "introvert": 0.7,
            "thinker": 0.8
        },
        on_enter_actions=["update_activity_timestamp"],
        priority=5
    ))
    
    # Transition: ACTIVE -> CREATIVE
    # Condition: High creative urge, sufficient time since last post, content opportunities
    rules.append(StateTransitionRule(
        from_state=TopLevelState.ACTIVE,
        to_state=TopLevelState.CREATIVE,
        conditions=[
            "creative_urge > 0.7",
            "time_since_last_post > 6 hours",
            "content_opportunities exist"
        ],
        condition_functions=[
            lambda i, e: i.creative_urge > 0.7,
            lambda i, e: i.time_since_last_post > timedelta(hours=6),
            lambda i, e: len(e.get_content_opportunities()) > 0
        ],
        probability_modifiers={
            "creative": 1.5,
            "thinker": 1.2,
            "social_butterfly": 0.8
        },
        on_enter_actions=["set_creative_focus"],
        priority=4
    ))
    
    # Transition: ACTIVE -> SOCIAL
    # Condition: Unread messages or pending requests, high social desire
    rules.append(StateTransitionRule(
        from_state=TopLevelState.ACTIVE,
        to_state=TopLevelState.SOCIAL,
        conditions=[
            "unread_messages > 0 OR pending_friend_requests > 0",
            "social_desire > 0.5"
        ],
        condition_functions=[
            lambda i, e: e.has_unread_interactions(),
            lambda i, e: i.social_desire > 0.5
        ],
        probability_modifiers={
            "social_butterfly": 1.5,
            "introvert": 0.6,
            "thinker": 0.7
        },
        on_enter_actions=["check_unread_interactions"],
        priority=6  # High priority - respond to direct interactions
    ))
    
    # Transition: ACTIVE -> EXPLORING
    # Condition: Low activity, high curiosity, sufficient energy
    rules.append(StateTransitionRule(
        from_state=TopLevelState.ACTIVE,
        to_state=TopLevelState.EXPLORING,
        conditions=[
            "friend_activity_level < 0.3",
            "energy_level > 0.5",
            "time_since_last_action > 2 hours"
        ],
        condition_functions=[
            lambda i, e: e.friend_activity_level < 0.3,
            lambda i, e: i.energy_level > 0.5,
            lambda i, e: i.time_since_last_action > timedelta(hours=2)
        ],
        probability_modifiers={
            "explorer": 1.5,
            "thinker": 1.2,
            "social_butterfly": 0.7
        },
        on_enter_actions=["set_exploration_target"],
        priority=3
    ))
    
    # Transition: ACTIVE -> RESTING
    # Condition: Low energy, long time since last action
    rules.append(StateTransitionRule(
        from_state=TopLevelState.ACTIVE,
        to_state=TopLevelState.RESTING,
        conditions=[
            "energy_level < 0.2",
            "time_since_last_action > 4 hours"
        ],
        condition_functions=[
            lambda i, e: i.energy_level < 0.2,
            lambda i, e: i.time_since_last_action > timedelta(hours=4)
        ],
        probability_modifiers={
            "introvert": 1.3,
            "social_butterfly": 0.6
        },
        on_enter_actions=["start_cooldown"],
        priority=2
    ))
    
    # Transition: CREATIVE -> ACTIVE
    # Condition: Post created or creative urge satisfied
    rules.append(StateTransitionRule(
        from_state=TopLevelState.CREATIVE,
        to_state=TopLevelState.ACTIVE,
        conditions=[
            "creative_urge < 0.4",
            "time_since_last_post < 1 hour"
        ],
        condition_functions=[
            lambda i, e: i.creative_urge < 0.4,
            lambda i, e: i.time_since_last_post < timedelta(hours=1)
        ],
        probability_modifiers={},  # Universal transition
        on_exit_actions=["reset_creative_urge"],
        priority=3
    ))
    
    # Transition: SOCIAL -> ACTIVE
    # Condition: Interactions handled, social desire satisfied
    rules.append(StateTransitionRule(
        from_state=TopLevelState.SOCIAL,
        to_state=TopLevelState.ACTIVE,
        conditions=[
            "unread_messages == 0",
            "pending_friend_requests == 0",
            "social_desire < 0.5"
        ],
        condition_functions=[
            lambda i, e: e.unread_messages == 0,
            lambda i, e: e.pending_friend_requests == 0,
            lambda i, e: i.social_desire < 0.5
        ],
        probability_modifiers={},  # Universal transition
        on_exit_actions=["update_social_timestamp"],
        priority=4
    ))
    
    # Transition: EXPLORING -> ACTIVE
    # Condition: Exploration complete or new content found
    rules.append(StateTransitionRule(
        from_state=TopLevelState.EXPLORING,
        to_state=TopLevelState.ACTIVE,
        conditions=[
            "time_since_last_action < 30 minutes",
            "friend_activity_level > 0.3 OR epsilon_probability"
        ],
        condition_functions=[
            lambda i, e: i.time_since_last_action < timedelta(minutes=30),
            lambda i, e: e.friend_activity_level > 0.3
        ],
        probability_modifiers={},  # Universal transition
        epsilon_probability=0.2,  # 20% chance to become active anyway if exploring finds something
        on_exit_actions=["update_exploration_results"],
        priority=3
    ))

    # Transition: EXPLORING -> PASSIVE
    # Condition: Bored of exploring, low energy, or time limit reached
    rules.append(StateTransitionRule(
        from_state=TopLevelState.EXPLORING,
        to_state=TopLevelState.PASSIVE,
        conditions=[
            "time_since_last_action > 1 hour",
            "energy_level < 0.4"
        ],
        condition_functions=[
            lambda i, e: i.time_since_last_action > timedelta(hours=1),
            lambda i, e: i.energy_level < 0.4
        ],
        probability_modifiers={
            "introvert": 1.2,
            "social_butterfly": 0.8
        },
        on_enter_actions=["enter_observation_mode"],
        priority=2
    ))

    # Transition: EXPLORING -> CREATIVE
    # Condition: Found inspiration while exploring
    rules.append(StateTransitionRule(
        from_state=TopLevelState.EXPLORING,
        to_state=TopLevelState.CREATIVE,
        conditions=[
            "creative_urge > 0.6",
            "energy_level > 0.5"
        ],
        condition_functions=[
            lambda i, e: i.creative_urge > 0.6,
            lambda i, e: i.energy_level > 0.5
        ],
        probability_modifiers={
            "creative": 1.4,
            "thinker": 1.2
        },
        epsilon_probability=0.1, # Random inspiration
        on_enter_actions=["set_creative_focus"],
        priority=3
    ))
    
    # Transition: RESTING -> ACTIVE
    # Condition: Energy restored, cooldown period passed
    rules.append(StateTransitionRule(
        from_state=TopLevelState.RESTING,
        to_state=TopLevelState.ACTIVE,
        conditions=[
            "energy_level > 0.5",
            "time_since_last_action > 1 hour"
        ],
        condition_functions=[
            lambda i, e: i.energy_level > 0.5,
            lambda i, e: i.time_since_last_action > timedelta(hours=1)
        ],
        probability_modifiers={},  # Universal transition
        on_exit_actions=["restore_energy"],
        priority=2
    ))
    
    # Transition: Any -> PASSIVE (fallback)
    # Condition: Low activity, low energy, no immediate needs
    rules.append(StateTransitionRule(
        from_state=TopLevelState.ACTIVE,  # Can transition from any state
        to_state=TopLevelState.PASSIVE,
        conditions=[
            "friend_activity_level < 0.3",
            "energy_level < 0.4",
            "social_desire < 0.4",
            "creative_urge < 0.4",
            "no_unread_interactions"
        ],
        condition_functions=[
            lambda i, e: e.friend_activity_level < 0.3,
            lambda i, e: i.energy_level < 0.4,
            lambda i, e: i.social_desire < 0.4,
            lambda i, e: i.creative_urge < 0.4,
            lambda i, e: not e.has_unread_interactions()
        ],
        probability_modifiers={
            "introvert": 1.2,
            "thinker": 1.1
        },
        on_enter_actions=["enter_observation_mode"],
        priority=1  # Low priority - fallback state
    ))
    
    return rules


def get_transition_rules_for_state(
    current_state: TopLevelState,
    rules: Optional[List[StateTransitionRule]] = None
) -> List[StateTransitionRule]:
    """
    Get all transition rules that can be applied from current state
    
    Args:
        current_state: Current top-level state
        rules: Optional list of rules (if None, creates default rules)
    
    Returns:
        List of applicable transition rules, sorted by priority
    """
    if rules is None:
        rules = create_transition_rules()
    
    applicable_rules = [
        rule for rule in rules
        if rule.from_state == current_state
    ]
    
    # Sort by priority (higher first)
    applicable_rules.sort(key=lambda r: r.priority, reverse=True)
    
    return applicable_rules


def evaluate_state_transitions(
    current_state: TopLevelState,
    internal_state: InternalState,
    external_state: ExternalState,
    archetype: str = "general"
) -> Optional[TopLevelState]:
    """
    Evaluate which state to transition to based on current state and conditions
    
    Uses epsilon-greedy strategy: sometimes transitions even when conditions not fully met
    to create diversity and break deadlocks.
    
    Args:
        current_state: Current top-level state
        internal_state: Current internal state
        external_state: Current external state
        archetype: Avatar archetype (for probability modifiers)
    
    Returns:
        New state to transition to, or None if no transition should occur
    """
    rules = get_transition_rules_for_state(current_state)
    
    # Evaluate rules in priority order
    for rule in rules:
        conditions_met = rule.evaluate_conditions(internal_state, external_state)
        
        # Check epsilon-greedy transition (even if conditions not fully met)
        if rule.epsilon_probability > 0.0:
            # Calculate epsilon probability based on mood
            mood_name = internal_state.mood.value if hasattr(internal_state.mood, 'value') else str(internal_state.mood)
            mood_modifier = rule.epsilon_mood_modifiers.get(mood_name, 1.0)
            
            # Base epsilon probability adjusted by mood
            epsilon_prob = rule.epsilon_probability * mood_modifier
            
            # Apply archetype modifier
            archetype_modifier = rule.get_probability_modifier(archetype)
            epsilon_prob = min(1.0, epsilon_prob * archetype_modifier)
            
            # Random chance to explore (transition)
            if random.random() < epsilon_prob:
                return rule.to_state
        
        # Regular transition (conditions fully met)
        if conditions_met:
            # Apply probability modifier based on archetype
            modifier = rule.get_probability_modifier(archetype)
            
            # If conditions are met and modifier > 0.5, transition
            if modifier > 0.5:
                return rule.to_state
    
    # No transition
    return None

