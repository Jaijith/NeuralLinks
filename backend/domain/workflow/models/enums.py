"""
Workflow Enums
Enumeration types for workflow states and types
"""

from enum import Enum


class MissionType(str, Enum):
    """Types of missions/workflows available"""
    MATCHMAKING = "matchmaking"
    NETWORKING = "networking"
    SALES_LEADS = "sales_leads"
    MARKETING_CAMPAIGN = "marketing_campaign"
    BONDING = "bonding"               # Relationship deepening conversations
    JOB_FINDER = "job_finder"
    MARKET_RESEARCH = "market_research"
    CONTENT_DISCOVERY = "content_discovery"
    CONTENT_PROMOTION = "content_promotion"
    CUSTOM = "custom"


class MissionStatus(str, Enum):
    """Mission execution status"""
    DRAFT = "draft"           # Mission created but not started
    QUEUED = "queued"         # Waiting to start
    RUNNING = "running"       # Currently executing
    PAUSED = "paused"         # Temporarily paused
    COMPLETED = "completed"   # Successfully finished
    FAILED = "failed"         # Failed with errors
    CANCELLED = "cancelled"   # User cancelled


class MissionPhase(str, Enum):
    """Current execution phase of a mission"""
    INITIALIZING = "initializing"   # Setting up the mission
    DISCOVERING = "discovering"     # Finding potential targets
    EVALUATING = "evaluating"       # Scoring and ranking targets
    ENGAGING = "engaging"           # Starting conversations
    ANALYZING = "analyzing"         # Generating insights and leads
    FINALIZING = "finalizing"       # Completing and summarizing


class LeadStatus(str, Enum):
    """Status of a generated lead"""
    NEW = "new"                     # Just discovered
    CONTACTED = "contacted"         # Conversation started
    RESPONDING = "responding"       # Target has responded
    QUALIFIED = "qualified"         # Confirmed as a good match
    CONVERTED = "converted"         # User followed up successfully
    DISMISSED = "dismissed"         # User dismissed this lead
    STALE = "stale"                 # No activity for too long


class LeadPriority(str, Enum):
    """Priority level of a lead"""
    HIGH = "high"       # Score >= 85
    MEDIUM = "medium"   # Score >= 70
    LOW = "low"         # Score < 70


class ApproachStyle(str, Enum):
    """How the avatar should approach targets"""
    CASUAL = "casual"                     # Friendly, informal approach
    PROFESSIONAL = "professional"         # Business-like approach
    CURIOUS = "curious"                   # Inquisitive, asking questions
    ENTHUSIASTIC = "enthusiastic"         # Energetic, excited
    THOUGHTFUL = "thoughtful"             # Reflective, deep conversations


class MessageRole(str, Enum):
    """Role in chat messages"""
    USER = "user"           # Human user sending instruction
    AVATAR = "avatar"       # Avatar responding
    SYSTEM = "system"       # System messages


class AgentType(str, Enum):
    """Types of agents in the multi-agent system"""
    ORCHESTRATOR = "orchestrator"
    DISCOVERY = "discovery"
    EVALUATION = "evaluation"
    ENGAGEMENT = "engagement"
    ANALYSIS = "analysis"
    MEMORY = "memory"


# ============================================================================
# BONDING WORKFLOW ENUMS
# ============================================================================

class UserIntent(str, Enum):
    """User's intent in bonding conversations"""
    CHECK_IN = "check_in"                 # "How's it going?" - casual status check
    VENTING = "venting"                   # "I'm so frustrated with..." - emotional release
    PLANNING = "planning"                 # "I want to achieve..." - goal setting
    REFLECTION = "reflection"             # "Looking back on..." - retrospective thinking
    SEEKING_ADVICE = "seeking_advice"     # "What should I do about..." - guidance request
    CELEBRATION = "celebration"           # "I did it!" - sharing success
    EXPLORATION = "exploration"           # "I'm curious about..." - discovery mode
    GENERAL_CHAT = "general_chat"         # Casual conversation


class UserMood(str, Enum):
    """Estimated user mood from conversation"""
    STRESSED = "stressed"                 # High pressure, overwhelmed
    EXCITED = "excited"                   # High energy, positive
    BORED = "bored"                       # Low energy, looking for stimulation
    REFLECTIVE = "reflective"             # Thoughtful, contemplative
    FRUSTRATED = "frustrated"             # Blocked, annoyed
    CONTENT = "content"                   # Satisfied, peaceful
    NEUTRAL = "neutral"                   # Default state


class BondingMode(str, Enum):
    """How the avatar should respond in bonding conversations"""
    CHECK_IN = "check_in"                 # Warm presence + curated recap
    COACH = "coach"                       # Guidance + reflection prompts
    PLAY = "play"                         # Fun + serendipity
    DEEP_TALK = "deep_talk"               # Reflection + identity exploration
    PLANNING = "planning"                 # Goal setting + micro-missions
    CELEBRATION = "celebration"           # Acknowledge wins + growth


class UserEmotion(str, Enum):
    """Specific emotional states detected"""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    CALM = "calm"
    CONFUSED = "confused"
    CONFIDENT = "confident"
    DISAPPOINTED = "disappointed"
    GRATEFUL = "grateful"
    CURIOUS = "curious"
    OVERWHELMED = "overwhelmed"
    RELIEVED = "relieved"


class BondingCardType(str, Enum):
    """Types of cards in a bonding response"""
    WARM_PRESENCE = "warm_presence"       # Opening acknowledgment
    RECAP = "recap"                       # Avatar activity summary
    SERENDIPITY = "serendipity"           # Surprising discovery
    REFLECTION = "reflection"             # Deeper insight
    GROWTH = "growth"                     # Avatar learning/skill
    GUIDANCE = "guidance"                 # Avatar asking for direction
    MICRO_MISSION = "micro_mission"       # Small task proposal
    CELEBRATION = "celebration"           # Acknowledge user win

