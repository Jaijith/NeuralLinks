#!/usr/bin/env python3
"""Test voice diversity across 3 avatars to verify posts sound unique."""
import asyncio
import os
import sys
import json
import boto3
import random
import warnings

warnings.filterwarnings("ignore")

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    raw = boto3.session.Session().client(
        'secretsmanager', region_name='us-west-1'
    ).get_secret_value(SecretId='2n1/mongodb/uri')['SecretString']
    try:
        url = json.loads(raw).get('uri', raw)
    except Exception:
        url = raw

    raw_oai = boto3.session.Session().client(
        'secretsmanager', region_name='us-west-1'
    ).get_secret_value(SecretId='2n1/openai/api-key')['SecretString']
    try:
        oai_key = json.loads(raw_oai).get('api_key', raw_oai)
    except Exception:
        oai_key = raw_oai

    os.environ['OPENAI_API_KEY'] = oai_key
    os.environ['MONGODB_URI'] = url

    from openai import AsyncOpenAI
    oc = AsyncOpenAI(api_key=oai_key)
    client = AsyncIOMotorClient(url)
    db = client['neurallinks_local']

    avatars = await db.users.find(
        {"avatar_actions_enabled": {"$exists": True}},
        {"_id": 0}
    ).to_list(500)

    test_set = avatars[:3]
    print(f"Testing {len(test_set)} avatars for voice diversity...\n", flush=True)

    from services.web_browsing_service import WebBrowsingService
    from domain.avatar.orchestration.post_orchestrator import PostOrchestrator

    for i, av in enumerate(test_set):
        uid = av.get('id')
        name = av.get('name', '?')
        aname = av.get('avatar_name', '?')
        cp = av.get('avatar_character_profile', {})

        print(f"{'='*60}", flush=True)
        print(f"  {name} ({aname})", flush=True)
        print(f"  Traits: {cp.get('personality_traits', [])[:4]}", flush=True)
        print(f"  Interests: {cp.get('interests', [])[:5]}", flush=True)
        print(f"{'='*60}", flush=True)

        ws = WebBrowsingService(db)
        news = await ws.get_shareable_news_for_avatar(uid, max_results=3)
        if not news:
            print("  No news found\n", flush=True)
            continue

        chosen = random.choice(news)
        news_ctx = {
            'title': chosen.get('title', ''),
            'url': chosen.get('url', ''),
            'snippet': chosen.get('snippet', ''),
            'source': chosen.get('source', ''),
        }
        print(f"  News: {news_ctx['title'][:70]}", flush=True)

        orch = PostOrchestrator(db, oc)
        result = await orch.generate_post(
            user_id=uid, avatar_id=uid,
            trigger='came across: ' + news_ctx['title'],
            mood=random.choice(['curious', 'excited', 'happy']),
            energy_level=0.7,
            news_context=news_ctx,
        )

        post = result.get('text', '')
        meta = result.get('metadata', {})
        print(f"  Structure: {meta.get('post_structure', '?')}", flush=True)
        print(f"  Tone: {meta.get('reaction_style', '?')}", flush=True)
        print(f"\n  --- POST ---", flush=True)
        print(f"  {post[:400]}", flush=True)
        print(f"  --- END ---\n", flush=True)

        if i < len(test_set) - 1:
            await asyncio.sleep(8)

    client.close()
    print("Done!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
