#!/usr/bin/env python3
"""
Test Life Moment Post Generation
Tests the new "life moment" post generation system that makes avatar posts
feel like a real person sharing moments from their life.

Tests both paths:
1. PostOrchestrator (primary — multi-agent pipeline)
2. IntelligentAvatar.generate_avatar_post (fallback)
3. IntelligentAvatar.generate_diverse_post (diverse types)
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import boto3
import json
import os
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from datetime import datetime, timezone
from domain.graph.rag import GraphRAG
from domain.avatar.intelligent import IntelligentAvatar
from domain.avatar.orchestration.post_orchestrator import PostOrchestrator


def get_secrets():
    """Get MongoDB URL and OpenAI key from AWS Secrets Manager"""
    session = boto3.session.Session()
    sm = session.client(service_name='secretsmanager', region_name='us-west-1')

    # MongoDB URI
    mongo_resp = sm.get_secret_value(SecretId='2n1/mongodb/uri')
    mongo_secret = mongo_resp['SecretString']
    try:
        mongo_dict = json.loads(mongo_secret)
        mongo_url = mongo_dict.get('uri') or mongo_dict.get('MONGO_URL')
    except Exception:
        mongo_url = mongo_secret

    # OpenAI API Key
    openai_key = os.environ.get('OPENAI_API_KEY', '')
    if not openai_key:
        try:
            openai_resp = sm.get_secret_value(SecretId='2n1/openai/api-key')
            openai_key = openai_resp['SecretString']
            # Try parsing as JSON in case it's wrapped
            try:
                key_dict = json.loads(openai_key)
                openai_key = key_dict.get('api_key') or key_dict.get('OPENAI_API_KEY') or openai_key
            except Exception:
                pass
        except Exception as e:
            print(f"  Warning: Could not get OpenAI key from Secrets Manager: {e}")

    return mongo_url, openai_key


async def test_post_orchestrator(db, openai_client, user_id: str, avatar_name: str):
    """Test the PostOrchestrator multi-agent pipeline (primary path)."""
    print("\n" + "=" * 70)
    print("  PATH 1: PostOrchestrator — Life Moment Pipeline")
    print("=" * 70)

    orchestrator = PostOrchestrator(db, openai_client)

    scenarios = [
        {
            "label": "Spontaneous (no hint)",
            "trigger": "",
            "topic_hint": "",
            "mood": "content",
            "energy": 0.7,
        },
        {
            "label": "Emotional / reflective",
            "trigger": "feeling reflective about life",
            "topic_hint": "",
            "mood": "reflective",
            "energy": 0.4,
        },
        {
            "label": "High energy, creative",
            "trigger": "burst of creative energy",
            "topic_hint": "",
            "mood": "excited",
            "energy": 0.9,
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'─' * 60}")
        print(f"  Test {i}/3: {scenario['label']}")
        print(f"  Mood={scenario['mood']}  Energy={scenario['energy']}")
        print(f"{'─' * 60}")

        try:
            result = await orchestrator.generate_post(
                user_id=user_id,
                avatar_id=user_id,
                trigger=scenario["trigger"],
                topic_hint=scenario["topic_hint"],
                mood=scenario["mood"],
                energy_level=scenario["energy"],
            )

            text = result.get("text", "")
            score = result.get("quality_score", 0)
            meta = result.get("metadata", {})
            intent = meta.get("intent", {})

            print(f"\n  Life moment type: {intent.get('moment_type', intent.get('emotional_driver', 'N/A'))}")
            print(f"  Emotional state: {intent.get('emotional_state', intent.get('emotional_driver', 'N/A'))}")
            print(f"  Quality score: {score:.2f}")
            print(f"\n  POST:")
            print(f"  ┌{'─' * 56}┐")
            for line in text.split('\n'):
                # Word-wrap long lines
                while len(line) > 54:
                    print(f"  │ {line[:54]} │")
                    line = line[54:]
                print(f"  │ {line:<54} │")
            print(f"  └{'─' * 56}┘")
            print(f"  Length: {len(text)} chars")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(2)


async def test_intelligent_avatar_post(db, openai_client, user_id: str, avatar_name: str):
    """Test IntelligentAvatar.generate_avatar_post (fallback path)."""
    print("\n" + "=" * 70)
    print("  PATH 2: IntelligentAvatar — Life Moment Fallback")
    print("=" * 70)

    graph_rag = GraphRAG(db)
    intelligent_avatar = IntelligentAvatar(db, openai_client, "gpt-4o-mini", graph_rag)

    for i in range(2):
        print(f"\n{'─' * 60}")
        print(f"  Test {i + 1}/2: generate_avatar_post (general)")
        print(f"{'─' * 60}")

        try:
            result = await intelligent_avatar.generate_avatar_post(
                user_id=user_id,
                post_type="general",
            )

            if "error" in result:
                print(f"  ERROR: {result['error']}")
            else:
                text = result.get("content", "")
                print(f"\n  POST:")
                print(f"  ┌{'─' * 56}┐")
                for line in text.split('\n'):
                    while len(line) > 54:
                        print(f"  │ {line[:54]} │")
                        line = line[54:]
                    print(f"  │ {line:<54} │")
                print(f"  └{'─' * 56}┘")
                print(f"  Length: {len(text)} chars")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(2)


async def test_diverse_posts(db, openai_client, user_id: str, avatar_name: str):
    """Test IntelligentAvatar.generate_diverse_post."""
    print("\n" + "=" * 70)
    print("  PATH 3: IntelligentAvatar — Diverse Post Types")
    print("=" * 70)

    graph_rag = GraphRAG(db)
    intelligent_avatar = IntelligentAvatar(db, openai_client, "gpt-4o-mini", graph_rag)

    # Test auto-selection twice to see variety
    for i in range(2):
        print(f"\n{'─' * 60}")
        print(f"  Test {i + 1}/2: generate_diverse_post (auto)")
        print(f"{'─' * 60}")

        try:
            result = await intelligent_avatar.generate_diverse_post(
                user_id=user_id,
                post_type="auto",
            )

            if "error" in result:
                print(f"  ERROR: {result['error']}")
            else:
                text = result.get("content", "")
                selected_type = result.get("type", "unknown")
                print(f"  Selected type: {selected_type}")
                print(f"\n  POST:")
                print(f"  ┌{'─' * 56}┐")
                for line in text.split('\n'):
                    while len(line) > 54:
                        print(f"  │ {line[:54]} │")
                        line = line[54:]
                    print(f"  │ {line:<54} │")
                print(f"  └{'─' * 56}┘")
                print(f"  Length: {len(text)} chars")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(2)


async def main():
    print("\n" + "=" * 70)
    print("  LIFE MOMENT POST GENERATION — FULL TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Connect
    mongo_url, openai_key = get_secrets()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']

    if not openai_key:
        print("\n  ERROR: No OpenAI API key found!")
        print("  Set OPENAI_API_KEY env var or add to backend/.env")
        client.close()
        return

    openai_client = AsyncOpenAI(api_key=openai_key)
    print(f"  OpenAI client: initialized")

    # Find the avatar
    user = await db.users.find_one({"avatar_name": "DigitalHunter"})
    if not user:
        # Try any avatar
        user = await db.users.find_one({"is_bot": True})
    if not user:
        print("No avatar found in the database!")
        client.close()
        return

    user_id = user.get("id")
    avatar_name = user.get("avatar_name", user.get("name", "Unknown"))
    print(f"\n  Avatar: {avatar_name}")
    print(f"  User ID: {user_id}")

    # Show current interests for reference
    interest_nodes = await db.graph_nodes.find(
        {"user_id": user_id, "node_type": "interest"},
        {"_id": 0, "label": 1, "properties.strength": 1}
    ).sort("properties.strength", -1).limit(15).to_list(15)

    print(f"\n  Interests ({len(interest_nodes)} found):")
    for node in interest_nodes:
        strength = node.get("properties", {}).get("strength", 0)
        print(f"    - {node['label']} (strength: {strength:.2f})")

    # Show recent avatar posts for comparison
    recent_posts = await db.posts.find(
        {"user_id": user_id, "post_type": "avatar"},
        {"_id": 0, "text": 1}
    ).sort("created_at", -1).limit(3).to_list(3)

    if recent_posts:
        print(f"\n  Recent avatar posts (for comparison):")
        for p in recent_posts:
            print(f"    > {p.get('text', '')[:80]}...")

    # Run all tests
    await test_post_orchestrator(db, openai_client, user_id, avatar_name)
    await test_intelligent_avatar_post(db, openai_client, user_id, avatar_name)
    await test_diverse_posts(db, openai_client, user_id, avatar_name)

    print("\n" + "=" * 70)
    print("  ALL TESTS COMPLETE")
    print("=" * 70 + "\n")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
