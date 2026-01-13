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

