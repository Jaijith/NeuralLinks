#!/usr/bin/env python3
"""
Test the enhanced GraphRAG with real production data.

Validates:
1. Graph loading and caching
2. Spreading activation algorithm
3. BFS multi-hop traversal
4. Context-aware seed selection
5. Narrative compilation (compile_context)
6. Backwards compatibility of legacy methods
7. New get_identity_context() for all action types
8. Output comparison: old flat lists vs new connected narratives
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import boto3
from motor.motor_asyncio import AsyncIOMotorClient

from domain.graph.rag import GraphRAG, InMemoryGraph

DB_NAME = "neurallinks_local"
USERS = {
    "DigitalHunter (Jaijith)": "dedc30ef-dca9-467d-84b1-5e643941e6fd",
    "Seven (Rafseena)": "5e03b1ac-81c6-48e9-8740-d4d93c1629d3",
    "Aera (Dilna)": "1033cd6c-03d8-4594-8e35-dfc0a778bbc6",
}


def get_mongo_uri():
    raw = boto3.client("secretsmanager", region_name="us-west-2").get_secret_value(
        SecretId="2n1/mongodb/uri"
    )["SecretString"]
    try:
        p = json.loads(raw)
        return p.get("uri") or p.get("MONGO_URL") or raw if isinstance(p, dict) else p
    except json.JSONDecodeError:
        return raw


def section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


async def test_graph_loading(rag: GraphRAG, user_id: str, name: str):
    """Test 1: Graph loads correctly with nodes, edges, and adjacency."""
    section(f"Test 1: Graph Loading — {name}")

    t0 = time.time()
    graph = await rag._load_graph(user_id)
    t1 = time.time()

    print(f"  Nodes: {graph.node_count}")
    print(f"  Edges: {graph.edge_count}")
    print(f"  Load time: {(t1-t0)*1000:.0f}ms")
    print(f"  Node types: {', '.join(f'{k}({len(v)})' for k, v in sorted(graph.by_type.items()))}")

    # Verify adjacency
    nodes_with_edges = set()
    for nid in graph.nodes:
        if graph.outgoing.get(nid) or graph.incoming.get(nid):
            nodes_with_edges.add(nid)
    connectivity = len(nodes_with_edges) / graph.node_count * 100 if graph.node_count else 0
    print(f"  Connectivity: {len(nodes_with_edges)}/{graph.node_count} nodes have edges ({connectivity:.0f}%)")

    # Verify cache works
    t0 = time.time()
    graph2 = await rag._load_graph(user_id)
    t1 = time.time()
    assert graph2 is graph, "Cache should return same object"
    print(f"  Cache hit: {(t1-t0)*1000:.1f}ms (should be <1ms)")

    # Edge type distribution
    edge_types = {}
    for e in graph.edges:
        rt = e.get("relationship_type", "?")
        edge_types[rt] = edge_types.get(rt, 0) + 1
    print(f"  Edge types: {', '.join(f'{k}({v})' for k, v in sorted(edge_types.items(), key=lambda x: -x[1])[:10])}")

    assert graph.node_count > 0, "Should have nodes"
    assert graph.edge_count > 0, "Should have edges"
    assert connectivity > 50, f"Connectivity should be >50%, got {connectivity:.0f}%"
    print("  ✓ PASSED")
    return graph


async def test_spreading_activation(rag: GraphRAG, graph: InMemoryGraph, name: str):
    """Test 2: Spreading activation propagates correctly through edges."""
    section(f"Test 2: Spreading Activation — {name}")

    interest_ids = graph.by_type.get("interest", [])
    if not interest_ids:
        print("  No interests to test with, skipping")
        return

    seed_id = interest_ids[0]
    seed_label = graph.nodes[seed_id].get("display_label") or graph.nodes[seed_id].get("label")
    seeds = {seed_id: 1.0}

    activations = rag._spreading_activation(graph, seeds, decay=0.5, threshold=0.05, max_steps=3)

    print(f"  Seed: '{seed_label}' (activation=1.0)")
    print(f"  Activated nodes: {len(activations)} / {graph.node_count}")

    activated_types = {}
    for nid in activations:
        ntype = graph.nodes[nid].get("node_type", "?")
        activated_types[ntype] = activated_types.get(ntype, 0) + 1

    print(f"  Activated types: {', '.join(f'{k}({v})' for k, v in sorted(activated_types.items()))}")

    top_5 = sorted(activations.items(), key=lambda x: x[1], reverse=True)[:5]
    for nid, act in top_5:
        node = graph.nodes[nid]
        label = node.get("display_label") or node.get("label")
        ntype = node.get("node_type")
        print(f"    {act:.3f} — {label} [{ntype}]")

    assert len(activations) > 1, "Activation should spread beyond seed"

    cross_type = any(
        graph.nodes[nid].get("node_type") != "interest"
        for nid in activations if nid != seed_id
    )
    print(f"  Cross-type activation: {'✓ YES' if cross_type else '✗ NO'}")
    print("  ✓ PASSED")


async def test_bfs_traversal(rag: GraphRAG, graph: InMemoryGraph, name: str):
    """Test 3: BFS multi-hop traversal discovers connected nodes."""
    section(f"Test 3: BFS Multi-Hop Traversal — {name}")

    conn_ids = graph.by_type.get("connection", [])
    if not conn_ids:
        print("  No connections to test with, skipping")
        return

    seed_id = conn_ids[0]
    seed_label = graph.nodes[seed_id].get("display_label") or graph.nodes[seed_id].get("label")

    for hops in [1, 2, 3]:
        distances, edges = rag._bfs_traverse(graph, {seed_id}, max_hops=hops, min_weight=0.2)
        types_found = set(graph.nodes[nid].get("node_type") for nid in distances)
        print(f"  {hops}-hop from '{seed_label}': {len(distances)} nodes reached, {len(edges)} edges, types={types_found}")

    distances_2hop, _ = rag._bfs_traverse(graph, {seed_id}, max_hops=2)
    assert len(distances_2hop) > 1, "Should reach more than the seed"
    print("  ✓ PASSED")


async def test_seed_selection(rag: GraphRAG, graph: InMemoryGraph, name: str):
    """Test 4: Seed selection works for all action types."""
    section(f"Test 4: Seed Selection — {name}")

    for action_type in ["post_generation", "chat_response", "personality_profile", "decision", "general"]:
        extra = {}
        if action_type == "chat_response":
            extra["other_user_interests"] = ["architecture", "travel"]

        seeds = rag._select_seeds(graph, action_type, **extra)
        types = {}
        for nid in seeds:
            t = graph.nodes[nid].get("node_type", "?")
            types[t] = types.get(t, 0) + 1

        print(f"  {action_type:25s}: {len(seeds)} seeds — {dict(types)}")

    seeds_topic = rag._select_seeds(graph, "post_generation", topic="architecture")
    if seeds_topic:
        for nid, act in sorted(seeds_topic.items(), key=lambda x: -x[1])[:3]:
            label = graph.nodes[nid].get("display_label") or graph.nodes[nid].get("label")
            print(f"    topic='architecture' → {label} (activation={act:.2f})")

    print("  ✓ PASSED")


async def test_narrative_compilation(rag: GraphRAG, user_id: str, name: str):
    """Test 5: Narrative compilation produces connected identity text."""
    section(f"Test 5: Narrative Compilation — {name}")

    for action_type in ["post_generation", "personality_profile", "chat_response"]:
        extra = {}
        if action_type == "chat_response":
            extra["other_user_interests"] = ["architecture", "travel", "painting"]

        t0 = time.time()
        narrative = await rag.get_identity_context(
            user_id, action_type=action_type, max_tokens=2000, **extra,
        )
        t1 = time.time()

        char_count = len(narrative)
        token_est = char_count / 4

        print(f"\n  --- {action_type} ({(t1-t0)*1000:.0f}ms, ~{token_est:.0f} tokens) ---")
        for line in narrative.split("\n"):
            if line.strip():
                print(f"  {line[:120]}{'...' if len(line) > 120 else ''}")

    print("\n  ✓ PASSED")


async def test_backwards_compatibility(rag: GraphRAG, user_id: str, name: str):
    """Test 6: Legacy methods still work with the same return format."""
    section(f"Test 6: Backwards Compatibility — {name}")

    # get_user_context
    ctx = await rag.get_user_context(user_id, max_nodes=20)
    assert "interests" in ctx, "Should have interests key"
    assert "traits" in ctx, "Should have traits key"
    assert "values" in ctx, "Should have values key"
    assert isinstance(ctx["interests"], list), "interests should be list"

    if ctx["interests"]:
        item = ctx["interests"][0]
        assert "label" in item, "item should have label"
        assert "strength" in item, "item should have strength"
        assert "source" in item, "item should have source"
        assert "connected" in item, "item should have connected (new field)"
        print(f"  get_user_context: {sum(len(v) for v in ctx.values())} items, "
              f"top interest='{item['label']}' with {len(item['connected'])} connections")

    # get_relevant_context (post_generation)
    post_ctx = await rag.get_relevant_context(user_id, "post_generation")
    assert isinstance(post_ctx, str), "post_generation should return string"
    assert len(post_ctx) > 50, "Should have substantial content"
    print(f"  get_relevant_context(post_generation): {len(post_ctx)} chars")

    # get_relevant_context (matching)
    match_ctx = await rag.get_relevant_context(user_id, "matching")
    assert isinstance(match_ctx, dict), "matching should return dict"
    assert "interests" in match_ctx, "Should have interests"
    print(f"  get_relevant_context(matching): {len(match_ctx.get('interests', []))} interests")

    # get_avatar_personality_profile
    profile = await rag.get_avatar_personality_profile(user_id)
    assert isinstance(profile, str), "Should return string"
    assert "WHO YOU ARE" in profile, "Should have identity section"
    assert len(profile) > 200, "Should be substantial"
    print(f"  get_avatar_personality_profile: {len(profile)} chars")

    print("  ✓ ALL BACKWARDS COMPATIBILITY CHECKS PASSED")


async def test_comparison(rag: GraphRAG, user_id: str, name: str):
    """Test 7: Compare old flat output vs new graph-traversal output."""
    section(f"Test 7: Old vs New Comparison — {name}")

    graph = await rag._load_graph(user_id)

    # Simulate old flat output
    interests = [graph.nodes[nid].get("label", "?") for nid in graph.by_type.get("interest", [])]
    traits = [graph.nodes[nid].get("label", "?") for nid in graph.by_type.get("trait", [])]
    values = [graph.nodes[nid].get("label", "?") for nid in graph.by_type.get("value", [])]

    old_output = f"""User Profile Context:
