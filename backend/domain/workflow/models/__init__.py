"""
Workflow Models
Data models for missions, leads, chat, and activities
"""

from .enums import MissionType, MissionStatus, MissionPhase, LeadStatus, LeadPriority
from .mission import Mission, MissionCriteria, MissionStrategy
from .lead import Lead, LeadScoreBreakdown
from .chat import AvatarChatMessage, AvatarChatSession
from .activity import MissionActivity

