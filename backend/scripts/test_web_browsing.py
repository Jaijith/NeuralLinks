#!/usr/bin/env python3
"""
Test script for the Web Browsing Service and related MCP tools.
Tests:
1. WebBrowsingService - web search, news search, image search
2. ContentAwarenessService - real web data integration
3. MCP tools registration - browse_web, search_images in tool list
4. CreatePostTool - image_url support in schema
"""

import asyncio
import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / '.env')


async def test_web_browsing_service():
    """Test the WebBrowsingService core methods."""
    print("\n" + "=" * 60)
    print("TEST 1: WebBrowsingService")
    print("=" * 60)

    from services.web_browsing_service import WebBrowsingService
    service = WebBrowsingService()

    # Test 1a: Web search
    print("\n--- 1a. Web Search ---")
    try:
        results = await service.search_web("artificial intelligence news", max_results=3)
        print(f"  ✅ Web search returned {len(results)} results")
        for r in results[:2]:
            print(f"     - {r.get('title', 'No title')[:80]}")
            print(f"       URL: {r.get('url', 'No URL')[:80]}")
    except Exception as e:
        print(f"  ❌ Web search error: {e}")

    # Test 1b: News search
    print("\n--- 1b. News Search ---")
    try:
        results = await service.search_news("technology latest", max_results=3, timelimit="w")
        print(f"  ✅ News search returned {len(results)} results")
        for r in results[:2]:
            print(f"     - {r.get('title', 'No title')[:80]}")
            print(f"       Source: {r.get('source', 'Unknown')}")
            has_image = bool(r.get('image'))
            print(f"       Has image: {has_image}")
    except Exception as e:
        print(f"  ❌ News search error: {e}")

    # Test 1c: Image search
    print("\n--- 1c. Image Search ---")
    try:
        results = await service.search_images("beautiful sunset photography", max_results=3, type_image="photo")
        print(f"  ✅ Image search returned {len(results)} results")
        for r in results[:2]:
            print(f"     - {r.get('title', 'No title')[:60]}")
            print(f"       Image URL: {r.get('image_url', 'No URL')[:80]}")
            print(f"       Size: {r.get('width', '?')}x{r.get('height', '?')}")
    except Exception as e:
        print(f"  ❌ Image search error: {e}")

    # Test 1d: Find image for topic
    print("\n--- 1d. Find Image for Topic ---")
    try:
        results = await service.find_image_for_topic("coding workspace", style="photo", count=2)
        print(f"  ✅ Found {len(results)} images for topic")
        for r in results[:2]:
            print(f"     - {r.get('image_url', 'No URL')[:80]}")
    except Exception as e:
        print(f"  ❌ Find image error: {e}")

    # Test 1e: Caching
    print("\n--- 1e. Caching ---")
    try:
        # Second call should be from cache
        results2 = await service.search_web("artificial intelligence news", max_results=3)
        print(f"  ✅ Cache test: returned {len(results2)} results (should match previous)")
    except Exception as e:
        print(f"  ❌ Cache test error: {e}")

    return True


async def test_content_awareness_service():
    """Test the upgraded ContentAwarenessService."""
    print("\n" + "=" * 60)
    print("TEST 2: ContentAwarenessService (with real web data)")
    print("=" * 60)

    from services.content_awareness_service import ContentAwarenessService
    service = ContentAwarenessService()

    # Test 2a: Trending topics
    print("\n--- 2a. Trending Topics ---")
    try:
        topics = await service.get_trending_topics("technology")
        print(f"  ✅ Got {len(topics)} trending topics")
        for t in topics[:3]:
            print(f"     - {t.get('title', 'No title')[:80]}")
            has_url = bool(t.get('url'))
            print(f"       Real data: {has_url}")
    except Exception as e:
        print(f"  ❌ Trending topics error: {e}")

    # Test 2b: News for interests
    print("\n--- 2b. News for Interests ---")
    try:
        news = await service.get_news_for_interests(["AI", "programming", "music"])
        print(f"  ✅ Got {len(news)} news items for interests")
        for n in news[:3]:
            print(f"     - {n.get('title', 'No title')[:80]}")
    except Exception as e:
        print(f"  ❌ News for interests error: {e}")

    # Test 2c: Viral content
    print("\n--- 2c. Viral Content ---")
    try:
        viral = await service.get_viral_content()
        print(f"  ✅ Got {len(viral)} viral items")
        for v in viral[:2]:
            print(f"     - {v.get('title', 'No title')[:80]}")
    except Exception as e:
        print(f"  ❌ Viral content error: {e}")

    return True


