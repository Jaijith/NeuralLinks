"""
Consolidation Executor — Applies ConsolidationResult decisions to LTM.

For each decision:
1. Resolve entity to existing LTM node (or create new)
2. Apply Bayesian belief updates (alpha/beta increments)
3. Apply salience and stability updates
4. Apply status transitions
5. Append to evidence_log
6. Update frequency metrics and narrative descriptors
7. Create new edges if suggested
8. Mark STM observations as consolidated
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from .bayesian import (
    add_bayesian_defaults,
    add_bayesian_edge_defaults,
    compute_belief_confidence,
    compute_belief_strength,
    compute_belief_variance,
)
from .entity_resolver import EntityResolver, make_node_id
from .models import (
    ConsolidationDecision,
    ConsolidationResult,
    EdgeSuggestion,
)

logger = logging.getLogger(__name__)


class ConsolidationExecutor:
    """Applies ConsolidationResult decisions to LTM (graph_nodes/graph_edges)."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.resolver = EntityResolver(db)

    async def execute(
        self,
        user_id: str,
        avatar_id: str,
        result: ConsolidationResult,
        stm_observation_ids: List[str],
    ) -> Dict[str, int]:
        """
        Execute all consolidation decisions for a user.

        Returns a summary of actions taken.
        """
        stats = {
            "nodes_updated": 0,
            "nodes_created": 0,
            "edges_created": 0,
            "observations_consolidated": 0,
        }

        now = datetime.now(timezone.utc)

        # Preload user's LTM nodes for efficient resolution
        await self.resolver.preload_user_nodes(user_id)

        # Apply each consolidation decision
        for decision in result.consolidation_decisions:
            try:
                existing = await self.resolver.resolve(
                    user_id=user_id,
                    entity_label=decision.entity_label,
                    entity_type=decision.entity_type,
                )

                if existing:
                    await self._update_existing_node(existing, decision, now)
                    stats["nodes_updated"] += 1
                else:
                    await self._create_new_node(
                        user_id, avatar_id, decision, now
                    )
                    stats["nodes_created"] += 1

            except Exception as e:
                logger.error(
                    f"Error executing decision for '{decision.entity_label}': {e}"
                )

        # Create suggested edges
        for edge_sug in result.new_edges_suggested:
            try:
                created = await self._create_edge(user_id, edge_sug, now)
                if created:
                    stats["edges_created"] += 1
            except Exception as e:
                logger.warning(f"Error creating edge: {e}")

        # Mark STM observations as consolidated
        if stm_observation_ids:
            await self.db.stm_observations.update_many(
                {"id": {"$in": stm_observation_ids}},
                {"$set": {"consolidated": True, "consolidated_at": now}},
            )
            stats["observations_consolidated"] = len(stm_observation_ids)

        # Update coverage in knowledge gaps
        await self._update_coverage(user_id, result)

        # Signal cache invalidation
        await self._signal_cache_bust(user_id, now)

        self.resolver.clear_cache()

        logger.info(
            f"Consolidation executed for {user_id[:8]}...: "
            f"{stats['nodes_updated']} updated, {stats['nodes_created']} created, "
            f"{stats['edges_created']} edges, "
            f"{stats['observations_consolidated']} observations consolidated"
        )
        return stats

    async def _update_existing_node(
        self,
        existing: Dict[str, Any],
        decision: ConsolidationDecision,
        now: datetime,
    ):
        """Apply consolidation decision to an existing LTM node."""
        bu = decision.belief_update
        su = decision.salience_update
        sd = decision.status_decision
        fa = decision.frequency_assessment

        old_alpha = existing.get("belief_alpha", 1.0)
        old_beta = existing.get("belief_beta", 1.0)
        new_alpha = old_alpha + bu.delta_alpha
        new_beta = old_beta + bu.delta_beta

        bs = compute_belief_strength(new_alpha, new_beta)
        bv = compute_belief_variance(new_alpha, new_beta)
        bc = compute_belief_confidence(new_alpha, new_beta)

        evidence_entry = {
            "at": now,
            "source": "consolidation",
            "weight": bu.delta_alpha,
            "subtype": "consolidation_batch",
            "session_id": "",
        }

        update = {
            "$set": {
                "belief_alpha": new_alpha,
                "belief_beta": new_beta,
                "belief_strength": bs,
                "belief_variance": bv,
                "belief_confidence": bc,
                "salience": su.new_salience,
                "salience_stability": su.new_stability_days,
                "salience_last_computed": now,
                "status": sd.new_status,
                "evidence_pattern": fa.evidence_pattern,
                "narrative_descriptor": fa.narrative_descriptor,
                "mention_frequency": fa.mention_frequency_per_month,
                "strength": bs,
                "last_evidence_at": now,
                "updated_at": now,
            },
            "$inc": {"evidence_count": 1},
            "$push": {"evidence_log": evidence_entry},
            "$addToSet": {"evidence_sources": "consolidation"},
        }

        # Calculate evidence span
        first = existing.get("first_evidence_at")
        if first and isinstance(first, datetime):
            if first.tzinfo is None:
                first = first.replace(tzinfo=timezone.utc)
            update["$set"]["evidence_span_days"] = max(0, (now - first).days)

        await self.db.graph_nodes.update_one(
            {"_id": existing["_id"]},
            update,
        )

    async def _create_new_node(
        self,
        user_id: str,
        avatar_id: str,
        decision: ConsolidationDecision,
        now: datetime,
    ):
        """Create a new LTM node from a consolidation decision."""
        bu = decision.belief_update
        su = decision.salience_update
        sd = decision.status_decision
        fa = decision.frequency_assessment

        node_type = decision.entity_type
        label = decision.entity_label.lower().strip()
        node_id = make_node_id(node_type, user_id, label)

        alpha = 1.0 + bu.delta_alpha
        beta = 1.0 + bu.delta_beta
        bs = compute_belief_strength(alpha, beta)

        node = {
            "id": node_id,
            "user_id": user_id,
            "node_type": node_type,
            "label": label,
            "display_label": label.title(),
            "strength": bs,
            "mention_count": 1,
            "properties": {"source": "consolidation"},
            "created_at": now,
            "updated_at": now,
            # Bayesian
            "belief_alpha": alpha,
            "belief_beta": beta,
            "belief_strength": bs,
            "belief_variance": compute_belief_variance(alpha, beta),
            "belief_confidence": compute_belief_confidence(alpha, beta),
            # Evidence
            "evidence_count": 1,
            "evidence_log": [{
                "at": now,
                "source": "consolidation",
                "weight": bu.delta_alpha,
                "subtype": "consolidation_initial",
                "session_id": "",
            }],
            "evidence_sources": ["consolidation"],
            "first_evidence_at": now,
            "last_evidence_at": now,
            # Frequency
            "mention_frequency": fa.mention_frequency_per_month,
            "evidence_span_days": 0,
            "evidence_pattern": fa.evidence_pattern,
            "narrative_descriptor": fa.narrative_descriptor,
            # Salience
            "salience": su.new_salience,
            "salience_stability": su.new_stability_days,
            "salience_last_computed": now,
            # Status
            "status": sd.new_status,
        }

        try:
            await self.db.graph_nodes.insert_one(node)
        except Exception as e:
            if "duplicate key" in str(e).lower():
                logger.warning(
                    f"Duplicate node during creation: {node_id} — "
                    f"likely race condition, skipping"
                )
            else:
                raise

    async def _create_edge(
        self,
        user_id: str,
        edge_sug: EdgeSuggestion,
        now: datetime,
    ) -> bool:
        """Create a new LTM edge from a suggested edge."""
        from_label = edge_sug.from_label.lower().strip()
        to_label = edge_sug.to_label.lower().strip()

        from_node = await self.db.graph_nodes.find_one(
            {"user_id": user_id, "label": from_label},
            {"_id": 0, "id": 1},
        )
        to_node = await self.db.graph_nodes.find_one(
            {"user_id": user_id, "label": to_label},
            {"_id": 0, "id": 1},
        )

        if not from_node or not to_node:
            return False

        from_id = from_node["id"]
        to_id = to_node["id"]

        existing_edge = await self.db.graph_edges.find_one({
            "from_node_id": from_id,
            "to_node_id": to_id,
        })
        if existing_edge:
            return False

        edge = {
            "id": str(uuid.uuid4()),
            "from_node_id": from_id,
            "to_node_id": to_id,
            "relationship_type": edge_sug.relationship_type,
            "weight": 0.5,
            "properties": {"reasoning": edge_sug.reasoning, "source": "consolidation"},
            "created_at": now,
        }
        add_bayesian_edge_defaults(edge, user_id=user_id)
        await self.db.graph_edges.insert_one(edge)
        return True

    async def _update_coverage(
        self, user_id: str, result: ConsolidationResult
    ):
        """Update knowledge gap coverage from consolidation insights."""
        cu = result.coverage_updates
        deltas = {
            "life_narrative": cu.life_narrative,
            "values_beliefs": cu.values_beliefs,
            "communication_style": cu.communication_style,
            "social_patterns": cu.social_patterns,
            "interests_passions": cu.interests_passions,
            "emotional_patterns": cu.emotional_patterns,
            "daily_life": cu.daily_life,
            "humor_personality": cu.humor_personality,
        }

        non_zero = {k: v for k, v in deltas.items() if v != 0}
        if not non_zero:
            return

        try:
            gap_doc = await self.db.avatar_knowledge_gaps.find_one(
                {"user_id": user_id},
            )
            if gap_doc:
                inc_ops = {}
                for dim, delta in non_zero.items():
                    field = f"coverage.{dim}"
                    current = gap_doc.get("coverage", {}).get(dim, 0)
                    inc_ops[field] = min(1.0, current + delta)
                if inc_ops:
                    await self.db.avatar_knowledge_gaps.update_one(
                        {"_id": gap_doc["_id"]},
                        {"$set": inc_ops},
                    )
        except Exception as e:
            logger.warning(f"Coverage update error: {e}")

    async def _signal_cache_bust(self, user_id: str, now: datetime):
        """
        Write to graph_cache_bust for cross-process cache invalidation.
        API servers check this collection to know when to invalidate GraphRAG cache.
        """
        try:
            await self.db.graph_cache_bust.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "busted_at": now}},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"Cache bust signal error: {e}")
