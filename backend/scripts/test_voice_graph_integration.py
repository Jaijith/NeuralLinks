"""
Comprehensive test: Voice system × Knowledge Graph integration

Tests:
1. GraphRAG loads and produces identity narratives for voice_conversation action
2. Voice prompt generator injects graph narrative into the prompt
3. Voice memory service reads interests from graph_nodes
4. Memory format includes graph-sourced data
5. End-to-end: full prompt quality evaluation for real users
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import boto3
from motor.motor_asyncio import AsyncIOMotorClient

# ── AWS Secrets ──────────────────────────────────────────────
def get_secret(name):
    client = boto3.client("secretsmanager", region_name="us-west-1")
    return client.get_secret_value(SecretId=name)["SecretString"]

MONGODB_URI = get_secret("2n1/mongodb/uri")

# ── Test users ───────────────────────────────────────────────
TEST_USERS = {
    "digitalhunter": {
        "name": "Jaijith",
        "user_id": None,  # resolved at runtime
    },
    "_blikker": {
        "name": "Sreejith",
        "user_id": None,
    },
}

# ── Counters ─────────────────────────────────────────────────
passed = 0
failed = 0
warnings = 0


def ok(label):
    global passed
    passed += 1
    print(f"  [PASS] {label}")


def fail(label, detail=""):
    global failed
    failed += 1
    print(f"  [FAIL] {label}")
    if detail:
        print(f"         {detail[:200]}")


def warn(label, detail=""):
    global warnings
    warnings += 1
    print(f"  [WARN] {label}")
    if detail:
        print(f"         {detail[:200]}")


async def main():
    global passed, failed, warnings

    client = AsyncIOMotorClient(MONGODB_URI)
    db_name = "neurallinks_local"
    # Extract db name from URI if present (mongodb+srv://.../<dbname>?...)
    if "/" in MONGODB_URI.split("?")[0].split("//")[-1]:
        parts = MONGODB_URI.split("?")[0].split("/")
        if parts[-1]:
            db_name = parts[-1]
    db = client[db_name]
    print(f"Connected to: {db.name}\n")

    # Resolve user IDs
    for avatar_name, info in TEST_USERS.items():
        user = await db.users.find_one(
            {"avatar_name": {"$regex": f"^{avatar_name}$", "$options": "i"}},
            {"id": 1, "name": 1, "avatar_name": 1},
        )
        if user:
            info["user_id"] = user["id"]
            print(f"Resolved {avatar_name} -> user_id={user['id']}, name={user.get('name', '?')}")
        else:
            print(f"WARNING: Could not find user with avatar_name={avatar_name}")

    print()

    # ==================================================================
    # TEST 1: GraphRAG identity narrative for voice_conversation
    # ==================================================================
    print("=" * 60)
    print("TEST 1: GraphRAG identity narrative (voice_conversation)")
    print("=" * 60)

    from domain.graph.rag import GraphRAG
    graph_rag = GraphRAG(db)

    for avatar_name, info in TEST_USERS.items():
        uid = info["user_id"]
        if not uid:
            fail(f"{avatar_name}: no user_id")
            continue

        print(f"\n  --- {avatar_name} ({info['name']}) ---")

        t0 = time.time()
        narrative = await graph_rag.get_identity_context(
            uid, action_type="voice_conversation", max_tokens=1200,
        )
        elapsed = time.time() - t0

        if narrative and len(narrative) > 50:
            ok(f"Narrative generated ({len(narrative)} chars, {elapsed:.2f}s)")
        else:
            fail(f"Narrative too short or empty ({len(narrative) if narrative else 0} chars)")

        if elapsed < 2.0:
            ok(f"Fast enough for voice session start ({elapsed:.2f}s < 2s)")
        else:
            warn(f"Slow for voice session ({elapsed:.2f}s) — may cause timeout")

        # Check narrative quality
        if narrative:
            has_identity = "Identity" in narrative or "identity" in narrative.lower() or "**" in narrative
            has_interests = "interest" in narrative.lower() or "passion" in narrative.lower()
            has_connections = "people" in narrative.lower() or "connection" in narrative.lower() or "family" in narrative.lower()

            if has_identity:
                ok("Contains identity section")
            else:
                warn("No clear identity section marker")

            if has_interests:
                ok("Contains interests/passions")
            else:
                warn("No interests mentioned in narrative")

            if has_connections:
                ok("Contains people/connections")
            else:
                warn("No connections/people mentioned")

            print(f"\n  Preview (first 500 chars):")
            print(f"  {narrative[:500]}...")

    # ==================================================================
    # TEST 2: Graph node count and edge coverage
    # ==================================================================
    print("\n" + "=" * 60)
    print("TEST 2: Graph data availability per user")
    print("=" * 60)

    for avatar_name, info in TEST_USERS.items():
        uid = info["user_id"]
        if not uid:
            continue

        print(f"\n  --- {avatar_name} ---")

        node_count = await db.graph_nodes.count_documents({"user_id": uid})
        edge_count = await db.graph_edges.count_documents({
            "$or": [
                {"from_node_id": {"$regex": uid}},
                {"to_node_id": {"$regex": uid}},
            ]
        })

        # Count by type
        pipeline = [
            {"$match": {"user_id": uid}},
            {"$group": {"_id": "$node_type", "count": {"$sum": 1}}},
        ]
        type_counts = {doc["_id"]: doc["count"] async for doc in db.graph_nodes.aggregate(pipeline)}

        print(f"  Nodes: {node_count}, Edges: {edge_count}")
        print(f"  By type: {json.dumps(type_counts, indent=4)}")

        if node_count >= 10:
            ok(f"Sufficient nodes ({node_count} >= 10)")
        else:
            fail(f"Too few nodes ({node_count} < 10)")

        if edge_count >= 5:
            ok(f"Has edge connections ({edge_count} >= 5)")
        else:
            warn(f"Few edges ({edge_count}) — graph traversal may be limited")

        if type_counts.get("interest", 0) >= 3:
            ok(f"Has interests ({type_counts.get('interest', 0)})")
        else:
            warn(f"Few interests ({type_counts.get('interest', 0)})")

        if type_counts.get("connection", 0) >= 1:
            ok(f"Has connections ({type_counts.get('connection', 0)})")
        else:
            warn(f"No connection nodes — people won't appear in narrative")

    # ==================================================================
    # TEST 3: Voice prompt generator — full prompt with graph narrative
    # ==================================================================
    print("\n" + "=" * 60)
    print("TEST 3: Voice prompt generator (full prompt with graph)")
    print("=" * 60)

    from domain.voice.prompt_generator import VoicePromptGenerator
    prompt_gen = VoicePromptGenerator(db)

    for avatar_name, info in TEST_USERS.items():
        uid = info["user_id"]
        if not uid:
            continue

        print(f"\n  --- {avatar_name} ({info['name']}) ---")

        t0 = time.time()
        prompt = await prompt_gen.generate_prompt(
            user_id=uid,
            avatar_id=uid,
            include_social_context=True,
        )
        elapsed = time.time() - t0

        if prompt and len(prompt) > 200:
            ok(f"Prompt generated ({len(prompt)} chars, {elapsed:.2f}s)")
        else:
            fail(f"Prompt too short ({len(prompt) if prompt else 0} chars)")

        if elapsed < 5.0:
            ok(f"Within voice timeout ({elapsed:.2f}s < 5s)")
        else:
            fail(f"Exceeds voice timeout ({elapsed:.2f}s >= 5s)")

        # Check that graph identity narrative is present
        if "Identity (from knowledge graph)" in prompt:
            ok("Graph identity narrative injected into prompt")
        elif "Identity" in prompt and "knowledge graph" in prompt.lower():
            ok("Graph identity narrative present (variant format)")
        else:
            # Check if it might be already in personality_text
            if "Who " in prompt and "Really Is" in prompt:
                warn("Identity may be in personality section, not separate graph section")
            else:
                fail("Graph identity narrative NOT found in prompt")

        # Check user name is used
        real_name = info["name"]
        if real_name.lower() in prompt.lower():
            ok(f"User's real name '{real_name}' used in prompt")
        else:
            fail(f"User's real name '{real_name}' NOT found in prompt")

        # Check for key sections
        sections_to_check = [
            ("Who You Are", "Avatar identity section"),
            ("How You Sound", "Voice style section"),
            ("What Matters", "Behavioral guidance"),
            ("Emotional Authenticity", "Emotion enforcement"),
        ]
        for marker, label in sections_to_check:
            if marker in prompt:
                ok(f"Has '{label}'")
            else:
                warn(f"Missing '{label}'")

        # Print prompt sections relevant to graph
        graph_start = prompt.find("Identity (from knowledge graph)")
        if graph_start >= 0:
            graph_section = prompt[graph_start:graph_start + 600]
            print(f"\n  Graph section preview:")
            for line in graph_section.split("\n")[:10]:
                print(f"    {line}")

    # ==================================================================
    # TEST 4: Voice memory service — graph interests integration
    # ==================================================================
    print("\n" + "=" * 60)
    print("TEST 4: Voice memory service — graph interests in memory")
    print("=" * 60)

    from domain.voice.voice_memory import VoiceMemoryService
    memory_service = VoiceMemoryService(db)

    for avatar_name, info in TEST_USERS.items():
        uid = info["user_id"]
        if not uid:
            continue

        print(f"\n  --- {avatar_name} ---")

        memory = await memory_service.get_user_memory(uid, uid)

        interests = memory.get("interests", [])
        connections = memory.get("connections", [])
        facts = memory.get("facts", [])
        recent_posts = memory.get("recent_posts", [])
        conversations = memory.get("recent_conversations", [])

        print(f"  Interests: {len(interests)}, Connections: {len(connections)}, "
              f"Facts: {len(facts)}, Posts: {len(recent_posts)}, Conversations: {len(conversations)}")

        if interests:
            graph_sourced = [i for i in interests if i.get("source") == "graph"]
            voice_sourced = [i for i in interests if i.get("source") == "voice"]
            ok(f"Interests loaded (graph: {len(graph_sourced)}, voice: {len(voice_sourced)})")

            # Show top interests
            top = interests[:5]
            for i in top:
                print(f"    - {i.get('label', i.get('topic', '?'))} "
                      f"(strength={i.get('strength', '?')}, source={i.get('source', '?')})")
        else:
            warn("No interests loaded")

        # Test format_memory_for_prompt
        formatted = memory_service.format_memory_for_prompt(memory, info["name"])
        if formatted and len(formatted) > 50:
            ok(f"Memory formatted for prompt ({len(formatted)} chars)")
        else:
            warn(f"Memory format empty or short ({len(formatted) if formatted else 0} chars)")

        if formatted:
            has_people = "People in" in formatted or "life" in formatted
            has_interests_section = "interests" in formatted.lower()
            if has_people:
                ok("Formatted memory includes people section")
            if has_interests_section:
                ok("Formatted memory includes interests section")

    # ==================================================================
    # TEST 5: Seed selection for voice_conversation vs general
    # ==================================================================
    print("\n" + "=" * 60)
    print("TEST 5: Seed selection — voice_conversation vs general")
    print("=" * 60)

    for avatar_name, info in TEST_USERS.items():
        uid = info["user_id"]
        if not uid:
            continue

        print(f"\n  --- {avatar_name} ---")

        graph = await graph_rag._load_graph(uid)

        # voice_conversation falls into "general" in _select_seeds
        seeds_voice = GraphRAG._select_seeds(graph, action_type="voice_conversation")
        seeds_post = GraphRAG._select_seeds(graph, action_type="post_generation")
        seeds_chat = GraphRAG._select_seeds(graph, action_type="chat_response")

        print(f"  Seeds - voice: {len(seeds_voice)}, post: {len(seeds_post)}, chat: {len(seeds_chat)}")

        if len(seeds_voice) >= 5:
            ok(f"Voice seeds sufficient ({len(seeds_voice)} >= 5)")
        else:
            warn(f"Few voice seeds ({len(seeds_voice)})")

        # Check type diversity in voice seeds
        seed_types = set()
        for nid in seeds_voice:
            node = graph.nodes.get(nid)
            if node:
                seed_types.add(node.get("node_type", "unknown"))
        print(f"  Voice seed types: {seed_types}")

        if len(seed_types) >= 2:
            ok(f"Diverse seed types ({len(seed_types)} types)")
        else:
            warn(f"Low type diversity ({seed_types})")

    # ==================================================================
    # TEST 6: Spreading activation produces connected subgraph
    # ==================================================================
    print("\n" + "=" * 60)
    print("TEST 6: Spreading activation connectivity")
    print("=" * 60)

    for avatar_name, info in TEST_USERS.items():
        uid = info["user_id"]
        if not uid:
            continue

        print(f"\n  --- {avatar_name} ---")

        graph = await graph_rag._load_graph(uid)
        seeds = GraphRAG._select_seeds(graph, action_type="voice_conversation")

        if not seeds:
            warn("No seeds, skipping activation test")
            continue

        activations = GraphRAG._spreading_activation(
            graph, seeds, decay=0.5, threshold=0.05, max_steps=3,
        )

        activated_count = len(activations)
        seed_count = len(seeds)
        spread_count = activated_count - seed_count

        print(f"  Seeds: {seed_count}, Activated: {activated_count}, Spread: {spread_count}")

        if spread_count > 0:
            ok(f"Activation spread to {spread_count} additional nodes")
        else:
            warn("No spreading — edges may be missing or weights too low")

        # Check activation distribution
        high_act = [nid for nid, a in activations.items() if a >= 0.5]
        med_act = [nid for nid, a in activations.items() if 0.2 <= a < 0.5]
        low_act = [nid for nid, a in activations.items() if a < 0.2]
        print(f"  Distribution: high={len(high_act)}, medium={len(med_act)}, low={len(low_act)}")

    # ==================================================================
    # TEST 7: Narrative quality comparison — voice vs general
    # ==================================================================
    print("\n" + "=" * 60)
    print("TEST 7: Narrative quality — voice vs post vs personality")
    print("=" * 60)

    for avatar_name, info in TEST_USERS.items():
        uid = info["user_id"]
        if not uid:
            continue

        print(f"\n  --- {avatar_name} ---")

        narrative_voice = await graph_rag.get_identity_context(
            uid, action_type="voice_conversation", max_tokens=1200,
        )
        narrative_post = await graph_rag.get_identity_context(
            uid, action_type="post_generation", max_tokens=1200,
        )
        narrative_profile = await graph_rag.get_identity_context(
            uid, action_type="personality_profile", max_tokens=1200,
        )

        print(f"  Lengths — voice: {len(narrative_voice)}, "
              f"post: {len(narrative_post)}, profile: {len(narrative_profile)}")

        if narrative_voice:
            ok(f"Voice narrative: {len(narrative_voice)} chars")
        else:
            fail("Voice narrative empty")

        # Profile should be the richest (widest activation)
        if narrative_profile and len(narrative_profile) >= len(narrative_voice) * 0.8:
            ok("Profile narrative is comprehensive (as expected)")
        else:
            warn("Profile narrative smaller than voice — check personality_profile activation")

    # ==================================================================
    # SUMMARY
    # ==================================================================
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {warnings} warnings")
    print("=" * 60)

    if failed == 0:
        print("\nAll tests passed! Voice system is fully leveraging the knowledge graph.")
    else:
        print(f"\n{failed} test(s) need attention.")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
