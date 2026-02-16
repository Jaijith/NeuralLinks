"""
Access Control Layer
Checks if a skill is installed and enabled for an avatar.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AccessResult:
    permitted: bool
    reason: Optional[str] = None


class AccessControlLayer:
    """Layer 1: Checks if a skill is installed and enabled for an avatar"""

    def __init__(self, db):
        self.db = db

    async def check(self, avatar_id: str, skill_slug: str, skill_type: str = "mcp_tool") -> AccessResult:
        """Check if avatar has this skill installed and enabled"""
        try:
            installation = await self.db.siddhi_installations.find_one({
                "user_id": avatar_id,
                "skill_slug": skill_slug,
            })

            if not installation:
                return AccessResult(permitted=False, reason=f"Skill '{skill_slug}' not installed")

            if not installation.get("enabled", True):
                return AccessResult(permitted=False, reason=f"Skill '{skill_slug}' is disabled")

            circuit_status = installation.get("gateway_state", {}).get("circuit_status", "closed")
            if circuit_status == "open":
                return AccessResult(permitted=False, reason=f"Skill '{skill_slug}' circuit is open (temporarily disabled)")

            return AccessResult(permitted=True)

        except Exception as e:
            logger.error(f"Access control check failed for {avatar_id}/{skill_slug}: {e}")
            return AccessResult(permitted=True, reason=None)
