"""
Personality module — deep personalization for avatars.
Generates dynamic, per-avatar personality prompts and style profiles.
"""
from .personality_prompt import PersonalityPromptGenerator
from .style_learner import StyleLearner
from .knowledge_gaps import KnowledgeGapTracker

__all__ = [
    'PersonalityPromptGenerator',
    'StyleLearner',
    'KnowledgeGapTracker',
]
