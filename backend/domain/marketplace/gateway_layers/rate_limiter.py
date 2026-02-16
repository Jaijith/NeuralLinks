"""
Rate Limiter Layer
Per-skill rate limiting using counters on the installation document.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    allowed: bool
    reason: Optional[str] = None
    retry_after_seconds: float = 0


class RateLimiterLayer:
    """Layer 2: Per-skill rate limiting"""

    def __init__(self, db):
        self.db = db
        self._skill_config_cache: Dict[str, Dict] = {}

    async def _get_skill_config(self, skill_slug: str) -> Dict[str, Any]:
        if skill_slug in self._skill_config_cache:
            return self._skill_config_cache[skill_slug]

        skill = await self.db.siddhi_skills.find_one({"slug": skill_slug})
        if skill:
            config = skill.get("gateway_config", {}).get("rate_limit", {})
            self._skill_config_cache[skill_slug] = config
            return config
        return {}

    async def check(self, avatar_id: str, skill_slug: str) -> RateLimitResult:
        """Check rate limits for this avatar+skill combo"""
        try:
            config = await self._get_skill_config(skill_slug)
            max_per_hour = config.get("max_per_hour")
            max_per_day = config.get("max_per_day")

            if max_per_hour is None and max_per_day is None:
                return RateLimitResult(allowed=True)

            installation = await self.db.siddhi_installations.find_one({
                "user_id": avatar_id,
                "skill_slug": skill_slug,
            })

            if not installation:
                return RateLimitResult(allowed=True)

            usage = installation.get("usage", {})
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            executions_today = usage.get("executions_today", 0)
            executions_today_date = usage.get("executions_today_date")

            if executions_today_date != today:
                executions_today = 0

            if max_per_day is not None and executions_today >= max_per_day:
                return RateLimitResult(
                    allowed=False,
                    reason=f"Daily limit reached ({executions_today}/{max_per_day})",
                )

            return RateLimitResult(allowed=True)

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return RateLimitResult(allowed=True)
