#!/usr/bin/env python3
"""
Test Web Browsing → Posting Integration
Tests the full flow:
1. WebBrowsingService: search_web, search_news, search_images, browse_for_avatar
2. Image search → create_post with image_url (auto image_query flow)
3. PostOrchestrator: generate a post inspired by a browsing discovery
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import boto3
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from datetime import datetime, timezone
from services.web_browsing_service import WebBrowsingService
from domain.avatar.orchestration.post_orchestrator import PostOrchestrator


def get_secrets():
    """Get MongoDB URL and OpenAI key from AWS Secrets Manager"""
    session = boto3.session.Session()
    sm = session.client(service_name='secretsmanager', region_name='us-west-1')

    mongo_resp = sm.get_secret_value(SecretId='2n1/mongodb/uri')
    mongo_secret = mongo_resp['SecretString']
    try:
        mongo_dict = json.loads(mongo_secret)
        mongo_url = mongo_dict.get('uri') or mongo_dict.get('MONGO_URL')
    except Exception:
        mongo_url = mongo_secret

    openai_key = os.environ.get('OPENAI_API_KEY', '')
    if not openai_key:
        try:
            openai_resp = sm.get_secret_value(SecretId='2n1/openai/api-key')
            openai_key = openai_resp['SecretString']
            try:
                key_dict = json.loads(openai_key)
                openai_key = key_dict.get('api_key') or key_dict.get('OPENAI_API_KEY') or openai_key
            except Exception:
                pass
        except Exception as e:
            print(f"  Warning: Could not get OpenAI key: {e}")

    return mongo_url, openai_key


def print_box(title, content, width=64):
    """Pretty-print a boxed section."""
    print(f"\n  {'─' * width}")
    print(f"  {title}")
    print(f"  {'─' * width}")
    if isinstance(content, str):
        for line in content.split('\n'):
            while len(line) > width - 4:
                print(f"  │ {line[:width-4]} │")
                line = line[width-4:]
            print(f"  │ {line:<{width-4}} │")
    print()


async def test_1_web_search(service: WebBrowsingService):
    """Test basic web search."""
    print("\n" + "=" * 68)
    print("  TEST 1: Web Search (search_web)")
    print("=" * 68)

    results = await service.search_web("technology innovation 2026", max_results=3)
    print(f"\n  Results: {len(results)}")
    for i, r in enumerate(results, 1):
        print(f"\n  [{i}] {r.get('title', 'No title')}")
        print(f"      URL: {r.get('url', '')[:70]}")
        print(f"      Snippet: {r.get('snippet', '')[:100]}...")
    return len(results) > 0


async def test_2_news_search(service: WebBrowsingService):
    """Test news search."""
    print("\n" + "=" * 68)
    print("  TEST 2: News Search (search_news)")
    print("=" * 68)

    results = await service.search_news("artificial intelligence", max_results=3, timelimit="w")
    print(f"\n  Results: {len(results)}")
    for i, r in enumerate(results, 1):
        print(f"\n  [{i}] {r.get('title', 'No title')}")
        print(f"      Source: {r.get('source', 'unknown')}")
        print(f"      Snippet: {r.get('snippet', '')[:100]}...")
    return len(results) > 0


async def test_3_image_search(service: WebBrowsingService):
    """Test image search."""
    print("\n" + "=" * 68)
    print("  TEST 3: Image Search (search_images)")
    print("=" * 68)

    results = await service.search_images("nature photography sunset", max_results=3)
    print(f"\n  Results: {len(results)}")
    for i, r in enumerate(results, 1):
        print(f"\n  [{i}] {r.get('title', 'No title')[:60]}")
        print(f"      Image URL: {r.get('image_url', '')[:70]}...")
        print(f"      Dimensions: {r.get('width', '?')}x{r.get('height', '?')}")
    return len(results) > 0


async def test_4_find_image_for_topic(service: WebBrowsingService):
    """Test find_image_for_topic (used by create_post image_query)."""
    print("\n" + "=" * 68)
    print("  TEST 4: Find Image For Topic (create_post integration)")
    print("=" * 68)

    topics = ["music festival", "garden flowers", "coding workspace"]
    all_found = True
    for topic in topics:
        images = await service.find_image_for_topic(topic, style="photo", count=2)
        print(f"\n  Topic: '{topic}' → {len(images)} images found")
        if images:
            print(f"      Best: {images[0].get('image_url', '')[:70]}...")
        else:
            all_found = False
    return all_found


async def test_5_browse_for_avatar(service: WebBrowsingService, user_id: str, avatar_name: str):
    """Test personality-aware browsing for a specific avatar."""
    print("\n" + "=" * 68)
    print(f"  TEST 5: Browse For Avatar — {avatar_name}")
    print("=" * 68)

    result = await service.browse_for_avatar(
        avatar_id=user_id,
        browse_type="auto",
    )

    print(f"\n  Success: {result.get('success')}")
    print(f"  Browse type: {result.get('browse_type')}")
    print(f"  Queries used: {result.get('queries_used', [])}")
    print(f"  Total results: {result.get('total_results', 0)}")

    news = result.get("news", [])
    articles = result.get("articles", [])
    images = result.get("images", [])

    if news:
        print(f"\n  NEWS ({len(news)}):")
        for n in news[:2]:
            print(f"    - {n.get('title', '')[:60]}")

    if articles:
        print(f"\n  ARTICLES ({len(articles)}):")
        for a in articles[:2]:
            print(f"    - {a.get('title', '')[:60]}")

    if images:
        print(f"\n  IMAGES ({len(images)}):")
        for img in images[:2]:
            print(f"    - {img.get('title', '')[:50]} → {img.get('image_url', '')[:40]}...")

    return result.get("success", False) and result.get("total_results", 0) > 0


async def test_6_post_with_image_query(db, openai_client, user_id: str, avatar_name: str):
    """
    Test the full flow: image_query → WebBrowsingService finds image → 
    PostOrchestrator generates post text → post created with image.
    This mimics what CreatePostTool does with image_query parameter.
    """
    print("\n" + "=" * 68)
    print(f"  TEST 6: Create Post with Image (image_query flow)")
    print("=" * 68)

    image_query = "technology innovation"
    print(f"\n  Image query: '{image_query}'")

    # Step 1: Find an image (same as CreatePostTool does)
    web_service = WebBrowsingService(db)
    images = await web_service.find_image_for_topic(image_query, style="photo", count=1)
    image_url = ""
    if images:
        image_url = images[0].get("image_url", "")
        print(f"  Found image: {image_url[:70]}...")
    else:
        print(f"  No image found (post will be text-only)")

    # Step 2: Generate post text with PostOrchestrator
    orchestrator = PostOrchestrator(db, openai_client)
    result = await orchestrator.generate_post(
        user_id=user_id,
        avatar_id=user_id,
        trigger="sharing a visual discovery from browsing the web",
        topic_hint=image_query,
        mood="excited",
        energy_level=0.8,
    )

    post_text = result.get("text", "")
    quality = result.get("quality_score", 0)
    meta = result.get("metadata", {})
    intent = meta.get("intent", {})

    print(f"\n  Life moment type: {intent.get('moment_type', 'N/A')}")
    print(f"  Quality score: {quality:.2f}")
    print(f"  Has image: {bool(image_url)}")
    print_box("GENERATED POST (with image)", post_text)
    if image_url:
        print(f"  Image URL: {image_url[:80]}...")

    # Step 3: Simulate saving the post (without actually saving)
    post = {
        "id": f"test-post-{datetime.now(timezone.utc).timestamp()}",
        "user_id": user_id,
        "text": post_text,
        "post_type": "avatar",
        "has_image": bool(image_url),
    }
    if image_url:
        post["image_url"] = image_url

    print(f"\n  Post would be saved with:")
    print(f"    - text: {len(post_text)} chars")
    print(f"    - image: {'YES' if image_url else 'NO'}")
    print(f"    - type: avatar")

    return bool(post_text)


async def test_7_browsing_inspired_post(db, openai_client, service: WebBrowsingService, user_id: str):
    """
    Full integration: browse web → discover content → generate a post inspired by it.
    This tests the flow where an avatar browses, finds interesting news,
    and creates a reaction/sharing post.
    """
    print("\n" + "=" * 68)
    print("  TEST 7: Browsing-Inspired Post (full integration)")
    print("=" * 68)

    # Step 1: Avatar browses the web
    print("\n  Step 1: Avatar browses the web...")
    browse_result = await service.browse_for_avatar(
        avatar_id=user_id,
        browse_type="news",
    )

    news = browse_result.get("news", [])
    if not news:
        print("  No news found — trying direct search...")
        news = await service.search_news("latest technology trends", max_results=3)

    if not news:
        print("  Could not find any news. Skipping this test.")
        return False

    # Pick a news item to react to
    chosen = news[0]
    news_title = chosen.get("title", "something interesting")
    print(f"  Found: '{news_title[:60]}...'")

    # Step 2: Generate a post reacting to what was found
    print("\n  Step 2: Generate a reaction post...")
    orchestrator = PostOrchestrator(db, openai_client)
    result = await orchestrator.generate_post(
        user_id=user_id,
        avatar_id=user_id,
        trigger=f"just read this: {news_title}",
        topic_hint="",
        mood="curious",
        energy_level=0.7,
    )

    post_text = result.get("text", "")
    intent = result.get("metadata", {}).get("intent", {})
    print(f"  Life moment: {intent.get('moment_type', 'N/A')}")
    print_box("BROWSING-INSPIRED POST", post_text)

    return bool(post_text)


async def main():
    print("\n" + "=" * 68)
    print("  WEB BROWSING → POSTING INTEGRATION TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 68)

    # Connect
    mongo_url, openai_key = get_secrets()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    openai_client = AsyncOpenAI(api_key=openai_key) if openai_key else None

    # Find avatar
    user = await db.users.find_one({"avatar_name": "DigitalHunter"})
    if not user:
        user = await db.users.find_one({"is_bot": True})
    if not user:
        print("  No avatar found!")
        client.close()
        return

    user_id = user.get("id")
    avatar_name = user.get("avatar_name", "Unknown")
    print(f"\n  Avatar: {avatar_name}")
    print(f"  User ID: {user_id}")

    # Create service
    service = WebBrowsingService(db)

    # Run tests
    results = {}

    results["1_web_search"] = await test_1_web_search(service)
    await asyncio.sleep(2)

    results["2_news_search"] = await test_2_news_search(service)
    await asyncio.sleep(2)

    results["3_image_search"] = await test_3_image_search(service)
    await asyncio.sleep(2)

    results["4_find_image_for_topic"] = await test_4_find_image_for_topic(service)
    await asyncio.sleep(2)

    results["5_browse_for_avatar"] = await test_5_browse_for_avatar(service, user_id, avatar_name)
    await asyncio.sleep(2)

    if openai_client:
        results["6_post_with_image"] = await test_6_post_with_image_query(db, openai_client, user_id, avatar_name)
        await asyncio.sleep(2)

        results["7_browsing_inspired_post"] = await test_7_browsing_inspired_post(db, openai_client, service, user_id)
    else:
        print("\n  Skipping tests 6-7 (no OpenAI key)")
        results["6_post_with_image"] = "SKIPPED"
        results["7_browsing_inspired_post"] = "SKIPPED"

    # Summary
    print("\n" + "=" * 68)
    print("  RESULTS SUMMARY")
    print("=" * 68)
    for test_name, passed in results.items():
        status = "PASS" if passed is True else ("SKIP" if passed == "SKIPPED" else "FAIL")
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}[status]
        print(f"  {icon} {test_name}: {status}")

    all_passed = all(v is True for v in results.values() if v != "SKIPPED")
    print(f"\n  {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print("=" * 68 + "\n")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
