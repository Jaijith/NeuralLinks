"""
Trigger Immediate Bot Activity
Forces bots to post and chat NOW for testing
"""

import asyncio
import os
import random
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncAzureOpenAI
from autonomous_manager import AutonomousActivityManager
from intelligent_avatar import IntelligentAvatar
from graph_rag import GraphRAG

load_dotenv()

# Database connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Azure OpenAI
llm_client = AsyncAzureOpenAI(
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")
)

deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


async def trigger_activity(num_posts=5, num_conversations=2):
    """Trigger immediate bot activity"""
    
    print("=" * 70)
    print("🚀 TRIGGERING IMMEDIATE BOT ACTIVITY")
    print("=" * 70)
    
    # Initialize components
    graph_rag = GraphRAG(db)
    intelligent_avatar = IntelligentAvatar(db, llm_client, deployment, graph_rag)
    manager = AutonomousActivityManager(db, intelligent_avatar)
    
    # Get all bots
    bots = await db.users.find(
        {"is_bot": True, "archetype": {"$exists": True}},
        {"_id": 0}
    ).to_list(100)
    
    if not bots:
        print("❌ No bots found with archetypes. Run test_autonomous_system.py first!")
        return
    
    print(f"\n✅ Found {len(bots)} configured bots\n")
    
    # Force reset next_post_time for all bots
    print("🔄 Resetting bot timers...")
    now = datetime.now(timezone.utc)
    await db.users.update_many(
        {"is_bot": True},
        {"$set": {"next_post_time": now}}
    )
    
    # Generate Posts
    print(f"\n📝 Generating {num_posts} posts...")
    print("-" * 70)
    
    random.shuffle(bots)
    for i, bot in enumerate(bots[:num_posts], 1):
        await manager._generate_bot_post(bot)
        await asyncio.sleep(2)  # Small delay between posts
    
    # Start Conversations
    print(f"\n\n💬 Starting {num_conversations} conversations...")
    print("-" * 70)
    
    random.shuffle(bots)
    for i, bot in enumerate(bots[:num_conversations], 1):
        await manager._start_bot_conversation(bot)
        await asyncio.sleep(3)  # Small delay between conversations
    
    # Show results
    print("\n\n" + "=" * 70)
    print("✅ ACTIVITY COMPLETE!")
    print("=" * 70)
    
    stats = await manager.get_activity_stats()
    print(f"\n📊 Statistics:")
    print(f"   Total activities: {stats['total_activities']}")
    print(f"   API calls used: {stats['api_calls_used']}")
    for activity_type, count in stats['activities_by_type'].items():
        print(f"   {activity_type}: {count}")
    
    # Show sample posts
    print(f"\n\n📝 Sample Posts:")
    print("-" * 70)
    
    bots_with_posts = await db.users.find(
        {"is_bot": True, "avatar_posts": {"$exists": True, "$ne": []}},
        {"_id": 0, "avatar_name": 1, "name": 1, "avatar_posts": 1, "archetype": 1}
    ).sort("last_activity", -1).limit(5).to_list(5)
    
    for bot in bots_with_posts:
        name = bot.get('avatar_name', bot.get('name'))
        archetype = bot.get('archetype', 'unknown')
        posts = bot.get('avatar_posts', [])
        
        if posts:
            latest_post = posts[-1]
            content = latest_post.get('content', '')
            
            print(f"\n🤖 {name} ({archetype}):")
            print(f"   \"{content}\"")
    
    # Show conversations
    print(f"\n\n💬 Conversations:")
    print("-" * 70)
    
    conversations = await db.avatar_conversations.find(
        {},
        {"_id": 0}
    ).sort("started_at", -1).limit(3).to_list(3)
    
    for i, conv in enumerate(conversations, 1):
        messages = conv.get('messages', [])
        topic = conv.get('topic', 'general')
        
        print(f"\nConversation {i} - Topic: {topic}")
        
        if messages:
            for msg in messages:
                sender = msg.get('sender_name', 'Unknown')
                content = msg.get('content', '')
                print(f"   {sender}: \"{content}\"")
                print()
    
    print("\n" + "=" * 70)
    print("🎉 DONE! Check your frontend to see the activity!")
    print("=" * 70)
    print("\n💡 Refresh your browser at: http://localhost:3000")
    print("   Toggle to Maya World (✨) to see all the bot posts and conversations!")
    print()


if __name__ == '__main__':
    import sys
    
    num_posts = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    num_conversations = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    print(f"\n🎯 Configuration:")
    print(f"   Posts to generate: {num_posts}")
    print(f"   Conversations to start: {num_conversations}")
    print()
    
    asyncio.run(trigger_activity(num_posts, num_conversations))


