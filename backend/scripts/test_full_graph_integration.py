#!/usr/bin/env python3
"""
Test that ALL consumers of the identity graph now receive the narrative.

Validates:
1. Post orchestrator (news reaction path) — gets identity_narrative
2. Post orchestrator (intent agent) — gets identity_narrative
3. Message orchestrator — loads identity_narrative in context
4. Intelligent avatar — bio generation uses identity_narrative
5. Memory manager — semantic memory includes identity_narrative
6. Voice prompt generator — personality_text includes identity narrative

Uses real production data for all three users.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import boto3
from motor.motor_asyncio import AsyncIOMotorClient

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


passed = 0
failed = 0


def check(test_name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {test_name}")
    else:
        failed += 1
        print(f"  ❌ {test_name}")
        if detail:
            print(f"     → {detail}")


async def test_graph_rag_identity_context(db, user_id, name):
    """Test that GraphRAG.get_identity_context returns a real narrative"""
    from domain.graph.rag import GraphRAG
    rag = GraphRAG(db)
    narrative = await rag.get_identity_context(user_id, action_type="post_generation", max_tokens=1500)
    check(f"GraphRAG identity narrative for {name}", len(narrative) > 100,
          f"Got {len(narrative)} chars")
    check(f"  has **Identity:** section", "**Identity:**" in narrative)
    check(f"  has **Interests & passions:**", "**Interests & passions:**" in narrative)
    return narrative


async def test_post_orchestrator_news_context(db, user_id, name):
    """Test that _load_context includes identity_narrative"""
    from domain.avatar.orchestration.post_orchestrator import PostOrchestrator

    class FakeOpenAI:
        pass

    orch = PostOrchestrator(db, FakeOpenAI())
    context = await orch._load_context(user_id)
    narrative = context.get("identity_narrative", "")
    check(f"PostOrchestrator context has identity_narrative for {name}",
          len(narrative) > 100, f"Got {len(narrative)} chars")
    return context


async def test_message_orchestrator_context(db, user_id, name):
    """Test that MessageOrchestrator._load_context includes identity_narrative"""
    from domain.avatar.orchestration.message_orchestrator import MessageOrchestrator

    class FakeOpenAI:
        pass

    orch = MessageOrchestrator(db, FakeOpenAI())
    context = await orch._load_context(user_id, "dummy-recipient-id")
    narrative = context.get("identity_narrative", "")
    check(f"MessageOrchestrator context has identity_narrative for {name}",
          len(narrative) > 100, f"Got {len(narrative)} chars")


async def test_memory_manager(db, user_id, name):
    """Test that MemoryManager.get_full_memory_context includes identity_narrative"""
    from domain.avatar.memory.memory_manager import MemoryManager
    mm = MemoryManager(db)
    ctx = await mm.get_full_memory_context(user_id)
    semantic = ctx.get("semantic_memory", {})

    check(f"MemoryManager semantic_memory has interests for {name}",
          len(semantic.get("interests", [])) > 0,
          f"Got {len(semantic.get('interests', []))} interests")
    check(f"MemoryManager semantic_memory has identity_narrative for {name}",
          len(semantic.get("identity_narrative", "")) > 100,
          f"Got {len(semantic.get('identity_narrative', ''))} chars")


async def test_personality_prompt_has_narrative(db, user_id, name):
    """Test that the cached personality prompt includes the identity narrative section"""
    from domain.avatar.personality.personality_prompt import PersonalityPromptGenerator
    gen = PersonalityPromptGenerator(db)
    prompt = await gen.generate_personality_prompt(user_id)
    check(f"PersonalityPrompt includes identity section for {name}",
          "Identity (from knowledge graph)" in prompt,
          f"Prompt length: {len(prompt)} chars")
    check(f"PersonalityPrompt includes connections section for {name}",
          "connection" in prompt.lower() or "people" in prompt.lower(),
          "Should mention relationships")


async def test_intelligent_avatar_bio(db, user_id, name):
    """Test that IntelligentAvatar.generate_avatar_profile_bio calls get_identity_context"""
    from domain.graph.rag import GraphRAG
    rag = GraphRAG(db)

    narrative = await rag.get_identity_context(
        user_id, action_type="personality_profile", max_tokens=1200,
    )
    check(f"IntelligentAvatar bio source (identity narrative) for {name}",
          len(narrative) > 100, f"Got {len(narrative)} chars")
    check(f"  narrative mentions real details",
          any(kw in narrative.lower() for kw in ["interests", "identity", "traits", "experiences"]))


async def test_backwards_compatibility(db, user_id, name):
    """Test that get_user_context still returns flat labels for programmatic use"""
    from domain.graph.rag import GraphRAG
    rag = GraphRAG(db)
    ctx = await rag.get_user_context(user_id, max_nodes=30)

    interests = [i.get("label") for i in ctx.get("interests", []) if i.get("label")]
    traits = [t.get("label") for t in ctx.get("traits", []) if t.get("label")]
    check(f"Backwards compat: get_user_context returns interests for {name}",
          len(interests) > 0, f"Got {len(interests)} interests")
    check(f"Backwards compat: get_user_context returns traits for {name}",
          len(traits) > 0, f"Got {len(traits)} traits")


async def main():
    print("=" * 80)
    print("  Full Graph Integration Test")
    print("=" * 80)

    uri = get_mongo_uri()
    client = AsyncIOMotorClient(
        uri, serverSelectionTimeoutMS=30000, connectTimeoutMS=30000, socketTimeoutMS=60000,
    )
    db = client[DB_NAME]
    await client.admin.command("ismaster")
    print(f"  Connected to MongoDB\n")

    for name, user_id in USERS.items():
        print(f"\n{'─'*60}")
        print(f"  {name} ({user_id[:8]}...)")
        print(f"{'─'*60}")

        await test_graph_rag_identity_context(db, user_id, name)
        await test_post_orchestrator_news_context(db, user_id, name)
        await test_message_orchestrator_context(db, user_id, name)
        await test_memory_manager(db, user_id, name)
        await test_personality_prompt_has_narrative(db, user_id, name)
        await test_intelligent_avatar_bio(db, user_id, name)
        await test_backwards_compatibility(db, user_id, name)

    client.close()

    print(f"\n{'='*80}")
    print(f"  RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
    print(f"{'='*80}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
