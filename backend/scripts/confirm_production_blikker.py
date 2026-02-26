#!/usr/bin/env python3
"""Confirm the verified graph for _bLikker is live on PRODUCTION MongoDB."""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

USER_ID = "fb1a5d18-5c93-4084-8da1-2227b1bea266"


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

    client = AsyncIOMotorClient(get_secret("2n1/mongodb/uri"))
    db = client["neurallinks_local"]

    host_info = await client.admin.command("ismaster")
    print(f"Connected to: {host_info.get('hosts', [host_info.get('me', '?')])}")

    nodes = await db.graph_nodes.count_documents({"user_id": USER_ID})
    node_ids = [n["id"] async for n in db.graph_nodes.find({"user_id": USER_ID}, {"id": 1, "_id": 0})]
    edges = await db.graph_edges.count_documents(
        {"$or": [{"user_id": USER_ID}, {"from_node_id": {"$in": node_ids}}, {"to_node_id": {"$in": node_ids}}]}
    )
    print(f"\nNodes: {nodes}  |  Edges: {edges}")

    checks = []

    async def check(name, query, expected=True):
        result = await db.graph_nodes.find_one({"user_id": USER_ID, **query})
        passed = (result is not None) == expected
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        checks.append(passed)
        return result

    print("\n--- Spot Checks (should exist) ---")
    r = await check("Rafseena Sedeed (connection)", {"node_type": "connection", "label": "rafseena sedeed"})
    if r:
        rt = r.get("properties", {}).get("relationship_type", "?")
        rel = r.get("properties", {}).get("relationship", "?")
        print(f"         -> relationship: {rel}, type: {rt}")
        passed_col = rt == "colleague_of"
        print(f"  [{'PASS' if passed_col else 'FAIL'}] Rafseena relationship = colleague_of")
        checks.append(passed_col)

    await check("Abdul Jaleel (connection)", {"node_type": "connection", "label": "abdul jaleel"})
    n = await check("Narmada (mother)", {"node_type": "connection", "label": "narmada"})
    if n:
        rt = n.get("properties", {}).get("relationship_type", "?")
        print(f"         -> relationship_type: {rt}")

    t = await check("Taran (son)", {"node_type": "connection", "label": "taran"})
    if t:
        rt = t.get("properties", {}).get("relationship_type", "?")
        print(f"         -> relationship_type: {rt}")

    await check("Jishnu (connection)", {"node_type": "connection", "label": "jishnu"})
    await check("Kozhikode location", {"node_type": "demographic", "label": {"$regex": "kozhikode", "$options": "i"}})
    await check("Architect job", {"node_type": "demographic", "label": {"$regex": "architect", "$options": "i"}})
    await check("Architecture interest", {"node_type": "interest", "label": "architecture"})
    await check("Heritage-Inspired Design", {"node_type": "interest", "label": "heritage-inspired design"})
    await check("Nadumuttams", {"node_type": "interest", "label": "nadumuttams"})
    await check("Architectural Rendering", {"node_type": "interest", "label": "architectural rendering"})
    await check("Norse Mythology", {"node_type": "interest", "label": "norse mythology"})
    await check("Quantum Physics", {"node_type": "interest", "label": "quantum physics"})
    await check("Badminton", {"node_type": "interest", "label": "badminton"})
    await check("FIFA", {"node_type": "interest", "label": "fifa"})
    await check("Goa Road Trips", {"node_type": "interest", "label": "goa road trips"})
    await check("Vili & Vé Studio", {"node_type": "experience", "label": {"$regex": "vili", "$options": "i"}})
    await check("Elance HQ", {"node_type": "experience", "label": {"$regex": "elance", "$options": "i"}})
    await check("HiLite Office", {"node_type": "experience", "label": {"$regex": "hilite", "$options": "i"}})
    await check("Coimbatore Apt", {"node_type": "experience", "label": {"$regex": "coimbatore", "$options": "i"}})
    await check("Tropical House", {"node_type": "experience", "label": {"$regex": "tropical", "$options": "i"}})
    await check("Hardworking trait", {"node_type": "trait", "label": "hardworking"})
    await check("Creative trait", {"node_type": "trait", "label": "creative"})
    await check("Culturally Rooted trait", {"node_type": "trait", "label": "culturally rooted"})
    await check("Heritage & Tradition value", {"node_type": "value", "label": "heritage and tradition"})
    await check("Malayalam language", {"node_type": "demographic", "label": {"$regex": "malayalam", "$options": "i"}})

    print("\n--- Hallucination Checks (should NOT exist) ---")
    await check("No 'CEO at Elance' hallucination", {"label": {"$regex": "ceo.*elance", "$options": "i"}}, expected=False)
    await check("No 'Rabsina' misrecognition", {"label": {"$regex": "rabsina", "$options": "i"}}, expected=False)
    await check("No 'audacious' trait", {"label": "audacious"}, expected=False)
    await check("No 'judgmental' trait", {"label": "judgmental"}, expected=False)
    await check("No 'tired' trait", {"label": "tired"}, expected=False)
    await check("No 'busy' trait", {"label": "busy"}, expected=False)
    await check("No 'romance' interest", {"label": "romance"}, expected=False)
    await check("No 'fashion' interest", {"label": "fashion"}, expected=False)
    await check("No 'the house is the' preference", {"label": {"$regex": "^the house is the", "$options": "i"}}, expected=False)
    await check("No old 'mom' label (should be narmada)", {"node_type": "connection", "label": "mom"}, expected=False)

    # Check users.connections
    user = await db.users.find_one({"id": USER_ID}, {"connections": 1})
    if user and user.get("connections"):
        print("\n--- Users.connections ---")
        for c in user["connections"]:
            print(f"  {c.get('name')}: {c.get('relationship')}")
        has_rabsina = any(c.get("name", "").lower() == "rabsina" for c in user["connections"])
        has_rafseena = any("rafseena" in c.get("name", "").lower() for c in user["connections"])
        print(f"  [{'PASS' if not has_rabsina else 'FAIL'}] No 'Rabsina' in connections")
        print(f"  [{'PASS' if has_rafseena else 'FAIL'}] 'Rafseena Sedeed' in connections")
        checks.append(not has_rabsina)
        checks.append(has_rafseena)

    passed = sum(checks)
    total = len(checks)
    print(f"\n{'='*60}")
    print(f"  RESULT: {passed}/{total} checks passed")
    if passed == total:
        print(f"  VERIFIED GRAPH IS LIVE AND CORRECT ON PRODUCTION!")
    else:
        print(f"  {total - passed} ISSUES FOUND — REVIEW NEEDED")
    print(f"{'='*60}")

    client.close()

asyncio.run(main())
