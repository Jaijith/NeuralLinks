#!/usr/bin/env python3
"""
Migration script: Dual-Memory Architecture — Phase 1 Foundation

This script is idempotent: safe to run multiple times. It checks for existing
Bayesian fields before updating.

What it does:
  1. Migrates existing graph_nodes to Bayesian parameters
  2. Migrates existing graph_edges to Bayesian parameters
  3. Creates STM collections with TTL indexes
  4. Creates enhanced LTM indexes
  5. Deduplicates nodes with same (user_id, node_type, label)
  6. Re-classifies 'preference' nodes that are voice-extracted facts → 'fact'
  7. Merges knowledge_graph → graph_nodes (if data exists)
  8. Migrates identity_memory → graph_nodes (if data exists)
  9. Creates graph_cache_bust collection

Usage:
  python -m scripts.migrate_to_bayesian
  python -m scripts.migrate_to_bayesian --dry-run
"""

import argparse
import asyncio
import logging
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, ".")
from core.database import MONGODB_URI, DB_NAME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bayesian migration helpers
# ---------------------------------------------------------------------------

def migrate_node_to_bayesian(node: Dict[str, Any]) -> Dict[str, Any]:
    """Compute initial Bayesian parameters from a legacy node's current data."""
    now = datetime.now(timezone.utc)
    strength = node.get("strength") or node.get("properties", {}).get("strength", 0.5)
    if not isinstance(strength, (int, float)):
        strength = 0.5
    strength = min(max(float(strength), 0.0), 1.0)

    mention_count = node.get("mention_count", 1)
    if not isinstance(mention_count, int) or mention_count < 1:
        mention_count = 1

    total_evidence = max(mention_count, 1)
    alpha = 1.0 + total_evidence * strength
    beta = 1.0 + total_evidence * (1.0 - strength) * 0.5

    created_at = node.get("created_at", now)
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            created_at = now

    updated_at = node.get("updated_at", now)
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            updated_at = now

    age_days = max(0, (now - created_at).days) if isinstance(created_at, datetime) else 0
    stability = min(365.0, 7.0 + total_evidence * 3.0 + age_days * 0.1)

    belief_strength = alpha / (alpha + beta)
    belief_variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))

    source = node.get("properties", {}).get("source", "unknown")
    if isinstance(source, list):
        source = source[0] if source else "unknown"

    return {
        "belief_alpha": alpha,
        "belief_beta": beta,
        "belief_strength": belief_strength,
        "belief_variance": belief_variance,
        "belief_confidence": max(0.0, min(1.0, 1.0 - belief_variance * 4)),
        "evidence_count": total_evidence,
        "evidence_log": [{
            "at": created_at if isinstance(created_at, datetime) else now,
            "source": source,
            "weight": strength,
            "subtype": "migration_initial",
            "session_id": "",
        }],
        "evidence_sources": [source],
        "first_evidence_at": created_at if isinstance(created_at, datetime) else now,
        "last_evidence_at": updated_at if isinstance(updated_at, datetime) else now,
        "mention_frequency": 0.0,
        "evidence_span_days": age_days,
        "evidence_pattern": "migration",
        "narrative_descriptor": "",
        "salience": belief_strength,
        "salience_stability": stability,
        "salience_last_computed": now,
        "status": "active",
        "strength": belief_strength,  # backwards compat
    }


def migrate_edge_to_bayesian(edge: Dict[str, Any]) -> Dict[str, Any]:
    """Compute initial Bayesian parameters from a legacy edge."""
    now = datetime.now(timezone.utc)
    weight = edge.get("weight", 0.5)
    if not isinstance(weight, (int, float)):
        weight = 0.5
    weight = min(max(float(weight), 0.0), 1.0)

    created_at = edge.get("created_at", now)
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            created_at = now

    alpha = 1.0 + weight * 2
    beta = 1.0

    return {
        "belief_alpha": alpha,
        "belief_beta": beta,
        "edge_strength": alpha / (alpha + beta),
        "valid_from": created_at if isinstance(created_at, datetime) else now,
        "valid_until": None,
        "last_evidence_at": created_at if isinstance(created_at, datetime) else now,
        "evidence_count": 1,
    }


