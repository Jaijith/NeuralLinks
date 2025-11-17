"""
Avatar domain - Intelligent avatar and autonomous agents
"""

from .intelligent import IntelligentAvatar
from .agent import SimpleReactiveAgent
from .manager import SimpleAgentManager
from .config import (
    ARCHETYPES,
    assign_archetype_to_bot,
    get_archetype_config,
    should_bot_act,
    get_conversation_length,
    get_post_delay_hours,
    get_post_prompt
)

__all__ = [
    'IntelligentAvatar',
    'SimpleReactiveAgent',
    'SimpleAgentManager',
    'ARCHETYPES',
    'assign_archetype_to_bot',
    'get_archetype_config',
    'should_bot_act',
    'get_conversation_length',
    'get_post_delay_hours',
    'get_post_prompt'
]

