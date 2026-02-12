"""
Test script: News Reaction Posts
Tests the full pipeline of browsing real news and creating reaction posts with links.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main():
    import boto3
    from motor.motor_asyncio import AsyncIOMotorClient

    print("=" * 70)
    print("  NEWS REACTION POST TEST")
    print("  Testing: real news fetch → emotional reaction → post with link")
    print("=" * 70)

    # ------- Load secrets -------
    import json as _json
    session = boto3.session.Session()
    sm = session.client(service_name="secretsmanager", region_name="us-west-1")

    mongo_resp = sm.get_secret_value(SecretId="2n1/mongodb/uri")
    mongo_secret = mongo_resp["SecretString"]
    try:
        mongo_dict = _json.loads(mongo_secret)
        mongo_uri = mongo_dict.get("uri") or mongo_dict.get("MONGO_URL") or mongo_secret
    except Exception:
        mongo_uri = mongo_secret

    openai_resp = sm.get_secret_value(SecretId="2n1/openai/api-key")
    openai_key = openai_resp["SecretString"]
    try:
        key_dict = _json.loads(openai_key)
        openai_key = key_dict.get("api_key") or key_dict.get("OPENAI_API_KEY") or openai_key
    except Exception:
        pass

    os.environ["OPENAI_API_KEY"] = openai_key
    os.environ["MONGODB_URI"] = mongo_uri

    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=openai_key)

    client = AsyncIOMotorClient(mongo_uri)
    db = client["neurallinks_local"]

    # ------- Pick an avatar -------
    avatar = await db.users.find_one({"avatar_name": "DigitalHunter"})
    if not avatar:
        avatar = await db.users.find_one({"is_bot": True})
    if not avatar:
        avatar = await db.users.find_one({"is_avatar": True})
    if not avatar:
        # Try to find any user with avatar_character_profile
        avatar = await db.users.find_one({"avatar_character_profile": {"$exists": True}})
    if not avatar:
        print("❌ No avatar found in database!")
        return
    avatar_id = avatar["id"]
    avatar_name = avatar.get("name", avatar_id)
    print(f"\n🤖 Avatar: {avatar_name} (ID: {avatar_id})")

    # Get avatar interests for context
    interests_cursor = db.graph_nodes.find(
        {"user_id": avatar_id, "node_type": "interest"},
        {"_id": 0, "label": 1, "strength": 1},
    ).sort("strength", -1).limit(10)
    interests = [n["label"] async for n in interests_cursor]
    print(f"📌 Interests: {interests}")

    # ============================================================
    # TEST 1: WebBrowsingService.get_shareable_news_for_avatar
    # ============================================================
    print("\n" + "=" * 70)
    print("  TEST 1: Fetch shareable news for avatar")
    print("=" * 70)

    from services.web_browsing_service import WebBrowsingService
    web_service = WebBrowsingService(db)

    news_items = await web_service.get_shareable_news_for_avatar(avatar_id, max_results=5)
    print(f"\n📰 Found {len(news_items)} shareable news items:\n")
    for i, item in enumerate(news_items, 1):
        print(f"  {i}. {item.get('title', 'No title')}")
        print(f"     Source: {item.get('source', '?')} | Type: {item.get('shareability', '?')}")
        print(f"     URL: {item.get('url', 'No URL')[:80]}")
        snippet = item.get("snippet", "")
        if snippet:
            print(f"     Snippet: {snippet[:120]}...")
        print()

    if not news_items:
        print("⚠️  No news found — DuckDuckGo may be rate-limiting. Trying again in 5s...")
        await asyncio.sleep(5)
        news_items = await web_service.get_shareable_news_for_avatar(avatar_id, max_results=3)
        if not news_items:
            print("❌ Still no news. Skipping post generation test.")
            return

    # ============================================================
    # TEST 2: PostOrchestrator — news reaction post
    # ============================================================
    print("\n" + "=" * 70)
    print("  TEST 2: Generate news reaction post via PostOrchestrator")
    print("=" * 70)

    from domain.avatar.orchestration.post_orchestrator import PostOrchestrator

    orchestrator = PostOrchestrator(db, openai_client)

    # Pick the first news item
    chosen_news = news_items[0]
    news_context = {
        "title": chosen_news.get("title", ""),
        "url": chosen_news.get("url", ""),
        "snippet": chosen_news.get("snippet", ""),
        "source": chosen_news.get("source", ""),
    }

    print(f"\n🎯 Reacting to: {news_context['title']}")
    print(f"   Source: {news_context['source']}")
    print(f"   URL: {news_context['url'][:80]}")

    result = await orchestrator.generate_post(
        user_id=avatar_id,
        avatar_id=avatar_id,
        trigger=f"just read: {news_context['title']}",
        mood="curious",
        energy_level=0.7,
        news_context=news_context,
    )

    post_text = result.get("text", "")
    meta = result.get("metadata", {})
    print(f"\n📝 Generated Post (pipeline: {meta.get('pipeline', '?')}):")
    print(f"   Reaction style: {meta.get('reaction_style', 'auto')}")
    print(f"   Quality: {result.get('quality_score', 0):.2f}")
    print()
    print("   " + "-" * 50)
    for line in post_text.split("\n"):
        print(f"   {line}")
    print("   " + "-" * 50)

    # Check that the URL is in the post
    url_present = news_context["url"] and news_context["url"] in post_text
    print(f"\n   ✅ URL included: {url_present}")
    if not url_present and news_context["url"]:
        print(f"   ⚠️  Expected URL: {news_context['url'][:60]}...")

    # ============================================================
    # TEST 3: Generate another news reaction for a different story
    # ============================================================
    if len(news_items) > 1:
        print("\n" + "=" * 70)
        print("  TEST 3: Another news reaction (different story)")
        print("=" * 70)

        chosen_news2 = news_items[1]
        news_context2 = {
            "title": chosen_news2.get("title", ""),
            "url": chosen_news2.get("url", ""),
            "snippet": chosen_news2.get("snippet", ""),
            "source": chosen_news2.get("source", ""),
        }

        print(f"\n🎯 Reacting to: {news_context2['title']}")

        await asyncio.sleep(2)  # Small delay for rate limiting
        result2 = await orchestrator.generate_post(
            user_id=avatar_id,
            avatar_id=avatar_id,
            trigger=f"just saw: {news_context2['title']}",
            mood="excited",
            energy_level=0.8,
            news_context=news_context2,
        )

        post_text2 = result2.get("text", "")
        meta2 = result2.get("metadata", {})
        print(f"\n📝 Generated Post (pipeline: {meta2.get('pipeline', '?')}):")
        print(f"   Reaction style: {meta2.get('reaction_style', 'auto')}")
        print()
        print("   " + "-" * 50)
        for line in post_text2.split("\n"):
            print(f"   {line}")
        print("   " + "-" * 50)

        url2_present = news_context2["url"] and news_context2["url"] in post_text2
        print(f"\n   ✅ URL included: {url2_present}")

    # ============================================================
    # TEST 4: BrowseAndShareNewsTool (full end-to-end via MCP)
    # ============================================================
    print("\n" + "=" * 70)
    print("  TEST 4: BrowseAndShareNewsTool (MCP tool — full pipeline)")
    print("=" * 70)

    # Set up OpenAI for the MCP module
    os.environ["OPENAI_API_KEY"] = openai_key

    # Need to set up get_openai_client
    try:
        from core.config import get_openai_client
        # Ensure it returns a valid client
        test_client = get_openai_client()
        if test_client is None:
            print("⚠️  get_openai_client() returned None — setting env and retrying")
    except Exception:
        pass

    from domain.avatar.mcp.server import BrowseAndShareNewsTool

    tool = BrowseAndShareNewsTool()
    print(f"\n🔧 Tool: {tool.name}")
    print(f"   Description: {tool.description[:80]}...")

    await asyncio.sleep(3)  # Rate limit buffer

    mcp_result = await tool._execute_action(avatar_id, mood="curious")

    if mcp_result.get("success"):
        print(f"\n✅ SUCCESS!")
        print(f"   Post ID: {mcp_result.get('post_id', '?')}")
        print(f"   News: {mcp_result.get('news_title', '?')}")
        print(f"   URL: {mcp_result.get('news_url', '?')[:80]}")
        print(f"\n   Post text:")
        print("   " + "-" * 50)
        for line in mcp_result.get("post_text", "").split("\n"):
            print(f"   {line}")
        print("   " + "-" * 50)
    else:
        print(f"\n❌ FAILED: {mcp_result.get('error', 'Unknown error')}")

    print("\n" + "=" * 70)
    print("  ALL TESTS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
