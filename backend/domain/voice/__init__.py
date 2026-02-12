"""
Voice Module - Real-time voice agent for avatar communication
Uses OpenAI Realtime API with dynamic prompts based on avatar state
"""

from .prompt_generator import VoicePromptGenerator
from .voice_config import VoiceConfig, VOICE_SETTINGS, VOICE_TOOLS
from .social_context import SocialContextService
from .voice_memory import VoiceMemoryService
from .memory_orchestrator import MemoryOrchestrator
from .conversation_recall import ConversationRecallService

__all__ = [
    'VoicePromptGenerator',
    'VoiceConfig',
    'VOICE_SETTINGS',
    'VOICE_TOOLS',
    'SocialContextService',
    'VoiceMemoryService',
    'MemoryOrchestrator',
    'ConversationRecallService',
]
