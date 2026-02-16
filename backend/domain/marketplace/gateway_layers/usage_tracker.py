"""
Usage Tracker Layer
Records execution results for analytics and marketplace stats.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)


class UsageTracker:
    """Layer 4: Records execution results for analytics"""

    def __init__(self, db):
        self.db = db

    async def record(self, avatar_id: str, skill_slug: str, result: Dict[str, Any], latency_ms: float, source: str):
        """Record execution result"""
        try:
            success = result.get("success", False)
            now = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")

            installation = await self.db.siddhi_installations.find_one({
                "user_id": avatar_id,
                "skill_slug": skill_slug,
            })

            if installation:
                usage = installation.get("usage", {})
                exec_date = usage.get("executions_today_date")
                exec_today = usage.get("executions_today", 0) if exec_date == today else 0

                update = {
                    "$inc": {
                        "usage.total_executions": 1,
                        "usage.success_count": 1 if success else 0,
                        "usage.failure_count": 0 if success else 1,
                    },
                    "$set": {
                        "usage.last_used_at": now.isoformat(),
                        "usage.executions_today": exec_today + 1,
                        "usage.executions_today_date": today,
                    },
                }

                await self.db.siddhi_installations.update_one(
                    {"user_id": avatar_id, "skill_slug": skill_slug},
                    update,
                )

            await self.db.siddhi_skills.update_one(
                {"slug": skill_slug},
                {"$inc": {"stats.total_executions": 1}},
            )

        except Exception as e:
            logger.error(f"Usage tracking failed for {avatar_id}/{skill_slug}: {e}")
