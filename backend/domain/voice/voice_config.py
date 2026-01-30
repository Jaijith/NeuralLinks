"""
Voice Configuration
Configuration settings for the OpenAI Realtime Voice API (GA Version)
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class VoiceType(str, Enum):
    """Available OpenAI voices for Realtime API"""
    ALLOY = "alloy"
    ASH = "ash"
    BALLAD = "ballad"
    CORAL = "coral"
    ECHO = "echo"
    SAGE = "sage"
    SHIMMER = "shimmer"
    VERSE = "verse"


class TurnDetectionMode(str, Enum):
    """Voice activity detection modes"""
    SERVER_VAD = "server_vad"  # Server-side voice activity detection
    NONE = "none"  # Push-to-talk only


class VoiceConfig(BaseModel):
    """Configuration for voice session - GA API format"""
    # Model settings - use gpt-4o-realtime for GA
    model: str = Field(default="gpt-4o-realtime-preview-2024-12-17")
    
    # Always use Shimmer voice for intimate, feminine tone
    voice: VoiceType = Field(default=VoiceType.SHIMMER)
    
    # Turn detection with near-field noise removal (None = disabled for push-to-talk)
    turn_detection: Optional[Dict[str, Any]] = Field(default_factory=lambda: {
        "type": "server_vad",
        "threshold": 0.5,  # Sensitivity for voice detection (0.0-1.0)
        "prefix_padding_ms": 300,  # Audio before speech starts
        "silence_duration_ms": 500,  # Silence before end of speech
        "create_response": True  # Auto-respond after user stops speaking
    })
    
    # Temperature for response variation
    temperature: float = Field(default=0.8, ge=0.6, le=1.2)
    
    # Maximum response tokens
    max_response_output_tokens: str = Field(default="inf")
    
    def to_session_config(self, instructions: str) -> Dict[str, Any]:
        """
        Convert to OpenAI GA Realtime session configuration
        
        Format for POST /v1/realtime/client_secrets
        """
        # Build input config
        input_config = {
            "format": {
                "type": "audio/pcm",
                "rate": 24000
            },
            "transcription": {
                "model": "whisper-1"
            }
        }
        
        # Add turn_detection inside audio.input (None = manual/push-to-talk mode)
        if self.turn_detection is not None:
            input_config["turn_detection"] = self.turn_detection
        
        session_config = {
            "session": {
                "type": "realtime",
                "model": self.model,
                "instructions": instructions,
                "audio": {
                    "input": input_config,
                    "output": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": 24000
                        },
                        "voice": self.voice.value
                    }
                },
                "max_output_tokens": self.max_response_output_tokens
            }
        }
        
        return session_config


# Default voice settings - can be overridden by user preferences
# Optimized for low latency while maintaining good voice detection
VOICE_SETTINGS = {
    "default": VoiceConfig(
        turn_detection={
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 200,  # Reduced from 300
            "silence_duration_ms": 350,  # Reduced from 500
            "create_response": True
        }
    ),
    "low_latency": VoiceConfig(
        turn_detection={
            "type": "server_vad",
            "threshold": 0.55,  # Slightly higher for faster detection
            "prefix_padding_ms": 150,  # Minimal buffer
            "silence_duration_ms": 250,  # Very fast response
            "create_response": True
        },
        temperature=0.7
    ),
    "ultra_low_latency": VoiceConfig(
        turn_detection={
            "type": "server_vad",
            "threshold": 0.6,  # Higher threshold for instant detection
            "prefix_padding_ms": 100,  # Minimal buffer
            "silence_duration_ms": 200,  # Fastest response
            "create_response": True
        },
        temperature=0.7
    ),
    "quiet_environment": VoiceConfig(
        turn_detection={
            "type": "server_vad",
            "threshold": 0.35,  # Lower threshold for quiet environments
            "prefix_padding_ms": 250,
            "silence_duration_ms": 400,
            "create_response": True
        }
    ),
    "noisy_environment": VoiceConfig(
        turn_detection={
            "type": "server_vad",
            "threshold": 0.7,  # Higher threshold to filter noise
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500,
            "create_response": True
        }
    ),
    "push_to_talk": VoiceConfig(
        turn_detection=None  # Disable VAD for push-to-talk (manual mode)
    )
}


# OpenAI Realtime API endpoints (GA)
OPENAI_REALTIME_CLIENT_SECRETS_URL = "https://api.openai.com/v1/realtime/client_secrets"
OPENAI_REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"