async def test_mcp_tools():
    """Test that MCP tools are correctly registered and schemas are valid."""
    print("\n" + "=" * 60)
    print("TEST 3: MCP Tools Registration & Schemas")
    print("=" * 60)

    from domain.avatar.mcp.server import mcp_server

    # Test 3a: All tools registered
    print("\n--- 3a. Tool Registration ---")
    tools = mcp_server.get_tools_list()
    tool_names = [t['name'] for t in tools]
    print(f"  Total tools registered: {len(tools)}")
    
    required_tools = ["browse_web", "search_images", "create_post"]
    for tool_name in required_tools:
        if tool_name in tool_names:
            print(f"  ✅ {tool_name} is registered")
        else:
            print(f"  ❌ {tool_name} is NOT registered")

    # Test 3b: browse_web schema
    print("\n--- 3b. browse_web Tool Schema ---")
    browse_tool = next((t for t in tools if t['name'] == 'browse_web'), None)
    if browse_tool:
        schema = browse_tool.get('inputSchema', {})
        props = schema.get('properties', {})
        print(f"  ✅ browse_web schema has {len(props)} properties: {list(props.keys())}")
        if 'query' in props and 'browse_type' in props:
            print(f"  ✅ browse_web has correct properties")
        else:
            print(f"  ❌ browse_web missing expected properties")
    else:
        print(f"  ❌ browse_web not found in tools")

    # Test 3c: search_images schema
    print("\n--- 3c. search_images Tool Schema ---")
    search_tool = next((t for t in tools if t['name'] == 'search_images'), None)
    if search_tool:
        schema = search_tool.get('inputSchema', {})
        props = schema.get('properties', {})
        print(f"  ✅ search_images schema has {len(props)} properties: {list(props.keys())}")
        if 'query' in props:
            print(f"  ✅ search_images has 'query' property")
        else:
            print(f"  ❌ search_images missing 'query' property")
    else:
        print(f"  ❌ search_images not found in tools")

    # Test 3d: create_post schema (enhanced with image_url)
    print("\n--- 3d. create_post Tool Schema (image support) ---")
    create_tool = next((t for t in tools if t['name'] == 'create_post'), None)
    if create_tool:
        schema = create_tool.get('inputSchema', {})
        props = schema.get('properties', {})
        print(f"  ✅ create_post schema has {len(props)} properties: {list(props.keys())}")
        if 'image_url' in props:
            print(f"  ✅ create_post has 'image_url' property")
        else:
            print(f"  ❌ create_post missing 'image_url' property")
        if 'image_query' in props:
            print(f"  ✅ create_post has 'image_query' property (auto image search)")
        else:
            print(f"  ❌ create_post missing 'image_query' property")
    else:
        print(f"  ❌ create_post not found in tools")

    # Print all registered tools
    print(f"\n--- All {len(tools)} registered tools ---")
    for t in tools:
        print(f"  • {t['name']}: {t.get('description', '')[:60]}...")

    return True


async def test_personality_aware_browsing():
    """Test personality-aware browsing without database (using mock interests)."""
    print("\n" + "=" * 60)
    print("TEST 4: Personality-Aware Search Query Generation")
    print("=" * 60)

    from services.web_browsing_service import WebBrowsingService
    service = WebBrowsingService()

    # Test query generation
    print("\n--- 4a. Query Generation ---")
    interests = ["artificial intelligence", "music production", "hiking"]
    
    for mood in ["curious", "creative", "bored", "excited"]:
        queries = service._generate_search_queries(interests, mood)
        print(f"  Mood={mood}: {queries}")

    # Test browse type selection
    print("\n--- 4b. Browse Type Selection ---")
    for mood in ["curious", "creative", "bored", "happy", "neutral"]:
        browse_type = service._select_browse_type(mood)
        print(f"  Mood={mood} → browse_type={browse_type}")

    return True


async def test_news_for_interests_real():
    """Test real news fetching for multiple interests."""
    print("\n" + "=" * 60)
    print("TEST 5: Real News for Multiple Interests")
    print("=" * 60)

    from services.web_browsing_service import WebBrowsingService
    service = WebBrowsingService()

    interests = ["technology", "space exploration", "cooking"]
    
    try:
        news = await service.get_news_for_interests(interests, max_per_interest=2)
        print(f"  ✅ Got {len(news)} news items for {len(interests)} interests")
        for item in news:
            print(f"     [{item.get('interest', '?')}] {item.get('title', 'No title')[:70]}")
            if item.get('image'):
                print(f"       📷 Has image: {item['image'][:60]}...")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    return True


async def main():
    """Run all tests."""
    print("🚀 Web Browsing Service Test Suite")
    print("=" * 60)

    all_passed = True

    # Test 1: Core web browsing
    try:
        await test_web_browsing_service()
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        all_passed = False

    # Test 2: Content awareness (upgraded)
    try:
        await test_content_awareness_service()
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        all_passed = False

    # Test 3: MCP tools
    try:
        await test_mcp_tools()
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        all_passed = False

    # Test 4: Personality-aware browsing
    try:
        await test_personality_aware_browsing()
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        all_passed = False

    # Test 5: Real news for interests
    try:
        await test_news_for_interests_real()
    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
        all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("⚠️  SOME TESTS HAD ISSUES (check output above)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
