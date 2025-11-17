"""
Script to set all avatars to 'hypo' activity level and enable autonomy
"""

import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Load environment variables
load_dotenv()

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "neurallinks_local"


async def main():
    """Set all avatars to hypo activity level"""
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🔧 Set All Avatars to Hypo Activity Level              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Connect to MongoDB
    print("🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Test connection
    try:
        await db.command("ping")
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        sys.exit(1)
    
    # Find all users with avatars
    print("\n🔍 Finding all users with avatars...")
    users_with_avatars = await db.users.find({
        "$or": [
            {"avatar_name": {"$exists": True, "$ne": None}},
            {"avatar_autonomous": True}
        ]
    }).to_list(1000)
    
    print(f"📊 Found {len(users_with_avatars)} users with avatars")
    
    # Update all to hypo activity level and enable autonomy
    print("\n🔄 Updating all avatars to 'hypo' activity level...")
    
    update_result = await db.users.update_many(
        {
            "$or": [
                {"avatar_name": {"$exists": True, "$ne": None}},
                {"avatar_autonomous": True}
            ]
        },
        {
            "$set": {
                "avatar_activity_level": "hypo",
                "avatar_autonomous": True
            }
        }
    )
    
    print(f"✅ Updated {update_result.modified_count} avatars")
    
    # Verify updates
    print("\n🔍 Verifying updates...")
    hypo_avatars = await db.users.find({
        "avatar_activity_level": "hypo",
        "avatar_autonomous": True
    }).to_list(1000)
    
    print(f"✅ Verified: {len(hypo_avatars)} avatars now have 'hypo' activity level and autonomy enabled")
    
    # Show some examples
    if hypo_avatars:
        print("\n📋 Sample avatars updated:")
        for i, avatar in enumerate(hypo_avatars[:5], 1):
            name = avatar.get('avatar_name') or avatar.get('name', 'Unknown')
            print(f"   {i}. {name} (ID: {avatar.get('id', 'N/A')[:20]}...)")
    
    # Check recent posts
    print("\n📊 Checking recent posts from avatars...")
    recent_posts = await db.posts.find({
        "post_type": "avatar"
    }).sort([("created_at", -1)]).limit(10).to_list(10)
    
    print(f"   Found {len(recent_posts)} recent avatar posts")
    if recent_posts:
        print("\n   Recent avatar posts:")
        for post in recent_posts[:5]:
            user_id = post.get('user_id', 'Unknown')
            text = post.get('text', '')[:50]
            created = post.get('created_at', 'Unknown')
            print(f"   - {user_id[:20]}...: {text}... ({created})")
    else:
        print("   ⚠️  No avatar posts found yet")
    
    client.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

