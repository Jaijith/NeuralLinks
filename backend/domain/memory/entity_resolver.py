"""
Entity Resolver — Matches STM entity labels to existing LTM nodes.

Handles:
- Exact label match
- Legacy node_type mapping (preference → fact, etc.)
- ID format normalization ({type}_{user_id}_{label})
"""

import logging
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Maps entity_type from the Classification Agent to possible LTM node_types
ENTITY_TYPE_TO_NODE_TYPES = {
    "interest": ["interest"],
    "fact": ["fact", "preference"],
    "connection": ["connection"],
    "trait": ["trait"],
    "value": ["value"],
    "preference": ["preference", "interest"],
    "experience": ["experience"],
    "demographic": ["demographic", "fact", "preference"],
}


def make_node_id(node_type: str, user_id: str, label: str) -> str:
    """Generate the canonical node ID format."""
    safe_label = label.lower().strip().replace(" ", "_")
    return f"{node_type}_{user_id}_{safe_label}"


class EntityResolver:
    """Resolves STM entity labels to existing LTM graph_nodes."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._cache: Dict[str, Optional[Dict[str, Any]]] = {}

    async def resolve(
        self,
        user_id: str,
        entity_label: str,
        entity_type: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the existing LTM node matching this entity, if any.

        Returns the node document or None if not found.
        """
        label = entity_label.lower().strip()
        cache_key = f"{user_id}:{entity_type}:{label}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        possible_types = ENTITY_TYPE_TO_NODE_TYPES.get(entity_type, [entity_type])

        for nt in possible_types:
            node = await self.db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": nt,
                "label": label,
            }, {"_id": 1, "id": 1, "label": 1, "node_type": 1,
                "belief_alpha": 1, "belief_beta": 1, "belief_strength": 1,
                "salience": 1, "salience_stability": 1, "status": 1,
                "evidence_count": 1, "evidence_log": 1,
                "first_evidence_at": 1, "last_evidence_at": 1,
                "strength": 1, "mention_count": 1})

            if node:
                self._cache[cache_key] = node
                return node

        self._cache[cache_key] = None
        return None

    async def preload_user_nodes(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Load all active LTM nodes for a user.
        Returns list of node documents and populates the resolver cache.
        """
        nodes = await self.db.graph_nodes.find(
            {"user_id": user_id},
            {"_id": 1, "id": 1, "label": 1, "node_type": 1, "display_label": 1,
             "belief_alpha": 1, "belief_beta": 1, "belief_strength": 1,
             "salience": 1, "salience_stability": 1, "status": 1,
             "evidence_count": 1, "evidence_log": 1,
             "first_evidence_at": 1, "last_evidence_at": 1,
             "strength": 1, "mention_count": 1,
             "evidence_pattern": 1, "narrative_descriptor": 1,
             "mention_frequency": 1, "evidence_span_days": 1,
             "salience_last_computed": 1}
        ).to_list(10000)

        for n in nodes:
            nt = n.get("node_type", "interest")
            label = (n.get("label") or "").lower().strip()
            if label:
                cache_key = f"{user_id}:{nt}:{label}"
                self._cache[cache_key] = n

        return nodes

    def clear_cache(self):
        self._cache.clear()