# ---------------------------------------------------------------------------
# Step 1: Migrate graph_nodes
# ---------------------------------------------------------------------------

async def migrate_nodes(db, *, dry_run: bool = False) -> int:
    """Add Bayesian fields to all nodes that don't have them yet."""
    logger.info("STEP 1: Migrating graph_nodes to Bayesian parameters...")

    cursor = db.graph_nodes.find(
        {"belief_alpha": {"$exists": False}},
        {"_id": 1, "strength": 1, "mention_count": 1, "properties": 1,
         "created_at": 1, "updated_at": 1, "node_type": 1}
    )

    count = 0
    async for node in cursor:
        fields = migrate_node_to_bayesian(node)
        if not dry_run:
            await db.graph_nodes.update_one(
                {"_id": node["_id"]},
                {"$set": fields}
            )
        count += 1
        if count % 100 == 0:
            logger.info(f"  ... migrated {count} nodes")

    logger.info(f"  Migrated {count} nodes {'(dry-run)' if dry_run else ''}")
    return count


# ---------------------------------------------------------------------------
# Step 2: Migrate graph_edges
# ---------------------------------------------------------------------------

async def migrate_edges(db, *, dry_run: bool = False) -> int:
    """Add Bayesian fields to all edges that don't have them yet."""
    logger.info("STEP 2: Migrating graph_edges to Bayesian parameters...")

    cursor = db.graph_edges.find(
        {"belief_alpha": {"$exists": False}},
        {"_id": 1, "weight": 1, "created_at": 1,
         "from_node_id": 1, "to_node_id": 1}
    )

    # Build node → user_id lookup for edges
    node_user_map = {}
    async for n in db.graph_nodes.find({}, {"_id": 0, "id": 1, "user_id": 1}):
        nid = n.get("id")
        if nid:
            node_user_map[nid] = n.get("user_id")

    count = 0
    async for edge in cursor:
        fields = migrate_edge_to_bayesian(edge)
        # Infer user_id from connected nodes
        uid = node_user_map.get(edge.get("from_node_id")) or \
              node_user_map.get(edge.get("to_node_id"))
        if uid:
            fields["user_id"] = uid

        if not dry_run:
            await db.graph_edges.update_one(
                {"_id": edge["_id"]},
                {"$set": fields}
            )
        count += 1

    logger.info(f"  Migrated {count} edges {'(dry-run)' if dry_run else ''}")
    return count


# ---------------------------------------------------------------------------
# Step 3: Create STM collections and TTL indexes
# ---------------------------------------------------------------------------

async def create_stm_indexes(db, *, dry_run: bool = False):
    """Create STM collections and all required indexes."""
    logger.info("STEP 3: Creating STM collections and indexes...")

    if dry_run:
        logger.info("  (dry-run) Would create stm_observations and stm_edges with indexes")
        return

    # STM observation indexes
    await db.stm_observations.create_index(
        [("expires_at", 1)],
        expireAfterSeconds=0,
        name="ttl_expires_at",
    )
    await db.stm_observations.create_index(
        [("user_id", 1), ("consolidated", 1), ("observed_at", -1)],
        name="user_unconsolidated",
    )
    await db.stm_observations.create_index(
        [("user_id", 1), ("entity_label", 1), ("observed_at", -1)],
        name="user_entity_recency",
    )

    # STM edge indexes
    await db.stm_edges.create_index(
        [("expires_at", 1)],
        expireAfterSeconds=0,
        name="ttl_expires_at",
    )
    await db.stm_edges.create_index(
        [("user_id", 1), ("consolidated", 1)],
        name="user_unconsolidated",
    )

    logger.info("  Created STM indexes (stm_observations: 3, stm_edges: 2)")


# ---------------------------------------------------------------------------
# Step 4: Create enhanced LTM indexes
# ---------------------------------------------------------------------------

