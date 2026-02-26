#!/usr/bin/env python3
"""Confirm the verified graph is live on the PRODUCTION MongoDB."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

USER_ID = "dedc30ef-dca9-467d-84b1-5e643941e6fd"

def get_secret(name):
    import boto3
    raw = boto3.client("secretsmanager", region_name="us-west-2").get_secret_value(SecretId=name)["SecretString"]
    try:
        p = json.loads(raw)
        return p.get("uri") or p.get("MONGO_URL") or raw if isinstance(p, dict) else p
    except json.JSONDecodeError:
        return raw

async def main():
    from motor.motor_asyncio import AsyncIOMotorClient
    uri = get_secret("2n1/mongodb/uri")

    at_idx = uri.find("@")
    host_part = uri[at_idx+1:] if at_idx > 0 else uri
    print(f"MongoDB host: {host_part[:80]}...")

    client = AsyncIOMotorClient(uri)
    db = client["neurallinks_local"]

    node_count = await db.graph_nodes.count_documents({"user_id": USER_ID})
    nids = [n["id"] for n in await db.graph_nodes.find({"user_id": USER_ID}, {"id": 1, "_id": 0}).to_list(10000)]
    edge_count = await db.graph_edges.count_documents({"$or": [{"user_id": USER_ID}, {"from_node_id": {"$in": nids}}]})

    subhadra = await db.graph_nodes.find_one(
        {"user_id": USER_ID, "node_type": "connection", "label": "subhadra"},
        {"_id": 0, "display_label": 1, "strength": 1, "properties.relationship_type": 1}
    )
    sreejith = await db.graph_nodes.find_one(
        {"user_id": USER_ID, "node_type": "connection", "label": "sreejith"},
        {"_id": 0, "display_label": 1, "strength": 1, "properties.relationship_type": 1}
    )
    kerala = await db.graph_nodes.find_one(
        {"user_id": USER_ID, "node_type": "demographic", "label": {"$regex": "thiruvananthapuram"}},
        {"_id": 0, "display_label": 1, "strength": 1}
    )
    linkin = await db.graph_nodes.find_one(
        {"user_id": USER_ID, "label": "linkin park"},
        {"_id": 0, "display_label": 1, "strength": 1}
    )
    chess = await db.graph_nodes.find_one(
        {"user_id": USER_ID, "label": "chess"},
        {"_id": 0, "display_label": 1, "strength": 1}
    )
    job = await db.graph_nodes.find_one(
        {"user_id": USER_ID, "node_type": "demographic", "label": {"$regex": "job:software"}},
        {"_id": 0, "display_label": 1, "strength": 1}
    )

    print(f"\n{'='*60}")
    print(f"  PRODUCTION DATABASE CONFIRMATION")
    print(f"{'='*60}")
    print(f"  Database: neurallinks_local (PRODUCTION)")
    print(f"  Nodes for DigitalHunter: {node_count}")
    print(f"  Edges for DigitalHunter: {edge_count}")
    print(f"\n  Spot checks:")
    print(f"    Subhadra:    {subhadra}")
    print(f"    Sreejith:    {sreejith}")
    print(f"    Origin:      {kerala}")
    print(f"    Linkin Park: {linkin}")
    print(f"    Chess:       {chess}")
    print(f"    Job:         {job}")

    google = await db.graph_nodes.find_one({"user_id": USER_ID, "label": {"$regex": "works at google", "$options": "i"}})
    seattle = await db.graph_nodes.find_one({"user_id": USER_ID, "label": {"$regex": "moved to seattle", "$options": "i"}})
    vasubhadra = await db.graph_nodes.find_one({"user_id": USER_ID, "label": {"$regex": "vasubhadra", "$options": "i"}})

    print(f"\n  Hallucination check:")
    print(f"    'works at google':  {'FOUND!' if google else 'GONE'}")
    print(f"    'moved to seattle': {'FOUND!' if seattle else 'GONE'}")
    print(f"    'vasubhadra':       {'FOUND!' if vasubhadra else 'GONE'}")

    if node_count == 88 and edge_count == 139 and not google and not seattle and not vasubhadra:
        print(f"\n  CONFIRMED: Verified graph is LIVE in PRODUCTION.")
    else:
        print(f"\n  WARNING: Counts or checks do not match expected values!")

    client.close()

asyncio.run(main())
