#!/usr/bin/env python3
"""
Apply the manually verified graph for _bLikker / Sreejith Sreekantan to the production database.

This script:
  1. Backs up the current graph_nodes and graph_edges for this user
  2. Replaces ALL nodes/edges with the verified graph (atomic delete + insert)
  3. Fixes related collections (identity_memory, users.connections)
  4. Invalidates the personality prompt cache
  5. Comprehensive post-deployment verification

Usage:
  python apply_verified_graph_blikker.py             # dry-run (preview changes)
  python apply_verified_graph_blikker.py --live       # apply to production
  python apply_verified_graph_blikker.py --rollback --backup-file <path>  # restore from backup
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from domain.memory.bayesian import add_bayesian_defaults, add_bayesian_edge_defaults

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("apply_graph_blikker")

USER_ID = "fb1a5d18-5c93-4084-8da1-2227b1bea266"
DB_NAME = "neurallinks_local"
SECRETS_REGION = "us-west-2"
GRAPH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verified_graph_blikker")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups_blikker")
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
        await db.graph_nodes.delete_many({"user_id": USER_ID})
        if backup_nodes:
            for n in backup_nodes:
                add_bayesian_defaults(n, prior="strong", source="verified_graph")
            await db.graph_nodes.insert_many(backup_nodes)
        node_ids = [n["id"] for n in backup_nodes if n.get("id")]
        await db.graph_edges.delete_many({
            "$or": [{"user_id": USER_ID}, {"from_node_id": {"$in": node_ids}}, {"to_node_id": {"$in": node_ids}}]
        })
        if backup_edges:
            for e in backup_edges:
                add_bayesian_edge_defaults(e)
            await db.graph_edges.insert_many(backup_edges)
        await db.avatar_personality_prompts.delete_many({"user_id": USER_ID})
        logger.info("ROLLBACK COMPLETE")
    finally:
        client.close()


async def main(dry_run: bool):
    from motor.motor_asyncio import AsyncIOMotorClient

    if not os.path.exists(GRAPH_FILE):
        logger.error(f"Graph file not found: {GRAPH_FILE}")
        logger.error("Run build_verified_graph_blikker.py first!")
        return

    with open(GRAPH_FILE) as f:
        graph = json.load(f)

    new_nodes = graph["nodes"]
    new_edges = graph["edges"]
    logger.info(f"Loaded verified graph: {len(new_nodes)} nodes, {len(new_edges)} edges")

    mongo_uri = get_mongo_uri()
    client = AsyncIOMotorClient(mongo_uri)
    db = client[DB_NAME]

    try:
        host_info = await client.admin.command("ismaster")
        hosts = host_info.get("hosts", [host_info.get("me", "unknown")])
        logger.info(f"Connected to MongoDB: {hosts}")

        # ── PHASE 1: Backup ──────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("PHASE 1: Backing up current data")
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        old_nodes = await db.graph_nodes.find({"user_id": USER_ID}, {"_id": 0}).to_list(10000)
        backup_nodes_path = os.path.join(BACKUP_DIR, f"nodes_backup_{ts}.json")
        with open(backup_nodes_path, "w") as f:
            json.dump(old_nodes, f, indent=2, default=str)
        logger.info(f"  Backed up {len(old_nodes)} nodes -> {backup_nodes_path}")

        old_node_ids = [n["id"] for n in old_nodes if n.get("id")]
        old_edges = await db.graph_edges.find(
            {"$or": [{"user_id": USER_ID}, {"from_node_id": {"$in": old_node_ids}}, {"to_node_id": {"$in": old_node_ids}}]},
            {"_id": 0}
        ).to_list(10000)
        backup_edges_path = os.path.join(BACKUP_DIR, f"edges_backup_{ts}.json")
        with open(backup_edges_path, "w") as f:
            json.dump(old_edges, f, indent=2, default=str)
        logger.info(f"  Backed up {len(old_edges)} edges -> {backup_edges_path}")

        if dry_run:
            logger.info("DRY RUN — would make the following changes:")
            logger.info(f"  Delete: {len(old_nodes)} nodes, {len(old_edges)} edges")
            logger.info(f"  Insert: {len(new_nodes)} nodes, {len(new_edges)} edges")
            logger.info("  Fix 'Rabsina' -> 'Rafseena Sedeed' in users.connections")
            logger.info("  Invalidate personality prompt cache")
            logger.info("Run with --live to apply.")
            client.close()
            return

        # ── PHASE 2: Delete old graph ────────────────────────────────────
        logger.info("=" * 60)
        logger.info("PHASE 2: Removing old graph data")
        del_nodes = await db.graph_nodes.delete_many({"user_id": USER_ID})
        logger.info(f"  Deleted {del_nodes.deleted_count} nodes")

        del_edges = await db.graph_edges.delete_many(
            {"$or": [{"user_id": USER_ID}, {"from_node_id": {"$in": old_node_ids}}, {"to_node_id": {"$in": old_node_ids}}]}
        )
        logger.info(f"  Deleted {del_edges.deleted_count} edges")

        # ── PHASE 3: Insert verified graph ───────────────────────────────
        logger.info("=" * 60)
        logger.info("PHASE 3: Inserting verified graph")
        if new_nodes:
            for n in new_nodes:
                add_bayesian_defaults(n, prior="strong", source="verified_graph")
            await db.graph_nodes.insert_many(new_nodes)
            logger.info(f"  Inserted {len(new_nodes)} nodes")
        if new_edges:
            for e in new_edges:
                add_bayesian_edge_defaults(e)
            await db.graph_edges.insert_many(new_edges)
            logger.info(f"  Inserted {len(new_edges)} edges")

        # ── PHASE 4: Fix users.connections ───────────────────────────────
        logger.info("=" * 60)
        logger.info("PHASE 4: Fixing related collections")

        user_doc = await db.users.find_one({"id": USER_ID}, {"connections": 1})
        if user_doc and user_doc.get("connections"):
            conns = user_doc["connections"]
            updated_conns = []
            fixed = False
            for c in conns:
                name = c.get("name", "")
                if name.lower() in ("rabsina", "rafseena sedeed"):
                    c["name"] = "Rafseena Sedeed"
                    c["relationship"] = "colleague_and_co_architect"
                    c["details"] = "Co-principal architect at Vili & Vé Architecture Studio"
                    fixed = True
                    logger.info(f"  Fixed connection: {name} -> Rafseena Sedeed (colleague)")
                updated_conns.append(c)
            if fixed:
                await db.users.update_one({"id": USER_ID}, {"$set": {"connections": updated_conns}})
                logger.info("  Updated users.connections")
            else:
                logger.info("  No Rabsina/Rafseena connection found to fix")

        # ── PHASE 5: Invalidate personality prompt cache ─────────────────
        logger.info("=" * 60)
        logger.info("PHASE 5: Invalidating caches")
        del_cache = await db.avatar_personality_prompts.delete_many({"user_id": USER_ID})
        logger.info(f"  Deleted {del_cache.deleted_count} cached personality prompts")

        # ── PHASE 6: Post-deployment verification ────────────────────────
        logger.info("=" * 60)
        logger.info("PHASE 6: Post-deployment verification")

        live_nodes = await db.graph_nodes.count_documents({"user_id": USER_ID})
        new_node_ids = [n["id"] for n in new_nodes]
        live_edges = await db.graph_edges.count_documents(
            {"$or": [{"user_id": USER_ID}, {"from_node_id": {"$in": new_node_ids}}, {"to_node_id": {"$in": new_node_ids}}]}
        )
        logger.info(f"  Live node count: {live_nodes} (expected {len(new_nodes)})")
        logger.info(f"  Live edge count: {live_edges} (expected {len(new_edges)})")

        checks_passed = 0
        checks_total = 0

        def check(name, condition):
            nonlocal checks_passed, checks_total
            checks_total += 1
            if condition:
                checks_passed += 1
                logger.info(f"  [PASS] {name}")
            else:
                logger.error(f"  [FAIL] {name}")

        check("Node count matches", live_nodes == len(new_nodes))
        check("Edge count matches", live_edges == len(new_edges))

        # Spot checks
        rafseena_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "connection", "label": "rafseena sedeed"}
        )
        check("Rafseena Sedeed connection exists", rafseena_node is not None)
        if rafseena_node:
            check("Rafseena relationship = husband_of",
                  rafseena_node.get("properties", {}).get("relationship_type") == "husband_of")

        jaleel_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "connection", "label": "abdul jaleel"}
        )
        check("Abdul Jaleel connection exists", jaleel_node is not None)

        mom_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "connection", "label": "mom"}
        )
        check("Mom connection exists", mom_node is not None)

        kozhikode_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "demographic", "label": {"$regex": "kozhikode", "$options": "i"}}
        )
        check("Kozhikode location exists", kozhikode_node is not None)

        arch_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "interest", "label": "architecture"}
        )
        check("Architecture interest exists", arch_node is not None)
        if arch_node:
            check("Architecture strength = 1.0", arch_node.get("strength") == 1.0)

        heritage_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "interest", "label": "heritage-inspired design"}
        )
        check("Heritage design interest exists", heritage_node is not None)

        nadumuttam_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "interest", "label": "nadumuttams"}
        )
        check("Nadumuttams interest exists", nadumuttam_node is not None)

        rendering_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "interest", "label": "architectural rendering"}
        )
        check("Architectural rendering interest exists", rendering_node is not None)

        studio_exp = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "experience", "label": {"$regex": "vili", "$options": "i"}}
        )
        check("Founded Vili & Vé experience exists", studio_exp is not None)

        norse_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "interest", "label": "norse mythology"}
        )
        check("Norse mythology interest exists", norse_node is not None)

        job_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "demographic", "label": {"$regex": "architect", "$options": "i"}}
        )
        check("Architect job exists", job_node is not None)

        badminton_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "interest", "label": "badminton"}
        )
        check("Badminton interest exists", badminton_node is not None)

        goa_node = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "node_type": "interest", "label": "goa road trips"}
        )
        check("Goa road trips interest exists", goa_node is not None)

        # Hallucination checks - ensure removed data does NOT exist
        ceo_elance = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "label": {"$regex": "ceo.*elance", "$options": "i"}}
        )
        check("No 'CEO at Elance Learning' hallucination", ceo_elance is None)

        rabsina = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "label": {"$regex": "rabsina", "$options": "i"}}
        )
        check("No 'Rabsina' misrecognition node", rabsina is None)

        audacious = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "label": "audacious"}
        )
        check("No 'audacious' hallucinated trait", audacious is None)

        judgmental = await db.graph_nodes.find_one(
            {"user_id": USER_ID, "label": "judgmental"}
        )
        check("No 'judgmental' hallucinated trait", judgmental is None)

        # Check no co_occurs_with edges
        co_occurs = await db.graph_edges.count_documents({
            "user_id": USER_ID, "relationship_type": "co_occurs_with"
        })
        check("No co_occurs_with edges", co_occurs == 0)

        logger.info("=" * 60)
        logger.info(f"VERIFICATION: {checks_passed}/{checks_total} checks passed")
        if checks_passed == checks_total:
            logger.info("ALL CHECKS PASSED — DEPLOYMENT SUCCESSFUL!")
        else:
            logger.warning(f"{checks_total - checks_passed} CHECKS FAILED — REVIEW NEEDED")

        logger.info(f"\nBackup files (for rollback if needed):")
        logger.info(f"  Nodes: {backup_nodes_path}")
        logger.info(f"  Edges: {backup_edges_path}")

    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply verified graph for _bLikker")
    parser.add_argument("--live", action="store_true", help="Apply to production (default: dry-run)")
    parser.add_argument("--rollback", action="store_true", help="Rollback to backup")
    parser.add_argument("--backup-file", type=str, help="Base path for backup files (without _nodes/_edges suffix)")
    args = parser.parse_args()

    if args.rollback:
        if not args.backup_file:
            logger.error("--backup-file required for rollback")
            sys.exit(1)
        nodes_file = args.backup_file.replace(".json", "") + "_nodes.json"
        edges_file = args.backup_file.replace(".json", "") + "_edges.json"
        if not os.path.exists(nodes_file):
            import glob
            backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "nodes_backup_*.json")))
            if backups:
                nodes_file = backups[-1]
                edges_file = nodes_file.replace("nodes_backup_", "edges_backup_")
                logger.info(f"Using latest backup: {nodes_file}")
            else:
                logger.error("No backup files found")
                sys.exit(1)
        asyncio.run(rollback(nodes_file, edges_file))
    elif args.live:
        logger.warning("LIVE MODE — applying to production database!")
        asyncio.run(main(dry_run=False))
    else:
        logger.info("DRY RUN MODE — no changes will be made")
        asyncio.run(main(dry_run=True))