async def create_ltm_indexes(db, *, dry_run: bool = False):
    """Create new indexes for Bayesian-enhanced LTM queries."""
    logger.info("STEP 4: Creating enhanced LTM indexes...")

    if dry_run:
        logger.info("  (dry-run) Would create LTM indexes")
        return

    await db.graph_nodes.create_index(
        [("user_id", 1), ("belief_strength", -1)],
        name="user_belief_strength",
    )
    await db.graph_nodes.create_index(
        [("user_id", 1), ("status", 1), ("salience", -1)],
        name="user_status_salience",
    )
    await db.graph_nodes.create_index(
        [("user_id", 1), ("last_evidence_at", 1)],
        name="user_last_evidence",
    )
    await db.graph_nodes.create_index(
        [("user_id", 1), ("node_type", 1), ("status", 1)],
        name="user_type_status",
    )

    # Cache-bust collection for cross-process cache invalidation
    await db.graph_cache_bust.create_index(
        [("user_id", 1)],
        unique=True,
        name="user_id_unique",
    )

    logger.info("  Created LTM indexes (graph_nodes: 4, graph_cache_bust: 1)")


# ---------------------------------------------------------------------------
# Step 5: Deduplicate nodes
# ---------------------------------------------------------------------------

async def deduplicate_nodes(db, *, dry_run: bool = False) -> int:
    """
    Remove duplicate nodes sharing (user_id, node_type, label).
    Keeps the node with the highest strength/mention_count.
    """
    logger.info("STEP 5: Deduplicating graph_nodes...")

    pipeline = [
        {"$group": {
            "_id": {"user_id": "$user_id", "node_type": "$node_type", "label": "$label"},
            "count": {"$sum": 1},
            "ids": {"$push": "$_id"},
            "strengths": {"$push": {"$ifNull": ["$strength", 0]}},
            "mention_counts": {"$push": {"$ifNull": ["$mention_count", 0]}},
        }},
        {"$match": {"count": {"$gt": 1}}},
    ]

    removed = 0
    async for group in db.graph_nodes.aggregate(pipeline):
        ids = group["ids"]
        strengths = group["strengths"]
        mention_counts = group["mention_counts"]
        key = group["_id"]

        # Find the best node (highest strength, then highest mention_count)
        best_idx = 0
        for i in range(1, len(ids)):
            if (strengths[i], mention_counts[i]) > (strengths[best_idx], mention_counts[best_idx]):
                best_idx = i

        to_remove = [ids[i] for i in range(len(ids)) if i != best_idx]
        if to_remove:
            if not dry_run:
                await db.graph_nodes.delete_many({"_id": {"$in": to_remove}})
            removed += len(to_remove)
            logger.info(
                f"  Deduped {key['node_type']}:{key['label']} for {key['user_id'][:8]}... "
                f"— removed {len(to_remove)} duplicates"
            )

    logger.info(f"  Removed {removed} duplicate nodes {'(dry-run)' if dry_run else ''}")
    return removed


# ---------------------------------------------------------------------------
# Step 6: Re-classify 'preference' nodes that are actually facts
# ---------------------------------------------------------------------------

FACT_LABEL_PATTERNS = [
    "born in", "grew up", "from ", "lives in", "moved to", "works at",
    "works for", "studied at", "went to", "married", "divorced", "have ",
    "has ", "speaks ", "native ", "age ", "years old",
]


async def reclassify_fact_preferences(db, *, dry_run: bool = False) -> int:
    """
    Voice memory stores facts as node_type='preference' with source='conversation'.
    Re-classify ones that match fact-like patterns.
    """
    logger.info("STEP 6: Re-classifying voice 'preference' nodes that are actually facts...")

    count = 0
    cursor = db.graph_nodes.find({
        "node_type": "preference",
        "$or": [
            {"properties.source": "conversation"},
            {"properties.service": "voice"},
        ]
    })

    async for node in cursor:
        label = (node.get("label") or "").lower()
        full_text = (node.get("full_text") or "").lower()
        text_to_check = full_text or label

        is_fact = any(pattern in text_to_check for pattern in FACT_LABEL_PATTERNS)
        if is_fact:
            if not dry_run:
                await db.graph_nodes.update_one(
                    {"_id": node["_id"]},
                    {"$set": {"node_type": "fact"}}
                )
            count += 1

    logger.info(f"  Re-classified {count} nodes from 'preference' to 'fact' {'(dry-run)' if dry_run else ''}")
    return count


