"""
Voice Module - Real-time voice agent for avatar communication
Uses OpenAI Realtime API with dynamic prompts based on avatar state
"""

from .prompt_generator import VoicePromptGenerator
from .voice_config import VoiceConfig, VOICE_SETTINGS

__all__ = [
    'VoicePromptGenerator',
    'VoiceConfig',
    'VOICE_SETTINGS'
]
