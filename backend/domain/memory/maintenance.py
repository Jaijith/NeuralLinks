"""
Memory Maintenance — Weekly housekeeping job.

Runs periodically (weekly recommended) to:
1. Archive fading nodes — nodes with salience < threshold for extended periods
   are moved to an archive collection so they stop appearing in queries.
2. Prune orphan edges — edges where one or both nodes no longer exist.
3. Clean expired STM — MongoDB TTL handles most of this, but we also
   clean up any stragglers and update stats.
4. Compact evidence logs — cap very long evidence_log arrays to prevent
   document size growth.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

FADING_ARCHIVE_DAYS = 30
MAX_EVIDENCE_LOG_ENTRIES = 50
ARCHIVE_SALIENCE_THRESHOLD = 0.02


class MemoryMaintenance:
    """
    Weekly maintenance tasks for the dual-memory system.

    Usage:
        maintenance = MemoryMaintenance(db)
        report = await maintenance.run_all()
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def run_all(self) -> Dict[str, Any]:
        """Run all maintenance tasks and return a combined report."""
        logger.info("=== Memory maintenance starting ===")

        archived = await self.archive_fading_nodes()
        pruned = await self.prune_orphan_edges()
        stm_cleaned = await self.clean_stm_stragglers()
        compacted = await self.compact_evidence_logs()

        report = {
            "archived_nodes": archived,
            "pruned_edges": pruned,
            "stm_cleaned": stm_cleaned,
            "evidence_logs_compacted": compacted,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("Memory maintenance complete: %s", report)
        return report

    async def archive_fading_nodes(self) -> int:
        """
        Move nodes that have been fading for >FADING_ARCHIVE_DAYS into
        an archive collection. They can be restored if needed.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=FADING_ARCHIVE_DAYS)

        fading_nodes = await self.db.graph_nodes.find(
            {
                "status": "fading",
                "salience": {"$lt": ARCHIVE_SALIENCE_THRESHOLD},
                "salience_last_computed": {"$lt": cutoff},
            }
        ).to_list(1000)

        if not fading_nodes:
            logger.info("No fading nodes to archive")
            return 0

        now = datetime.now(timezone.utc)
        for node in fading_nodes:
            node["archived_at"] = now
            node["original_id"] = node.pop("_id")

        await self.db.graph_nodes_archive.insert_many(fading_nodes)

        ids_to_remove = [n["original_id"] for n in fading_nodes]
        result = await self.db.graph_nodes.delete_many(
            {"_id": {"$in": ids_to_remove}}
        )

        logger.info("Archived %d fading nodes", result.deleted_count)
        return result.deleted_count

    async def prune_orphan_edges(self) -> int:
        """
        Remove edges where one or both endpoint nodes no longer exist
        in graph_nodes.
        """
        all_node_ids = set(
            await self.db.graph_nodes.distinct("id")
        )

        if not all_node_ids:
            return 0

        orphan_ids = []
        cursor = self.db.graph_edges.find(
            {},
            {"_id": 1, "from_node_id": 1, "to_node_id": 1},
        )

        async for edge in cursor:
            fid = edge.get("from_node_id")
            tid = edge.get("to_node_id")
            if fid not in all_node_ids or tid not in all_node_ids:
                orphan_ids.append(edge["_id"])

        if not orphan_ids:
            logger.info("No orphan edges found")
            return 0

        result = await self.db.graph_edges.delete_many(
            {"_id": {"$in": orphan_ids}}
        )

        logger.info("Pruned %d orphan edges", result.deleted_count)
        return result.deleted_count

    async def clean_stm_stragglers(self) -> int:
        """
        Clean up STM observations that are consolidated AND older than 30 days.
        MongoDB TTL index handles most expiry, but consolidated observations
        that had their expires_at extended can linger.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        result = await self.db.stm_observations.delete_many(
            {
                "consolidated": True,
                "observed_at": {"$lt": cutoff},
            }
        )

        if result.deleted_count > 0:
            logger.info("Cleaned %d stale STM observations", result.deleted_count)

        # Also clean stm_edges
        edge_result = await self.db.stm_edges.delete_many(
            {
                "consolidated": True,
                "observed_at": {"$lt": cutoff},
            }
        )

        return result.deleted_count + edge_result.deleted_count

    async def compact_evidence_logs(self) -> int:
        """
        Cap evidence_log arrays to MAX_EVIDENCE_LOG_ENTRIES.
        Keeps the most recent entries and a summary of older ones.
        """
        bloated = await self.db.graph_nodes.find(
            {
                f"evidence_log.{MAX_EVIDENCE_LOG_ENTRIES}": {"$exists": True},
            },
            {"_id": 1, "evidence_log": 1, "label": 1},
        ).to_list(500)

        compacted = 0
        for node in bloated:
            log = node.get("evidence_log", [])
            if len(log) <= MAX_EVIDENCE_LOG_ENTRIES:
                continue

            trimmed_count = len(log) - MAX_EVIDENCE_LOG_ENTRIES
            kept = log[-MAX_EVIDENCE_LOG_ENTRIES:]

            kept.insert(0, {
                "at": datetime.now(timezone.utc),
                "source": "maintenance_compaction",
                "weight": 0,
                "subtype": f"compacted_{trimmed_count}_older_entries",
                "session_id": "",
            })

            await self.db.graph_nodes.update_one(
                {"_id": node["_id"]},
                {"$set": {"evidence_log": kept}},
            )
            compacted += 1

        if compacted > 0:
            logger.info("Compacted evidence logs for %d nodes", compacted)
        return compacted

    async def restore_archived_node(
        self, user_id: str, label: str
    ) -> bool:
        """
        Restore a previously archived node back to graph_nodes.
        """
        archived = await self.db.graph_nodes_archive.find_one(
            {"user_id": user_id, "label": label.lower().strip()},
        )
        if not archived:
            return False

        original_id = archived.pop("original_id", None)
        archived.pop("archived_at", None)
        if original_id:
            archived["_id"] = original_id

        archived["status"] = "active"
        archived["salience"] = 0.3
        archived["salience_last_computed"] = datetime.now(timezone.utc)

        await self.db.graph_nodes.insert_one(archived)
        await self.db.graph_nodes_archive.delete_one(
            {"user_id": user_id, "label": label.lower().strip()}
        )

        logger.info("Restored archived node '%s' for user %s", label, user_id[:8])
        return True
