"""
Consolidation Pipeline — Orchestrates the daily STM → LTM transfer.

Scheduled to run daily (or every 2 days). For each user with unconsolidated
STM observations:
1. Load unconsolidated STM observations
2. Load current LTM nodes
3. Run Consolidation Agent (LLM reasoning)
4. Execute decisions via ConsolidationExecutor
5. Decay salience on all LTM nodes
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from .consolidation_agent import run_consolidation_agent
from .consolidation_executor import ConsolidationExecutor
from .salience_decay import SalienceDecayService

logger = logging.getLogger(__name__)


class ConsolidationPipeline:
    """Orchestrates the full consolidation process."""

    def __init__(self, db: AsyncIOMotorDatabase, openai_client):
        self.db = db
        self.openai = openai_client
        self.executor = ConsolidationExecutor(db)
        self.salience_service = SalienceDecayService(db)

    async def run_for_user(self, user_id: str) -> Dict[str, Any]:
        """
        Run the full consolidation pipeline for a single user.
        Returns execution stats.
        """
        logger.info(f"Starting consolidation for user {user_id[:8]}...")

        # Step 1: Load unconsolidated STM observations
        stm_docs = await self.db.stm_observations.find(
            {"user_id": user_id, "consolidated": False},
        ).sort("observed_at", 1).to_list(500)

        if not stm_docs:
            logger.info(f"No unconsolidated observations for {user_id[:8]}...")
            # Still run salience decay
            await self.salience_service.decay_user(user_id)
            return {"status": "no_observations", "user_id": user_id}

        logger.info(f"Found {len(stm_docs)} unconsolidated observations")

        # Get avatar_id
        avatar_id = stm_docs[0].get("avatar_id", user_id)

        # Step 2: Load current LTM nodes
        ltm_nodes = await self.db.graph_nodes.find(
            {"user_id": user_id},
            {"_id": 0, "id": 1, "label": 1, "node_type": 1, "display_label": 1,
             "belief_alpha": 1, "belief_beta": 1, "belief_strength": 1,
             "salience": 1, "salience_stability": 1, "status": 1,
             "evidence_count": 1, "evidence_pattern": 1,
             "narrative_descriptor": 1, "first_evidence_at": 1,
             "last_evidence_at": 1}
        ).to_list(500)

        # Prepare observation summaries for the agent
        stm_summaries = [
            {
                "label": d.get("entity_label", ""),
                "type": d.get("entity_type", ""),
                "subtype": d.get("observation_subtype", ""),
                "confidence": d.get("confidence", 0.5),
                "evidence_weight": d.get("evidence_weight", 0.5),
                "source": d.get("source", ""),
                "details": d.get("details", ""),
                "raw_evidence": d.get("raw_evidence", ""),
                "observed_at": str(d.get("observed_at", "")),
                "observation_type": d.get("observation_type", "new"),
                "corrects": d.get("corrects", ""),
                "reasoning": d.get("reasoning", ""),
            }
            for d in stm_docs
        ]

        # Step 3: Run Consolidation Agent
        logger.info("Running Consolidation Agent...")
        result = await run_consolidation_agent(
            openai_client=self.openai,
            stm_observations=stm_summaries,
            ltm_nodes=ltm_nodes,
        )

        if not result.consolidation_decisions:
            logger.info("Consolidation Agent returned no decisions")
            # Still mark as consolidated and run salience decay
            stm_ids = [d.get("id") for d in stm_docs if d.get("id")]
            if stm_ids:
                now = datetime.now(timezone.utc)
                await self.db.stm_observations.update_many(
                    {"id": {"$in": stm_ids}},
                    {"$set": {"consolidated": True, "consolidated_at": now}},
                )
            await self.salience_service.decay_user(user_id)
            return {"status": "no_decisions", "user_id": user_id, "observations": len(stm_docs)}

        # Step 4: Execute decisions
        stm_ids = [d.get("id") for d in stm_docs if d.get("id")]
        stats = await self.executor.execute(
            user_id=user_id,
            avatar_id=avatar_id,
            result=result,
            stm_observation_ids=stm_ids,
        )

        # Step 5: Decay salience on all LTM nodes
        await self.salience_service.decay_user(user_id)

        stats["user_id"] = user_id
        stats["status"] = "completed"
        stats["decisions"] = len(result.consolidation_decisions)
        stats["stm_observations"] = len(stm_docs)
        return stats

    async def run_for_all_users(self) -> List[Dict[str, Any]]:
        """
        Run consolidation for ALL users who have unconsolidated observations.
        Called by the scheduled job.
        """
        logger.info("Starting consolidation for all users...")

        # Find all users with unconsolidated STM observations
        pipeline = [
            {"$match": {"consolidated": False}},
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        user_groups = await self.db.stm_observations.aggregate(pipeline).to_list(1000)

        logger.info(f"Found {len(user_groups)} users with unconsolidated observations")

        results = []
        for group in user_groups:
            user_id = group["_id"]
            try:
                stats = await self.run_for_user(user_id)
                results.append(stats)
            except Exception as e:
                logger.error(f"Consolidation failed for {user_id[:8]}...: {e}")
                results.append({"user_id": user_id, "status": "error", "error": str(e)})

        # Also run salience decay for users without new observations
        all_users_with_nodes = await self.db.graph_nodes.distinct(
            "user_id",
            {"salience": {"$exists": True, "$gt": 0}},
        )
        processed_users = {r.get("user_id") for r in results}
        for uid in all_users_with_nodes:
            if uid not in processed_users:
                try:
                    await self.salience_service.decay_user(uid)
                except Exception as e:
                    logger.warning(f"Salience decay failed for {uid[:8]}...: {e}")

        logger.info(f"Consolidation complete: {len(results)} users processed")
        return results
