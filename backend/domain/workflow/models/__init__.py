"""
Workflow Models
Data models for missions, leads, chat, activities, and bonding
"""

from .enums import (
    MissionType, MissionStatus, MissionPhase, LeadStatus, LeadPriority,
    UserIntent, UserMood, BondingMode, UserEmotion, BondingCardType
)
from .mission import Mission, MissionCriteria, MissionStrategy
from .lead import Lead, LeadScoreBreakdown
from .chat import AvatarChatMessage, AvatarChatSession
from .activity import MissionActivity
from .bonding_state import BondingState, BondingMetrics, UnresolvedThread, RelationshipArc
from .bonding_memory import (
    IdentityMemory, NarrativeMemory, BondMoment, ReflectionLog, BondingSession
)

