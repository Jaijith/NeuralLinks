"""
Voice Configuration
Configuration settings for the OpenAI Realtime Voice API (GA Version)
"""
from typing import Dict, Any, Optional, List
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
    
    def to_session_config(
        self, 
        instructions: str,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Convert to OpenAI GA Realtime session configuration
        
        Format for POST /v1/realtime/client_secrets
        
        Args:
            instructions: System prompt instructions
            tools: Optional list of function tools the AI can call
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
        
        # Add tools if provided
        if tools:
            session_config["session"]["tools"] = tools
        
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


# Function tools for the AI to call when it needs more context
# The AI decides when to use these - we don't force it
VOICE_TOOLS = [
    {
        "type": "function",
        "name": "recall_social_context",
        "description": """Recall details about your social life when you need specific information you don't already know.

USE THIS WHEN:
- User asks for specific details about a friend that aren't in your context
- User asks about a specific conversation you had
- You want to share something specific but need to remember the details
- You need to look up what a particular friend has been doing

DO NOT USE THIS FOR:
- Casual conversation that doesn't need specific facts
- When you already have the information in your social context
- Simple greetings or emotional exchanges
- General questions you can answer from what you already know

When you call this, continue talking naturally while waiting for the response - 
share your thoughts, express anticipation, or talk about something related.""",
        "parameters": {
            "type": "object",
            "properties": {
                "context_type": {
                    "type": "string",
                    "enum": [
                        "my_activities",
                        "my_posts", 
                        "friends",
                        "friend_activity",
                        "conversations",
                        "specific_friend",
                        "specific_conversation"
                    ],
                    "description": "What type of social information to recall"
                },
                "friend_name": {
                    "type": "string",
                    "description": "Name of a specific friend (required for specific_friend and specific_conversation)"
                },
                "time_range": {
                    "type": "string",
                    "enum": ["today", "yesterday", "this_week", "recent"],
                    "description": "Time period to recall from (default: recent)"
                }
            },
            "required": ["context_type"]
        }
    },
    {
        "type": "function",
        "name": "recall_past_conversations",
        "description": """Search your memory of past voice conversations with the user.

USE THIS WHEN:
- The user asks "do you remember when we talked about...?"
- The user refers to a previous conversation or something they told you before
- You want to reference a past conversation to show you remember
- The user asks about something you discussed in an earlier session
- You need to recall specific details from a past discussion

DO NOT USE THIS FOR:
- Questions about social network activity (use recall_social_context for that)
- Current session topics (you already know those)
- General knowledge questions

When you call this, say something like "Let me think... I remember us talking about that..." 
to keep the conversation flowing naturally. Show genuine effort to remember.""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What you're trying to remember (e.g., 'Japan trip discussion', 'when they talked about their daughter')"
                },
                "include_full_transcript": {
                    "type": "boolean",
                    "description": "Whether to fetch the full conversation transcript for detailed recall. Use true when user asks for exact details."
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "trigger_workflow",
        "description": """Trigger a workflow mission when the user CONFIRMS they want to start a task.

IMPORTANT: ALWAYS CONFIRM BEFORE TRIGGERING!
When the user asks you to start a workflow, DO NOT trigger immediately. Instead:
1. First, understand what they want to do
2. Summarize back what you understood: "So you want me to [mission type] to find [criteria]. Is that right?"
3. Wait for their confirmation (like "yes", "that's right", "go ahead", "do it")
4. ONLY call this function AFTER they confirm

EXAMPLES OF CONFIRMATION FLOW:
User: "Find me people who like music"
You: "I can help you find people who share your interest in music. I'll search for profiles with music-related interests. Should I start this matchmaking mission for you?"
User: "Yes, go ahead"
[NOW call trigger_workflow]

User: "I need to network with tech professionals"  
You: "I'd be happy to help you connect with tech professionals. I can start a networking mission to find engineers, developers, and tech leaders. Want me to kick that off?"
User: "Yes please"
[NOW call trigger_workflow]

MISSION TYPES:
- matchmaking: Finding people with similar interests
- networking: Connecting with professionals
- sales_leads: Finding potential customers
- marketing_campaign: Running outreach campaigns
- job_finder: Finding job opportunities
- bonding: Deepening connection with you

DO NOT USE THIS FOR:
- Casual conversation or questions about workflows
- When the user hasn't confirmed yet
- Simple information requests

After triggering, tell the user that the mission has been started and they can check the Missions page to see the progress.""",
        "parameters": {
            "type": "object",
            "properties": {
                "mission_type": {
                    "type": "string",
                    "enum": [
                        "matchmaking",
                        "networking",
                        "sales_leads",
                        "marketing_campaign",
                        "bonding",
                        "job_finder"
                    ],
                    "description": "Type of workflow to run"
                },
                "mission_name": {
                    "type": "string",
                    "description": "A descriptive name for the mission based on what the user asked"
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what the mission should accomplish"
                },
                "interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Interests to filter by (e.g., ['music', 'technology'])"
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to search for (e.g., ['engineer', 'startup'])"
                },
                "approach": {
                    "type": "string",
                    "enum": ["casual", "professional", "curious", "enthusiastic", "thoughtful"],
                    "description": "Approach style for outreach (default: friendly)"
                },
                "max_targets": {
                    "type": "integer",
                    "description": "Maximum number of targets to find (default: 10)"
                }
            },
            "required": ["mission_type", "mission_name"]
        }
    }
]