# ---------------------------------------------------------------------------
# Step 7: Merge knowledge_graph → graph_nodes
# ---------------------------------------------------------------------------

async def merge_knowledge_graph(db, *, dry_run: bool = False) -> int:
    """
    Merge the parallel 'knowledge_graph' collection into 'graph_nodes'.
    Maps field 'type' → 'node_type'. Skips nodes that already exist in graph_nodes.
    """
    logger.info("STEP 7: Merging knowledge_graph → graph_nodes...")

    kg_count = await db.knowledge_graph.count_documents({})
    if kg_count == 0:
        logger.info("  knowledge_graph is empty — nothing to merge")
        return 0

    logger.info(f"  Found {kg_count} documents in knowledge_graph")
    merged = 0
    skipped = 0

    async for doc in db.knowledge_graph.find({}, {"_id": 0}):
        user_id = doc.get("user_id", "")
        node_type = doc.get("type", doc.get("node_type", "interest"))
        label = (doc.get("label") or "").lower().strip()

        if not user_id or not label:
            skipped += 1
            continue

        existing = await db.graph_nodes.find_one({
            "user_id": user_id,
            "node_type": node_type,
            "label": label,
        })

        if existing:
            skipped += 1
            continue

        now = datetime.now(timezone.utc)
        props = doc.get("properties", {})
        strength = props.get("strength", 0.5)
        if not isinstance(strength, (int, float)):
            strength = 0.5

        new_node = {
            "id": doc.get("id", doc.get("node_id", f"{node_type}_{user_id}_{label.replace(' ', '_')}")),
            "user_id": user_id,
            "node_type": node_type,
            "label": label,
            "display_label": doc.get("display_label", label.title()),
            "strength": float(strength),
            "mention_count": props.get("mention_count", 1),
            "properties": props,
            "created_at": doc.get("created_at", now),
            "updated_at": doc.get("updated_at", now),
        }

        bayesian_fields = migrate_node_to_bayesian(new_node)
        new_node.update(bayesian_fields)

        if not dry_run:
            await db.graph_nodes.insert_one(new_node)
        merged += 1

    logger.info(f"  Merged {merged}, skipped {skipped} (already exist) {'(dry-run)' if dry_run else ''}")
    return merged


# ---------------------------------------------------------------------------
# Step 8: Migrate identity_memory → graph_nodes
# ---------------------------------------------------------------------------

async def migrate_identity_memory(db, *, dry_run: bool = False) -> int:
    """
    Ensure all facts/interests in identity_memory have corresponding graph_nodes.
    """
    logger.info("STEP 8: Migrating identity_memory → graph_nodes...")

    im_count = await db.identity_memory.count_documents({})
    if im_count == 0:
        logger.info("  identity_memory is empty — nothing to migrate")
        return 0

    logger.info(f"  Found {im_count} identity_memory documents")
    created = 0
    now = datetime.now(timezone.utc)

    async for doc in db.identity_memory.find({}, {"_id": 0}):
        user_id = doc.get("user_id", "")
        if not user_id:
            continue

        # Migrate interests
        for interest in doc.get("interests", []):
            topic = (interest.get("topic") or "").strip()
            if not topic:
                continue
            label = topic.lower()

            existing = await db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": "interest",
                "label": label,
            })
            if existing:
                continue

            node = {
                "id": f"interest_{user_id}_{label.replace(' ', '_')}",
                "user_id": user_id,
                "node_type": "interest",
                "label": label,
                "display_label": topic.title(),
                "strength": 0.5,
                "mention_count": 1,
                "properties": {"source": "identity_memory_migration"},
                "created_at": now,
                "updated_at": now,
            }
            bayesian_fields = migrate_node_to_bayesian(node)
            node.update(bayesian_fields)

            if not dry_run:
                await db.graph_nodes.insert_one(node)
            created += 1

        # Migrate facts
        for fact in doc.get("facts", []):
            fact_text = (fact.get("fact") or "").strip()
            if not fact_text or len(fact_text) < 5:
                continue
            label = " ".join(fact_text.split()[:4]).lower()

            existing = await db.graph_nodes.find_one({
                "user_id": user_id,
                "$or": [
                    {"node_type": "fact", "label": label},
                    {"node_type": "preference", "label": label},
                ]
            })
            if existing:
                continue

            node = {
                "id": f"fact_{user_id}_{label.replace(' ', '_')}",
                "user_id": user_id,
                "node_type": "fact",
                "label": label,
                "display_label": fact_text[:50],
                "full_text": fact_text,
                "strength": 0.7,
                "mention_count": 1,
                "properties": {"source": "identity_memory_migration"},
                "created_at": now,
                "updated_at": now,
            }
            bayesian_fields = migrate_node_to_bayesian(node)
            node.update(bayesian_fields)

            if not dry_run:
                await db.graph_nodes.insert_one(node)
            created += 1

    logger.info(f"  Created {created} new graph_nodes from identity_memory {'(dry-run)' if dry_run else ''}")
    return created


