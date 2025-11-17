"""
Test script to run a single cycle for all avatars and check if they're posting
"""

import asyncio
import os
import sys

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
from domain.avatar.manager import SimpleAgentManager

# Load environment variables
load_dotenv()

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "neurallinks_local"

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_SERVICE")
if AZURE_OPENAI_ENDPOINT and not AZURE_OPENAI_ENDPOINT.startswith('https://'):
    AZURE_OPENAI_ENDPOINT = f"https://{AZURE_OPENAI_ENDPOINT}.openai.azure.com"

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
AZURE_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-02-15-preview")


async def main():
    """Run a single cycle and check for posts"""
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🧪 Test Avatar Posting - Single Cycle                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Check Azure OpenAI configuration
    if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT]):
        print("❌ ERROR: Azure OpenAI configuration incomplete!")
        print("\nRequired environment variables:")
        print("  - AZURE_OPENAI_SERVICE")
        print("  - AZURE_OPENAI_API_KEY")
        print("  - AZURE_OPENAI_CHATGPT_DEPLOYMENT")
        sys.exit(1)
    
    # Connect to MongoDB
    print("🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        await db.command("ping")
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        sys.exit(1)
    
    # Check current posts count
    print("\n📊 Checking current avatar posts...")
    posts_before = await db.posts.count_documents({"post_type": "avatar"})
    print(f"   Posts before: {posts_before}")
    
    # Initialize Azure OpenAI client
    print("\n🤖 Initializing Azure OpenAI...")
    llm_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_API_VERSION
    )
    print("✅ Azure OpenAI initialized")
    
    # Initialize agent manager
    print("\n🚀 Initializing agent manager...")
    manager = SimpleAgentManager(
        db=db,
        llm_client=llm_client,
        deployment=AZURE_OPENAI_DEPLOYMENT
    )
    
    # Initialize all bot agents
    await manager.initialize_agents()
    
    if not manager.agents:
        print("❌ No bot agents found!")
        client.close()
        sys.exit(1)
    
    print(f"✅ Found {len(manager.agents)} agents")
    
    # Show agent details
    print("\n📋 Agent Details:")
    for agent in manager.agents[:5]:
        name = agent.bot.get('avatar_name') or agent.bot.get('name', 'Unknown')
        activity = agent.bot.get('avatar_activity_level', 'unknown')
        autonomous = agent.bot.get('avatar_autonomous', False)
        actions = agent.bot.get('avatar_actions_enabled', {})
        can_post = actions.get('create_posts', False)
        print(f"   - {name}: activity={activity}, autonomous={autonomous}, can_post={can_post}")
    
    # Run a single cycle
    print("\n🔄 Running single cycle for all agents...")
    print("=" * 60)
    
    await manager.run_single_cycle()
    
    print("=" * 60)
    
    # Check posts after
    print("\n📊 Checking posts after cycle...")
    posts_after = await db.posts.count_documents({"post_type": "avatar"})
    new_posts = posts_after - posts_before
    print(f"   Posts after: {posts_after}")
    print(f"   New posts created: {new_posts}")
    
    if new_posts > 0:
        print("\n✅ SUCCESS! New posts were created!")
        print("\n📝 Recent avatar posts:")
        recent_posts = await db.posts.find({
            "post_type": "avatar"
        }).sort([("created_at", -1)]).limit(new_posts).to_list(new_posts)
        
        for i, post in enumerate(recent_posts, 1):
            user_id = post.get('user_id', 'Unknown')
            text = post.get('text', '')[:80]
            created = post.get('created_at', 'Unknown')
            # Get avatar name
            user = await db.users.find_one({"id": user_id})
            avatar_name = user.get('avatar_name') if user else 'Unknown'
            print(f"   {i}. {avatar_name}: {text}...")
    else:
        print("\n⚠️  No new posts were created in this cycle")
        print("\n   Possible reasons:")
        print("   - Agents may have hit rate limits")
        print("   - Not enough time passed since last post")
        print("   - create_posts action may not be enabled")
        print("   - Activity level may be too low")
    
    # Check activities
    print("\n📊 Recent activities:")
    recent_activities = await db.autonomous_activities.find().sort([("timestamp", -1)]).limit(10).to_list(10)
    print(f"   Found {len(recent_activities)} recent activities")
    for activity in recent_activities[:5]:
        action = activity.get('action_type', 'unknown')
        bot_name = activity.get('bot_name', 'Unknown')
        timestamp = activity.get('timestamp', 'Unknown')
        print(f"   - {bot_name}: {action} ({timestamp})")
    
    client.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

