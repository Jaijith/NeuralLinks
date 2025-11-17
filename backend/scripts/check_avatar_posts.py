"""
Check avatar posts and activity status
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "neurallinks_local"


async def main():
    """Check avatar posts and activity"""
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     📊 Check Avatar Posts and Activity                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Connect to MongoDB
    print("🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        await db.command("ping")
        print("✅ MongoDB connected\n")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        sys.exit(1)
    
    # Check avatars
    print("📋 Checking avatars...")
    avatars = await db.users.find({
        "$or": [
            {"avatar_autonomous": True},
            {"avatar_name": {"$exists": True, "$ne": None}}
        ]
    }).to_list(1000)
    
    print(f"   Found {len(avatars)} avatars")
    
    # Check activity levels
    activity_levels = {}
    for avatar in avatars:
        level = avatar.get('avatar_activity_level', 'not_set')
        activity_levels[level] = activity_levels.get(level, 0) + 1
    
    print("\n📊 Activity Levels:")
    for level, count in activity_levels.items():
        print(f"   {level}: {count}")
    
    # Check enabled actions
    print("\n📊 Enabled Actions:")
    create_posts_enabled = 0
    for avatar in avatars:
        actions = avatar.get('avatar_actions_enabled', {})
        if actions.get('create_posts', False):
            create_posts_enabled += 1
    
    print(f"   create_posts enabled: {create_posts_enabled}/{len(avatars)}")
    
    # Check recent posts (last 24 hours)
    print("\n📊 Recent Posts (last 24 hours):")
    one_day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    
    recent_posts = await db.posts.find({
        "post_type": "avatar",
        "created_at": {"$gte": one_day_ago}
    }).sort([("created_at", -1)]).to_list(100)
    
    print(f"   Found {len(recent_posts)} posts in last 24 hours")
    
    if recent_posts:
        print("\n   Recent posts:")
        for i, post in enumerate(recent_posts[:10], 1):
            user_id = post.get('user_id', 'Unknown')
            text = post.get('text', '')[:60]
            created = post.get('created_at', 'Unknown')
            
            # Get avatar name
            user = await db.users.find_one({"id": user_id})
            avatar_name = user.get('avatar_name') if user else 'Unknown'
            
            print(f"   {i}. {avatar_name}: {text}...")
            print(f"      Created: {created}")
    else:
        print("   ⚠️  No posts in last 24 hours")
    
    # Check all-time posts
    print("\n📊 All-Time Avatar Posts:")
    total_posts = await db.posts.count_documents({"post_type": "avatar"})
    print(f"   Total: {total_posts}")
    
    # Check recent activities
    print("\n📊 Recent Activities (last 24 hours):")
    recent_activities = await db.autonomous_activities.find({
        "timestamp": {"$gte": one_day_ago}
    }).sort([("timestamp", -1)]).to_list(50)
    
    print(f"   Found {len(recent_activities)} activities")
    
    if recent_activities:
        activity_types = {}
        for activity in recent_activities:
            action = activity.get('action_type', 'unknown')
            activity_types[action] = activity_types.get(action, 0) + 1
        
        print("\n   Activity breakdown:")
        for action, count in activity_types.items():
            print(f"      {action}: {count}")
        
        print("\n   Recent activity details:")
        for i, activity in enumerate(recent_activities[:5], 1):
            bot_name = activity.get('bot_name', 'Unknown')
            action = activity.get('action_type', 'unknown')
            timestamp = activity.get('timestamp', 'Unknown')
            print(f"   {i}. {bot_name}: {action} ({timestamp})")
    else:
        print("   ⚠️  No activities in last 24 hours")
        print("\n   💡 Tip: The autonomous agent system needs to be running")
        print("      to create posts. Run: python scripts/run_autonomous_agents.py")
    
    # Check last post times per avatar
    print("\n📊 Last Post Time by Avatar:")
    for avatar in avatars[:10]:
        avatar_id = avatar.get('id')
        avatar_name = avatar.get('avatar_name') or avatar.get('name', 'Unknown')
        
        last_post = await db.posts.find_one(
            {"user_id": avatar_id, "post_type": "avatar"},
            sort=[("created_at", -1)]
        )
        
        if last_post:
            created = last_post.get('created_at', 'Unknown')
            print(f"   {avatar_name}: {created}")
        else:
            print(f"   {avatar_name}: Never posted")
    
    client.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

