"""
Consolidation Scheduler — Decides when to run consolidation.

Two trigger modes:
1. **Daily batch** (primary): Runs at a scheduled time (e.g., 3 AM UTC)
   for all users with unconsolidated STM observations.
2. **High-activity threshold** (secondary): If a user accumulates >N
   unconsolidated observations, trigger early consolidation for that user.

The scheduler itself doesn't own the cron/EventBridge timer — that's
infrastructure. This module provides the logic for:
- Checking whether consolidation should run
- Running the consolidation pipeline
- Recording last-run timestamps
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from .consolidation_pipeline import ConsolidationPipeline
from .salience_decay import SalienceDecayService

logger = logging.getLogger(__name__)

HIGH_ACTIVITY_THRESHOLD = 50
COOLDOWN_HOURS = 4


class ConsolidationScheduler:
    """
    Manages consolidation scheduling decisions and execution.

    Usage (from an EventBridge / Lambda handler or manual trigger):

        scheduler = ConsolidationScheduler(db, openai_client)
        result = await scheduler.run_scheduled()    # daily batch
        result = await scheduler.check_and_run()    # threshold check
    """

    def __init__(self, db: AsyncIOMotorDatabase, openai_client):
        self.db = db
        self.openai = openai_client
        self.pipeline = ConsolidationPipeline(db, openai_client)
        self.salience_service = SalienceDecayService(db)

    async def run_scheduled(self) -> Dict[str, Any]:
        """
        Primary daily batch: consolidate all users + decay salience.
        Called by the scheduled EventBridge / cron trigger.
        """
        logger.info("=== Scheduled consolidation run starting ===")
        start = datetime.now(timezone.utc)

        consolidation_results = await self.pipeline.run_for_all_users()

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        users_processed = len(consolidation_results)

        await self._record_run(
            trigger="scheduled",
            users_processed=users_processed,
            elapsed_seconds=elapsed,
        )

        logger.info(
            "Scheduled consolidation complete: %d users in %.1fs",
            users_processed, elapsed,
        )

        return {
            "trigger": "scheduled",
            "users_processed": users_processed,
            "elapsed_seconds": round(elapsed, 2),
            "results": consolidation_results,
        }

    async def check_and_run_threshold(
        self, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Secondary trigger: check if any user (or a specific user) has
        crossed the high-activity threshold.

        If user_id is given, only check that user.
        Otherwise, scan all users.

        Returns consolidation results for users that triggered.
        """
        triggered_users: List[str] = []

        if user_id:
            count = await self.db.stm_observations.count_documents(
                {"user_id": user_id, "consolidated": False}
            )
            if count >= HIGH_ACTIVITY_THRESHOLD:
                if await self._check_cooldown(user_id):
                    triggered_users.append(user_id)
        else:
            pipeline = [
                {"$match": {"consolidated": False}},
                {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
                {"$match": {"count": {"$gte": HIGH_ACTIVITY_THRESHOLD}}},
            ]
            async for group in self.db.stm_observations.aggregate(pipeline):
                uid = group["_id"]
                if await self._check_cooldown(uid):
                    triggered_users.append(uid)

        if not triggered_users:
            return {"trigger": "threshold", "triggered": 0, "results": []}

        logger.info(
            "High-activity threshold triggered for %d users",
            len(triggered_users),
        )

        results: List[Dict[str, Any]] = []
        for uid in triggered_users:
            try:
                stats = await self.pipeline.run_for_user(uid)
                results.append(stats)
            except Exception as e:
                logger.error("Threshold consolidation failed for %s: %s", uid[:8], e)
                results.append({"user_id": uid, "status": "error", "error": str(e)})

        await self._record_run(
            trigger="threshold",
            users_processed=len(results),
            elapsed_seconds=0,
        )

        return {
            "trigger": "threshold",
            "triggered": len(triggered_users),
            "results": results,
        }

    async def get_schedule_status(self) -> Dict[str, Any]:
        """Return info about last runs and pending work."""
        last_scheduled = await self.db.consolidation_runs.find_one(
            {"trigger": "scheduled"},
            sort=[("completed_at", -1)],
        )
        last_threshold = await self.db.consolidation_runs.find_one(
            {"trigger": "threshold"},
            sort=[("completed_at", -1)],
        )

        pending_pipeline = [
            {"$match": {"consolidated": False}},
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        pending = await self.db.stm_observations.aggregate(
            pending_pipeline
        ).to_list(100)

        total_pending = sum(p["count"] for p in pending)
        users_above_threshold = sum(
            1 for p in pending if p["count"] >= HIGH_ACTIVITY_THRESHOLD
        )

        return {
            "last_scheduled_run": (
                str(last_scheduled["completed_at"]) if last_scheduled else None
            ),
            "last_threshold_run": (
                str(last_threshold["completed_at"]) if last_threshold else None
            ),
            "total_pending_observations": total_pending,
            "users_with_pending": len(pending),
            "users_above_threshold": users_above_threshold,
            "threshold": HIGH_ACTIVITY_THRESHOLD,
            "cooldown_hours": COOLDOWN_HOURS,
        }

    async def _check_cooldown(self, user_id: str) -> bool:
        """Prevent rapid re-consolidation for the same user."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=COOLDOWN_HOURS)
        recent = await self.db.consolidation_runs.find_one(
            {
                "trigger": "threshold",
                "completed_at": {"$gte": cutoff},
                "user_ids": user_id,
            }
        )
        return recent is None

    async def _record_run(
        self,
        *,
        trigger: str,
        users_processed: int,
        elapsed_seconds: float,
    ):
        """Record a consolidation run for auditing and cooldown checks."""
        await self.db.consolidation_runs.insert_one({
            "trigger": trigger,
            "completed_at": datetime.now(timezone.utc),
            "users_processed": users_processed,
            "elapsed_seconds": round(elapsed_seconds, 2),
        })