# ---------------------------------------------------------------------------
# Step 9: Verify knowledge_graph_nodes collection
# ---------------------------------------------------------------------------

async def check_knowledge_graph_nodes(db):
    """Report on the knowledge_graph_nodes collection status."""
    logger.info("STEP 9: Checking knowledge_graph_nodes collection...")

    count = await db.knowledge_graph_nodes.count_documents({})
    if count == 0:
        logger.info("  knowledge_graph_nodes is empty (serendipity/recap may return no results)")
    else:
        logger.info(f"  knowledge_graph_nodes has {count} documents")
        sample = await db.knowledge_graph_nodes.find_one({}, {"_id": 0})
        if sample:
            fields = list(sample.keys())
            logger.info(f"  Sample fields: {fields}")
        logger.info("  ACTION NEEDED: Update serendipity_engine.py and recap_generator.py to read from graph_nodes")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_migration(dry_run: bool = False):
    """Execute the full Phase 1 migration."""
    mode = "DRY RUN" if dry_run else "LIVE"
    logger.info("=" * 60)
    logger.info(f"Dual-Memory Architecture — Phase 1 Migration ({mode})")
    logger.info("=" * 60)

    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]

    try:
        # Pre-migration stats
        node_count = await db.graph_nodes.count_documents({})
        edge_count = await db.graph_edges.count_documents({})
        logger.info(f"Pre-migration: {node_count} graph_nodes, {edge_count} graph_edges")

        # Run all steps
        nodes_migrated = await migrate_nodes(db, dry_run=dry_run)
        edges_migrated = await migrate_edges(db, dry_run=dry_run)
        await create_stm_indexes(db, dry_run=dry_run)
        await create_ltm_indexes(db, dry_run=dry_run)
        deduped = await deduplicate_nodes(db, dry_run=dry_run)
        reclassified = await reclassify_fact_preferences(db, dry_run=dry_run)
        kg_merged = await merge_knowledge_graph(db, dry_run=dry_run)
        im_migrated = await migrate_identity_memory(db, dry_run=dry_run)
        await check_knowledge_graph_nodes(db)

        # Post-migration stats
        if not dry_run:
            final_nodes = await db.graph_nodes.count_documents({})
            bayesian_nodes = await db.graph_nodes.count_documents({"belief_alpha": {"$exists": True}})
            logger.info("")
            logger.info("=" * 60)
            logger.info("MIGRATION COMPLETE")
            logger.info(f"  Total graph_nodes: {final_nodes}")
            logger.info(f"  Bayesian-enhanced: {bayesian_nodes}")
            logger.info(f"  Nodes migrated: {nodes_migrated}")
            logger.info(f"  Edges migrated: {edges_migrated}")
            logger.info(f"  Duplicates removed: {deduped}")
            logger.info(f"  Re-classified: {reclassified}")
            logger.info(f"  knowledge_graph merged: {kg_merged}")
            logger.info(f"  identity_memory migrated: {im_migrated}")
            logger.info("=" * 60)
        else:
            logger.info("")
            logger.info("DRY RUN COMPLETE — no changes written")

    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate to Bayesian dual-memory architecture")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()
    asyncio.run(run_migration(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
