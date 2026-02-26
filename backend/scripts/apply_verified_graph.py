#!/usr/bin/env python3
"""
Apply the manually verified graph to the production database.

This script:
  1. Backs up the current graph_nodes and graph_edges
  2. Replaces ALL nodes/edges for DigitalHunter with the verified graph
  3. Fixes identity_memory (Vasubhadra → Subhadra)
  4. Invalidates the personality prompt cache

Usage:
  python apply_verified_graph.py             # dry-run (preview changes)
  python apply_verified_graph.py --live      # apply to production
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("apply_graph")

USER_ID = "dedc30ef-dca9-467d-84b1-5e643941e6fd"
DB_NAME = "neurallinks_local"
SECRETS_REGION = "us-west-2"
GRAPH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verified_graph")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
GRAPH_FILE = os.path.join(GRAPH_DIR, "verified_graph.json")


def get_secret(secret_name: str):
    import boto3
    client = boto3.client("secretsmanager", region_name=SECRETS_REGION)
    raw = client.get_secret_value(SecretId=secret_name)["SecretString"]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def get_mongo_uri() -> str:
    secret = get_secret("2n1/mongodb/uri")
    if isinstance(secret, dict):
        return secret.get("uri") or secret.get("MONGO_URL") or secret.get("connection_string", "")
    return secret


async def rollback(backup_nodes_file: str, backup_edges_file: str):
    """Restore graph from backup files."""
    from motor.motor_asyncio import AsyncIOMotorClient

    if not os.path.exists(backup_nodes_file):
        logger.error(f"Backup nodes file not found: {backup_nodes_file}")
        return
    if not os.path.exists(backup_edges_file):
        logger.error(f"Backup edges file not found: {backup_edges_file}")
        return

    with open(backup_nodes_file) as f:
        backup_nodes = json.load(f)
    with open(backup_edges_file) as f:
        backup_edges = json.load(f)

    logger.info(f"Loaded backup: {len(backup_nodes)} nodes, {len(backup_edges)} edges")

    mongo_uri = get_mongo_uri()
    client = AsyncIOMotorClient(mongo_uri)
    db = client[DB_NAME]

    try:
        del_nodes = await db.graph_nodes.delete_many({"user_id": USER_ID})
        logger.info(f"  Deleted {del_nodes.deleted_count} current nodes")

        current_node_ids = [n.get("id", "") for n in backup_nodes if n.get("id")]
        del_edges = await db.graph_edges.delete_many({"$or": [
            {"user_id": USER_ID},
            {"from_node_id": {"$in": current_node_ids}},
            {"to_node_id": {"$in": current_node_ids}},
        ]})
        logger.info(f"  Deleted {del_edges.deleted_count} current edges")

        if backup_nodes:
            await db.graph_nodes.insert_many(backup_nodes)
            logger.info(f"  Restored {len(backup_nodes)} nodes from backup")
        if backup_edges:
            await db.graph_edges.insert_many(backup_edges)
            logger.info(f"  Restored {len(backup_edges)} edges from backup")

        del_cache = await db.avatar_personality_prompts.delete_many(
            {"$or": [{"user_id": USER_ID}, {"avatar_id": USER_ID}]}
        )
        logger.info(f"  Invalidated {del_cache.deleted_count} cached prompts")

        final_count = await db.graph_nodes.count_documents({"user_id": USER_ID})
        logger.info(f"\n  ROLLBACK COMPLETE — {final_count} nodes in DB")
    finally:
        client.close()


async def main(dry_run: bool):
    from motor.motor_asyncio import AsyncIOMotorClient

    if not os.path.exists(GRAPH_FILE):
        logger.error(f"Verified graph not found at {GRAPH_FILE}")
        logger.error("Run build_verified_graph.py first")
        return

    with open(GRAPH_FILE) as f:
        graph = json.load(f)

    nodes = graph["nodes"]
    edges = graph["edges"]
    logger.info(f"Loaded verified graph: {len(nodes)} nodes, {len(edges)} edges")

    # Connect to MongoDB
    mongo_uri = get_mongo_uri()
    client = AsyncIOMotorClient(mongo_uri)
    db = client[DB_NAME]

    try:
        # ── Phase 1: Backup ────────────────────────────────────────────
        logger.info("Phase 1: Backing up current data...")
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        old_nodes = await db.graph_nodes.find(
            {"user_id": USER_ID}, {"_id": 0}
        ).to_list(10000)
        old_edges_q = {"$or": [
            {"user_id": USER_ID},
            {"from_node_id": {"$in": [n["id"] for n in old_nodes]}},
        ]}
        old_edges = await db.graph_edges.find(old_edges_q, {"_id": 0}).to_list(10000)

        backup_nodes_path = os.path.join(BACKUP_DIR, f"pre_apply_{ts}_nodes.json")
        backup_edges_path = os.path.join(BACKUP_DIR, f"pre_apply_{ts}_edges.json")
        with open(backup_nodes_path, "w") as f:
            json.dump(old_nodes, f, indent=2, default=str)
        with open(backup_edges_path, "w") as f:
            json.dump(old_edges, f, indent=2, default=str)
        logger.info(f"  Backed up {len(old_nodes)} nodes -> {backup_nodes_path}")
        logger.info(f"  Backed up {len(old_edges)} edges -> {backup_edges_path}")

        if dry_run:
            logger.info("\n=== DRY RUN MODE ===")
            logger.info(f"Would delete {len(old_nodes)} existing nodes")
            logger.info(f"Would delete {len(old_edges)} existing edges")
            logger.info(f"Would insert {len(nodes)} verified nodes")
            logger.info(f"Would insert {len(edges)} verified edges")

            logger.info("\nNode type breakdown:")
            from collections import Counter
            for t, c in Counter(n["node_type"] for n in nodes).most_common():
                logger.info(f"  {t}: {c}")

            logger.info("\nEdge type breakdown:")
            for t, c in Counter(e["relationship_type"] for e in edges).most_common():
                logger.info(f"  {t}: {c}")

            logger.info("\nSample nodes:")
            for n in nodes[:5]:
                logger.info(f"  [{n['node_type']}] {n['display_label']} (strength={n['strength']})")

            logger.info("\nWould also fix identity_memory: Vasubhadra -> Subhadra")
            logger.info("Would also invalidate personality prompt cache")
            logger.info("\nRun with --live to apply these changes.")
            return

        # ── Phase 2: Delete old graph ──────────────────────────────────
        logger.info("Phase 2: Removing old graph data...")

        old_node_ids = [n["id"] for n in old_nodes]
        del_nodes = await db.graph_nodes.delete_many({"user_id": USER_ID})
        logger.info(f"  Deleted {del_nodes.deleted_count} old nodes")

        del_edges = await db.graph_edges.delete_many({"$or": [
            {"user_id": USER_ID},
            {"from_node_id": {"$in": old_node_ids}},
            {"to_node_id": {"$in": old_node_ids}},
        ]})
        logger.info(f"  Deleted {del_edges.deleted_count} old edges")

        # ── Phase 3: Insert verified graph ─────────────────────────────
        logger.info("Phase 3: Inserting verified graph...")

        if nodes:
            await db.graph_nodes.insert_many(nodes)
            logger.info(f"  Inserted {len(nodes)} verified nodes")

        if edges:
            await db.graph_edges.insert_many(edges)
            logger.info(f"  Inserted {len(edges)} verified edges")

        # ── Phase 4: Fix identity_memory ───────────────────────────────
        logger.info("Phase 4: Fixing identity_memory (Vasubhadra -> Subhadra)...")

        identity_docs = await db.identity_memory.find(
            {"user_id": USER_ID}
        ).to_list(100)

        for doc in identity_docs:
            updated = False
            facts = doc.get("facts", [])
            for fact in facts:
                old_fact = fact.get("fact", "")
                if "Vasubhadra" in old_fact:
                    fact["fact"] = old_fact.replace("Vasubhadra", "Subhadra")
                    updated = True

            if updated:
                await db.identity_memory.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"facts": facts, "updated_at": datetime.now(timezone.utc)}}
                )
                logger.info(f"  Fixed Vasubhadra -> Subhadra in identity_memory doc")

        # Revert earlier wrong fix: Srijit back to Sreejith (user confirmed Sreejith is correct)
        logger.info("Phase 4b: Ensuring connections use correct names...")
        user = await db.users.find_one({"id": USER_ID})
        if user and user.get("connections"):
            updated_connections = []
            changed = False
            for conn in user["connections"]:
                if conn.get("name") == "Srijit":
                    conn["name"] = "Sreejith"
                    changed = True
                updated_connections.append(conn)
            if changed:
                await db.users.update_one(
                    {"id": USER_ID},
                    {"$set": {"connections": updated_connections}}
                )
                logger.info("  Reverted Srijit -> Sreejith in user connections")

        # ── Phase 5: Invalidate personality prompt cache ───────────────
        logger.info("Phase 5: Invalidating personality prompt cache...")
        del_cache = await db.avatar_personality_prompts.delete_many(
            {"$or": [{"user_id": USER_ID}, {"avatar_id": USER_ID}]}
        )
        logger.info(f"  Deleted {del_cache.deleted_count} cached personality prompts")

        # ── Phase 6: Post-deployment verification ──────────────────────
        logger.info("Phase 6: Post-deployment verification...")

        new_node_count = await db.graph_nodes.count_documents({"user_id": USER_ID})
        new_node_ids = [n["id"] for n in nodes]
        new_edge_count = await db.graph_edges.count_documents(
            {"$or": [
                {"user_id": USER_ID},
                {"from_node_id": {"$in": new_node_ids}},
            ]}
        )

        logger.info(f"  Nodes in DB: {new_node_count} (expected: {len(nodes)})")
        logger.info(f"  Edges in DB: {new_edge_count} (expected: {len(edges)})")

        if new_node_count == len(nodes) and new_edge_count == len(edges):
            logger.info("\n  DEPLOYMENT SUCCESSFUL")
        else:
            logger.error("\n  MISMATCH DETECTED — check data manually!")

        # Verify a few specific nodes
        test_cases = [
            ("connection", "subhadra", "Subhadra"),
            ("connection", "manju", "Manju"),
            ("connection", "sreejith", "Sreejith"),
            ("trait", "persistent", "Persistent"),
            ("demographic", "origin:thiruvananthapuram, kerala, india", "Thiruvananthapuram, Kerala, India"),
            ("demographic", "job:software engineer", "Software Engineer"),
            ("demographic", "language:malayalam", "Malayalam"),
            ("interest", "linkin park", "Linkin Park"),
            ("interest", "chess", "Chess"),
        ]
        all_pass = True
        for ntype, label, display in test_cases:
            found = await db.graph_nodes.find_one(
                {"user_id": USER_ID, "node_type": ntype, "label": label}
            )
            if found:
                logger.info(f"  [{ntype}] {display}: found (strength={found.get('strength')})")
            else:
                logger.error(f"  [{ntype}] {display}: NOT FOUND!")
                all_pass = False

        # Verify hallucinations are GONE
        hallucination_checks = [
            "works at google", "moved to seattle", "vasubhadra",
            "does not have a", "jaijith is from thiruvananthapuram",
        ]
        for bad_label in hallucination_checks:
            found = await db.graph_nodes.find_one(
                {"user_id": USER_ID, "label": {"$regex": bad_label, "$options": "i"}}
            )
            if found:
                logger.error(f"  HALLUCINATION STILL PRESENT: '{bad_label}'")
                all_pass = False
            else:
                logger.info(f"  Confirmed removed: '{bad_label}'")

        # Verify connection types
        logger.info("  Checking connection relationship types...")
        conn_nodes = await db.graph_nodes.find(
            {"user_id": USER_ID, "node_type": "connection"},
            {"_id": 0, "label": 1, "display_label": 1, "properties.relationship_type": 1, "properties.relationship": 1}
        ).to_list(20)
        for cn in conn_nodes:
            rt = cn.get("properties", {}).get("relationship_type", "?")
            rel = cn.get("properties", {}).get("relationship", "?")
            logger.info(f"    {cn.get('display_label', cn['label'])}: {rel} ({rt})")

        # Verify edge types are meaningful (not co_occurs_with)
        bad_edges = await db.graph_edges.count_documents({
            "user_id": USER_ID,
            "relationship_type": "co_occurs_with"
        })
        if bad_edges > 0:
            logger.warning(f"  {bad_edges} co_occurs_with edges still present")
        else:
            logger.info("  No co_occurs_with edges — all edges are meaningful")

        if all_pass:
            logger.info("\n  ALL CHECKS PASSED — Graph is clean and verified!")
        else:
            logger.error("\n  SOME CHECKS FAILED — Review output above")

    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply verified graph to production")
    parser.add_argument("--live", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("--rollback", action="store_true", help="Rollback to a backup")
    parser.add_argument("--backup-file", type=str, help="Path to backup nodes JSON for rollback")
    args = parser.parse_args()

    if args.rollback:
        if not args.backup_file:
            logger.error("--rollback requires --backup-file <path_to_nodes.json>")
            sys.exit(1)
        nodes_file = args.backup_file
        edges_file = nodes_file.replace("_nodes.json", "_edges.json")
        logger.warning(f"ROLLBACK MODE — Restoring from {nodes_file}")
        asyncio.run(rollback(nodes_file, edges_file))
    elif args.live:
        logger.warning("LIVE MODE — Changes will be applied to production!")
        asyncio.run(main(dry_run=False))
    else:
        logger.info("DRY-RUN MODE — No changes will be made")
        asyncio.run(main(dry_run=True))
