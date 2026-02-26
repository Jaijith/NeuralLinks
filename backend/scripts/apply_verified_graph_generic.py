#!/usr/bin/env python3
"""
Apply a manually verified graph to the production database for ANY user.

Usage:
  python apply_verified_graph_generic.py <user_id> <graph_dir> [--live]
  python apply_verified_graph_generic.py <user_id> <graph_dir> --rollback
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("apply_graph")

DB_NAME = "neurallinks_local"
SECRETS_REGION = "us-west-2"


def get_secret(secret_name):
    import boto3
    raw = boto3.client("secretsmanager", region_name=SECRETS_REGION).get_secret_value(SecretId=secret_name)["SecretString"]
    try:
        p = json.loads(raw)
        return p.get("uri") or p.get("MONGO_URL") or raw if isinstance(p, dict) else p
    except json.JSONDecodeError:
        return raw


async def main(user_id, graph_dir, dry_run):
    from motor.motor_asyncio import AsyncIOMotorClient

    graph_file = os.path.join(graph_dir, "verified_graph.json")
    backup_dir = graph_dir.replace("verified_graph_", "backups_")

    if not os.path.exists(graph_file):
        logger.error(f"Graph file not found: {graph_file}")
        return

    with open(graph_file) as f:
        graph = json.load(f)

    new_nodes = graph["nodes"]
    new_edges = graph["edges"]
    logger.info(f"Loaded verified graph: {len(new_nodes)} nodes, {len(new_edges)} edges")

    client = AsyncIOMotorClient(
        get_secret("2n1/mongodb/uri"),
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=60000,
        tls=True,
        tlsAllowInvalidCertificates=False,
    )
    db = client[DB_NAME]

    try:
        host_info = await client.admin.command("ismaster")
        hosts = host_info.get("hosts", [host_info.get("me", "unknown")])
        logger.info(f"Connected to MongoDB: {hosts}")

        # Get user info
        user = await db.users.find_one({"id": user_id}, {"name": 1, "avatar_name": 1, "_id": 0})
        user_name = user.get("name", "?") if user else "?"
        avatar_name = user.get("avatar_name", "?") if user else "?"
        logger.info(f"User: {user_name} (avatar: {avatar_name})")

        # Phase 1: Backup
        logger.info("=" * 60)
        logger.info("PHASE 1: Backing up current data")
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        old_nodes = await db.graph_nodes.find({"user_id": user_id}, {"_id": 0}).to_list(10000)
        backup_nodes_path = os.path.join(backup_dir, f"nodes_backup_{ts}.json")
        with open(backup_nodes_path, "w") as f:
            json.dump(old_nodes, f, indent=2, default=str)
        logger.info(f"  Backed up {len(old_nodes)} nodes")

        old_node_ids = [n["id"] for n in old_nodes if n.get("id")]
        old_edges = await db.graph_edges.find(
            {"$or": [{"user_id": user_id}, {"from_node_id": {"$in": old_node_ids}}, {"to_node_id": {"$in": old_node_ids}}]},
            {"_id": 0}
        ).to_list(10000)
        backup_edges_path = os.path.join(backup_dir, f"edges_backup_{ts}.json")
        with open(backup_edges_path, "w") as f:
            json.dump(old_edges, f, indent=2, default=str)
        logger.info(f"  Backed up {len(old_edges)} edges")

        if dry_run:
            logger.info("DRY RUN — would make the following changes:")
            logger.info(f"  Delete: {len(old_nodes)} nodes, {len(old_edges)} edges")
            logger.info(f"  Insert: {len(new_nodes)} nodes, {len(new_edges)} edges")
            logger.info("Run with --live to apply.")
            client.close()
            return

        # Phase 2: Delete old graph
        logger.info("=" * 60)
        logger.info("PHASE 2: Removing old graph data")
        del_nodes = await db.graph_nodes.delete_many({"user_id": user_id})
        logger.info(f"  Deleted {del_nodes.deleted_count} nodes")
        del_edges = await db.graph_edges.delete_many(
            {"$or": [{"user_id": user_id}, {"from_node_id": {"$in": old_node_ids}}, {"to_node_id": {"$in": old_node_ids}}]}
        )
        logger.info(f"  Deleted {del_edges.deleted_count} edges")

        # Phase 3: Insert verified graph
        logger.info("=" * 60)
        logger.info("PHASE 3: Inserting verified graph")
        if new_nodes:
            await db.graph_nodes.insert_many(new_nodes)
            logger.info(f"  Inserted {len(new_nodes)} nodes")
        if new_edges:
            await db.graph_edges.insert_many(new_edges)
            logger.info(f"  Inserted {len(new_edges)} edges")

        # Phase 4: Invalidate caches
        logger.info("=" * 60)
        logger.info("PHASE 4: Invalidating caches")
        del_cache = await db.avatar_personality_prompts.delete_many({"user_id": user_id})
        logger.info(f"  Deleted {del_cache.deleted_count} cached personality prompts")

        # Phase 5: Verification
        logger.info("=" * 60)
        logger.info("PHASE 5: Post-deployment verification")
        live_nodes = await db.graph_nodes.count_documents({"user_id": user_id})
        new_node_ids = [n["id"] for n in new_nodes]
        live_edges = await db.graph_edges.count_documents(
            {"$or": [{"user_id": user_id}, {"from_node_id": {"$in": new_node_ids}}, {"to_node_id": {"$in": new_node_ids}}]}
        )
        logger.info(f"  Live nodes: {live_nodes} (expected {len(new_nodes)})")
        logger.info(f"  Live edges: {live_edges} (expected {len(new_edges)})")

        checks = 0
        passed = 0

        def check(name, condition):
            nonlocal checks, passed
            checks += 1
            if condition:
                passed += 1
                logger.info(f"  [PASS] {name}")
            else:
                logger.error(f"  [FAIL] {name}")

        check("Node count matches", live_nodes == len(new_nodes))
        check("Edge count matches", live_edges == len(new_edges))

        # Check no co_occurs_with edges
        co_occurs = await db.graph_edges.count_documents({"user_id": user_id, "relationship_type": "co_occurs_with"})
        check("No co_occurs_with edges", co_occurs == 0)

        # Check sources are not all "verified_manual_review"
        sample = await db.graph_nodes.find_one({"user_id": user_id, "properties.source": {"$ne": "verified_manual_review"}})
        check("Sources are properly attributed (not all verified_manual_review)", sample is not None)

        # Spot check a few nodes by type
        for ntype in ["connection", "interest", "trait", "value", "demographic"]:
            count = await db.graph_nodes.count_documents({"user_id": user_id, "node_type": ntype})
            check(f"Has {ntype} nodes ({count})", count > 0)

        logger.info("=" * 60)
        logger.info(f"VERIFICATION: {passed}/{checks} checks passed")
        if passed == checks:
            logger.info(f"ALL CHECKS PASSED — DEPLOYMENT SUCCESSFUL for {user_name}!")
        else:
            logger.warning(f"{checks - passed} CHECKS FAILED — REVIEW NEEDED")

        logger.info(f"\nBackup files: {backup_nodes_path}")

    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply verified graph for any user")
    parser.add_argument("user_id", help="User ID")
    parser.add_argument("graph_dir", help="Directory containing verified_graph.json")
    parser.add_argument("--live", action="store_true", help="Apply to production")
    args = parser.parse_args()

    if args.live:
        logger.warning(f"LIVE MODE — applying to production for user {args.user_id}!")
    else:
        logger.info("DRY RUN MODE")

    asyncio.run(main(args.user_id, args.graph_dir, dry_run=not args.live))
