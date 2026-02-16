#!/usr/bin/env python3
"""
Test that ALL post types (regular + news) get images attached.
Runs 2 avatars: one regular life post, one news reaction post each.
"""
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


def log(msg):
    print(msg, flush=True)


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

    test_set = avatars[:2]
    log(f"Testing image attachment for {len(test_set)} avatars...\n")

    from services.web_browsing_service import WebBrowsingService
    from domain.avatar.orchestration.post_orchestrator import PostOrchestrator

    for i, av in enumerate(test_set):
        uid = av.get('id')
        name = av.get('name', '?')
        aname = av.get('avatar_name', '?')

        log(f"{'='*60}")
        log(f"  {name} ({aname})")
        log(f"{'='*60}")

        orch = PostOrchestrator(db, oc)

        # ---- TEST 1: Regular life post (no news) ----
        log(f"\n  [1] REGULAR LIFE POST:")
        result1 = await orch.generate_post(
            user_id=uid, avatar_id=uid,
            trigger="reflecting on the week",
            mood="happy",
            energy_level=0.7,
        )
        text1 = result1.get('text', '')[:150]
        img1 = result1.get('image_url', '')
        log(f"  Text: {text1}...")
        log(f"  Image: {'YES - ' + img1[:80] if img1 else 'NO IMAGE'}")
        log(f"  LLM query used: (check logs)")

        await asyncio.sleep(3)

        # ---- TEST 2: News reaction post ----
        log(f"\n  [2] NEWS REACTION POST:")
        ws = WebBrowsingService(db)
        news = await ws.get_shareable_news_for_avatar(uid, max_results=3)
        if news:
            chosen = random.choice(news)
            news_ctx = {
                'title': chosen.get('title', ''),
                'url': chosen.get('url', ''),
                'snippet': chosen.get('snippet', ''),
                'source': chosen.get('source', ''),
            }
            log(f"  News: {news_ctx['title'][:70]}")

            result2 = await orch.generate_post(
                user_id=uid, avatar_id=uid,
                trigger='came across: ' + news_ctx['title'],
                mood='curious',
                energy_level=0.7,
                news_context=news_ctx,
            )
            text2 = result2.get('text', '')[:150]
            img2 = result2.get('image_url', '')
            log(f"  Text: {text2}...")
            log(f"  Image: {'YES - ' + img2[:80] if img2 else 'NO IMAGE'}")
        else:
            log(f"  (no news found)")

        if i < len(test_set) - 1:
            log(f"\n  Waiting 8s...")
            await asyncio.sleep(8)

    client.close()
    log(f"\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
