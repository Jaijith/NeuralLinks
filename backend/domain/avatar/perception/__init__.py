"""
Perception module for avatar environment awareness

This module provides comprehensive perception of the avatar's environment,
including social network activity, relationships, and environmental context.
"""
from .engine import PerceptionEngine
from .social_network import SocialNetworkPerception
from .relationship import RelationshipPerception
from .environment import EnvironmentPerception

__all__ = [
    'PerceptionEngine',
    'SocialNetworkPerception',
    'RelationshipPerception',
    'EnvironmentPerception'
]

