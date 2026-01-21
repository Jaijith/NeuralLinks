#!/usr/bin/env python3
"""
Test MCP State-Aware Tools
Demonstrates how state drives MCP tool usage
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import boto3
import json
from motor.motor_asyncio import AsyncIOMotorClient

def get_mongo_url():
    """Get MongoDB URL from AWS Secrets Manager"""
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name='us-west-1')
    secret_response = client.get_secret_value(SecretId='2n1/mongodb/uri')
    secret = secret_response['SecretString']
    try:
        secret_dict = json.loads(secret)
        return secret_dict.get('uri') or secret_dict.get('MONGO_URL')
    except:
        return secret

async def test_mcp_tools():
    """Test the new MCP state-aware tools"""
    mongo_url = get_mongo_url()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    print("\n" + "="*70)
    print("║  Testing MCP State-Aware Tools")
    print("="*70)
    
    # Import MCP server
    from domain.avatar.mcp.server import mcp_server
    
    # Get an avatar
    user = await db.users.find_one({"avatar_name": "DigitalHunter"})
    if not user:
        print("❌ No avatar found")
        client.close()
        return
    
    avatar_id = user.get('id')
    avatar_name = user.get('avatar_name')
    
    print(f"\n✅ Testing with avatar: {avatar_name}")
    print(f"   User ID: {avatar_id}\n")
    
    # List all available tools
    print("=" * 70)
    print("ALL AVAILABLE MCP TOOLS:")
    print("=" * 70)
    all_tools = mcp_server.get_tools_list()
    for tool in all_tools:
        print(f"  • {tool['name']}: {tool['description']}")
    
    print(f"\n📊 Total tools: {len(all_tools)}")
    
    # Test 1: get_friend_activities
    print("\n\n" + "=" * 70)
    print("TEST 1: get_friend_activities Tool")
    print("=" * 70)
    print("Use Case: When avatar has high friend_focus\n")
    
    try:
        result = await mcp_server.call_tool(
            "get_friend_activities",
            avatar_id,
            {"hours_back": 48, "limit": 5}
        )
        
        if result.get('success'):
            print(f"✅ Tool executed successfully")
            print(f"   Found {result['count']} friend activities\n")
            
            activities = result.get('activities', [])
            for i, activity in enumerate(activities, 1):
                print(f"{i}. {activity['friend_name']}")
                print(f"   Type: {activity['type']}")
                print(f"   Summary: {activity['summary']}")
                print(f"   Engagement: {activity['likes']} likes, {activity['comments']} comments")
                if activity.get('is_popular'):
                    print(f"   🔥 POPULAR POST!")
                print()
        else:
            print(f"❌ Error: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 2: get_trending_topics
    print("\n" + "=" * 70)
    print("TEST 2: get_trending_topics Tool")
    print("=" * 70)
    print("Use Case: When avatar has high world_awareness\n")
    
    try:
        result = await mcp_server.call_tool(
            "get_trending_topics",
            avatar_id,
            {"category": "technology", "include_news_for_interests": True}
        )
        
        if result.get('success'):
            print(f"✅ Tool executed successfully")
            print(f"   Found {result['total_items']} items total\n")
            
            print("TRENDING TOPICS:")
            for i, topic in enumerate(result.get('trending_topics', []), 1):
                print(f"  {i}. {topic['title']}")
                print(f"     Category: {topic['category']}\n")
            
            if result.get('interest_news'):
                print("NEWS MATCHING INTERESTS:")
                for i, news in enumerate(result.get('interest_news', []), 1):
                    print(f"  {i}. {news['title']}")
                    print(f"     Related to: {news.get('interest', 'N/A')}\n")
        else:
            print(f"❌ Error: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 3: Demonstrate state-based selection
    print("\n" + "=" * 70)
    print("TEST 3: State-Based Tool Selection")
    print("=" * 70)
    
    from domain.avatar.state.internal_state import InternalState
    from domain.avatar.state.state_models import MoodState
    
    # Scenario 1: Social avatar
    print("\nSCENARIO 1: Social Mood (High Friend Focus)")
    print("-" * 70)
    state1 = InternalState()
    state1.adjust_mood(MoodState.SOCIAL)
    state1.social_desire = 0.9
    state1.voice_modulators.friend_focus = 0.9
    state1.voice_modulators.world_awareness = 0.3
    state1.update_voice_for_state()
    
    expr_ctx1 = state1.get_expression_context()
    print(f"Mood: {state1.mood.value}")
    print(f"Friend Focus: {state1.voice_modulators.friend_focus:.2f}")
    print(f"World Awareness: {state1.voice_modulators.world_awareness:.2f}")
    print(f"\nShould talk about friends: {expr_ctx1['should_talk_about_friends']}")
    print(f"Should reference world: {expr_ctx1['should_reference_world']}")
    print(f"\nRECOMMENDED MCP TOOLS:")
    if expr_ctx1['should_talk_about_friends']:
        print(f"  ✅ get_friend_activities (HIGH PRIORITY)")
    else:
        print(f"  ❌ get_friend_activities (skip)")
    
    if expr_ctx1['should_reference_world']:
        print(f"  ✅ get_trending_topics (HIGH PRIORITY)")
    else:
        print(f"  ❌ get_trending_topics (skip)")
    
    # Scenario 2: Curious avatar
    print("\n\nSCENARIO 2: Curious Mood (High World Awareness)")
    print("-" * 70)
    state2 = InternalState()
    state2.adjust_mood(MoodState.CURIOUS)
    state2.voice_modulators.friend_focus = 0.3
    state2.voice_modulators.world_awareness = 0.9
    state2.update_voice_for_state()
    
    expr_ctx2 = state2.get_expression_context()
    print(f"Mood: {state2.mood.value}")
    print(f"Friend Focus: {state2.voice_modulators.friend_focus:.2f}")
    print(f"World Awareness: {state2.voice_modulators.world_awareness:.2f}")
    print(f"\nShould talk about friends: {expr_ctx2['should_talk_about_friends']}")
    print(f"Should reference world: {expr_ctx2['should_reference_world']}")
    print(f"\nRECOMMENDED MCP TOOLS:")
    if expr_ctx2['should_talk_about_friends']:
        print(f"  ✅ get_friend_activities (HIGH PRIORITY)")
    else:
        print(f"  ❌ get_friend_activities (skip)")
    
    if expr_ctx2['should_reference_world']:
        print(f"  ✅ get_trending_topics (HIGH PRIORITY)")
    else:
        print(f"  ❌ get_trending_topics (skip)")
    
    # Summary
    print("\n\n" + "=" * 70)
    print("║  Summary")
    print("=" * 70)
    print("""
✅ MCP Tools Created:
   - get_friend_activities: Fetches friend posts & interactions
   - get_trending_topics: Fetches news & trending content

✅ State-Aware Selection:
   - Social mood → Use get_friend_activities
   - Curious mood → Use get_trending_topics
   - State determines which tools to call

✅ Proper Architecture:
   - Tools discoverable through MCP server
   - Permission-based access control
   - Standardized MCP protocol

✅ Integration:
   - Agent reads internal state
   - Checks friend_focus & world_awareness
   - Calls appropriate MCP tools
   - Uses retrieved content for posts
    """)
    
    client.close()


if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
