"""
STM Writer — Writes validated observations to Short-Term Memory collections.

Converts ClassifiedObservation objects to STMObservation documents and
inserts them into stm_observations and stm_edges collections.
"""

import logging
from datetime import datetime, timezone
from typing import Any, List

from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import (
    ClassificationResult,
    ClassifiedObservation,
    CoMention,
    ObservationType,
    STMEdge,
    STMObservation,
)

logger = logging.getLogger(__name__)


class STMWriter:
    """Writes classified observations to the STM collections."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def write(
        self,
        user_id: str,
        avatar_id: str,
        observations: List[ClassifiedObservation],
        co_mentions: List[CoMention],
        source: str,
        session_id: str = "",
    ) -> int:
        """
        Write validated observations and co-mentions to STM.

        Returns the number of observations written.
        """
        if not observations:
            return 0

        now = datetime.now(timezone.utc)
        written = 0

        # Write observations
        stm_docs = []
        for obs in observations:
            stm_obs = STMObservation(
                user_id=user_id,
                avatar_id=avatar_id,
                entity_label=obs.label,
                entity_type=obs.entity_type,
                display_label=obs.display_label or "",
                observation_subtype=obs.observation_subtype or "",
                observation_type=obs.observation_type or ObservationType.NEW.value,
                source=source,
                session_id=session_id,
                raw_evidence=obs.quote or "",
                details=obs.details or "",
                confidence=obs.confidence,
                evidence_weight=obs.evidence_weight,
                sentiment=obs.sentiment,
                reasoning=obs.reasoning or "",
                corrects=obs.corrects or "",
                observed_at=now,
            )
            stm_docs.append(stm_obs.to_mongo())

        if stm_docs:
            try:
                result = await self.db.stm_observations.insert_many(stm_docs)
                written = len(result.inserted_ids)
            except Exception as e:
                logger.error(f"Error writing {len(stm_docs)} observations to STM: {e}")
                return 0

        # Write co-mention edges
        if co_mentions:
            edge_docs = []
            for cm in co_mentions:
                edge = STMEdge(
                    user_id=user_id,
                    from_entity_label=cm.entity_a,
                    to_entity_label=cm.entity_b,
                    relationship_hint=cm.relationship_hint,
                    source=source,
                    session_id=session_id,
                    observed_at=now,
                )
                edge_docs.append(edge.to_mongo())

            try:
                await self.db.stm_edges.insert_many(edge_docs)
            except Exception as e:
                logger.warning(f"Error writing {len(edge_docs)} co-mention edges to STM: {e}")

        logger.info(
            f"STM write: {written} observations, {len(co_mentions)} edges "
            f"for user {user_id[:8]}... (source={source})"
        )
        return written

    async def write_from_result(
        self,
        user_id: str,
        avatar_id: str,
        result: ClassificationResult,
        source: str,
        session_id: str = "",
    ) -> int:
        """Convenience: write a full ClassificationResult to STM."""
        return await self.write(
            user_id=user_id,
            avatar_id=avatar_id,
            observations=result.observations,
            co_mentions=result.co_mentions,
            source=source,
            session_id=session_id,
        )
