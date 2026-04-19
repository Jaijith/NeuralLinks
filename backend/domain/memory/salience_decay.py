"""
Salience Decay Service — Pure math, no LLM.

Applies Ebbinghaus-inspired exponential salience decay to all LTM nodes.
Runs daily (standalone or as part of the consolidation pipeline).

Also handles fading-status transitions: nodes whose salience drops below
the fading threshold are marked "fading" so downstream consumers can
exclude or de-prioritize them.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from .bayesian import compute_salience_decay
from .models import NodeStatus

logger = logging.getLogger(__name__)

FADING_SALIENCE_THRESHOLD = 0.05
FLOOR_SALIENCE = 0.01


class SalienceDecayService:
    """
    Standalone salience decay processor.

    Can be invoked per-user or for all users with active nodes.
    Does not require an LLM — pure Ebbinghaus decay math.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def decay_user(self, user_id: str) -> Dict[str, Any]:
        """
        Apply salience decay to all LTM nodes for a single user.

        Returns stats: {decayed, faded, skipped}.
        """
        now = datetime.now(timezone.utc)

        cursor = self.db.graph_nodes.find(
            {
                "user_id": user_id,
                "salience": {"$exists": True, "$gt": FLOOR_SALIENCE},
            },
            {
                "_id": 1,
                "salience": 1,
                "salience_stability": 1,
                "salience_last_computed": 1,
                "status": 1,
                "label": 1,
            },
        )

        decayed = 0
        faded = 0
        skipped = 0

        async for node in cursor:
            last_computed = node.get("salience_last_computed")
            if not last_computed or not isinstance(last_computed, datetime):
                skipped += 1
                continue

            if last_computed.tzinfo is None:
                last_computed = last_computed.replace(tzinfo=timezone.utc)

            elapsed_days = max(0, (now - last_computed).total_seconds() / 86400)
            if elapsed_days < 0.5:
                skipped += 1
                continue

            old_sal = node.get("salience", 0.5)
            stability = node.get("salience_stability", 14.0)
            new_sal = compute_salience_decay(old_sal, elapsed_days, stability)
            new_sal = max(FLOOR_SALIENCE, new_sal)

            update_fields: Dict[str, Any] = {
                "salience": new_sal,
                "salience_last_computed": now,
            }

            current_status = node.get("status", NodeStatus.ACTIVE.value)
            if (
                new_sal < FADING_SALIENCE_THRESHOLD
                and current_status == NodeStatus.ACTIVE.value
            ):
                update_fields["status"] = NodeStatus.FADING.value
                faded += 1

            await self.db.graph_nodes.update_one(
                {"_id": node["_id"]},
                {"$set": update_fields},
            )
            decayed += 1

        if decayed > 0:
            logger.info(
                "Salience decay for %s...: %d decayed, %d faded, %d skipped",
                user_id[:8], decayed, faded, skipped,
            )

        return {
            "user_id": user_id,
            "decayed": decayed,
            "faded": faded,
            "skipped": skipped,
        }

    async def decay_all_users(self) -> List[Dict[str, Any]]:
        """
        Run salience decay for every user who has active salience values.
        Intended to be called by the scheduler or a cron/EventBridge trigger.
        """
        user_ids = await self.db.graph_nodes.distinct(
            "user_id",
            {"salience": {"$exists": True, "$gt": FLOOR_SALIENCE}},
        )

        logger.info("Running salience decay for %d users", len(user_ids))
        results: List[Dict[str, Any]] = []

        for uid in user_ids:
            try:
                stats = await self.decay_user(uid)
                results.append(stats)
            except Exception as e:
                logger.error("Salience decay failed for %s...: %s", uid[:8], e)
                results.append({"user_id": uid, "error": str(e)})

        total_decayed = sum(r.get("decayed", 0) for r in results)
        total_faded = sum(r.get("faded", 0) for r in results)
        logger.info(
            "Salience decay complete: %d users, %d nodes decayed, %d faded",
            len(results), total_decayed, total_faded,
        )
        return results