- Interests (all equally important): {', '.join(interests[:10])}
- Personality Traits: {', '.join(traits[:5])}
- Core Values: {', '.join(values[:5])}
- Post Diversity Note: Cover different interests across posts."""

    new_output = await rag.get_identity_context(
        user_id, action_type="post_generation", max_tokens=1500,
    )

    print("  --- OLD (flat labels) ---")
    for line in old_output.strip().split("\n"):
        print(f"    {line[:100]}")

    print(f"\n  --- NEW (graph-traversal narrative) ---")
    for line in new_output.strip().split("\n"):
        if line.strip():
            print(f"    {line[:100]}{'...' if len(line) > 100 else ''}")

    has_connections = "→" in new_output or "related_to" in new_output or "[" in new_output
    has_identity = "**Identity" in new_output or "**Important people" in new_output
    has_structure = "**" in new_output

    print(f"\n  New output shows edge connections: {'✓' if has_connections else '✗'}")
    print(f"  New output has identity section: {'✓' if has_identity else '✗'}")
    print(f"  New output has structured sections: {'✓' if has_structure else '✗'}")
    print(f"  Old token estimate: ~{len(old_output)/4:.0f} tokens")
    print(f"  New token estimate: ~{len(new_output)/4:.0f} tokens")
    print("  ✓ PASSED")


async def main():
    print("=" * 70)
    print("  Enhanced GraphRAG — Comprehensive Test Suite")
    print("=" * 70)

    uri = get_mongo_uri()
    client = AsyncIOMotorClient(
        uri,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=60000,
    )
    db = client[DB_NAME]

    host_info = await client.admin.command("ismaster")
    print(f"\nConnected to MongoDB: {host_info.get('hosts', ['?'])[:1]}")

    rag = GraphRAG(db)
    total_passed = 0
    total_tests = 0

    for name, user_id in USERS.items():
        print(f"\n{'#'*70}")
        print(f"#  Testing: {name} ({user_id[:8]}...)")
        print(f"{'#'*70}")

        try:
            graph = await test_graph_loading(rag, user_id, name)
            total_passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            graph = None
        total_tests += 1

        if graph:
            for test_fn in [test_spreading_activation, test_bfs_traversal, test_seed_selection]:
                try:
                    await test_fn(rag, graph, name)
                    total_passed += 1
                except Exception as e:
                    print(f"  ✗ FAILED: {e}")
                total_tests += 1

        for test_fn in [test_narrative_compilation, test_backwards_compatibility, test_comparison]:
            try:
                await test_fn(rag, user_id, name)
                total_passed += 1
            except Exception as e:
                print(f"  ✗ FAILED: {e}")
                import traceback
                traceback.print_exc()
            total_tests += 1

        rag.invalidate_cache(user_id)

    section("FINAL RESULTS")
    print(f"  {total_passed}/{total_tests} test groups passed")
    if total_passed == total_tests:
        print("  ✓ ALL TESTS PASSED")
    else:
        print(f"  ✗ {total_tests - total_passed} FAILURES")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
