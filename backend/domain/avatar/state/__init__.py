"""
State module for avatar internal and external state

This module manages the avatar's internal state (mood, energy, desires)
and external state (network activity, relationships, environment).
"""
from .internal_state import InternalState
from .external_state import ExternalState
from .state_manager import StateManager
from .state_models import MoodState, Goal, StateTransition, ActionOutcome, RelationshipSnapshot

__all__ = [
    'InternalState',
    'ExternalState',
    'StateManager',
    'MoodState',
    'Goal',
    'StateTransition',
    'ActionOutcome',
    'RelationshipSnapshot'
]

