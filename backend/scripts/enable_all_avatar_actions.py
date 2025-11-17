"""
Enable all avatar actions (especially create_posts) for all avatars
"""

import asyncio
import os
import sys

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
    """Enable all actions for all avatars"""
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🔧 Enable All Avatar Actions                            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
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
    
    # Find all avatars
    print("\n🔍 Finding all avatars...")
    avatars = await db.users.find({
        "$or": [
            {"avatar_autonomous": True},
            {"avatar_name": {"$exists": True, "$ne": None}}
        ]
    }).to_list(1000)
    
    print(f"📊 Found {len(avatars)} avatars")
    
    # Default actions to enable
    default_actions = {
        "like_posts": True,
        "comment_posts": True,
        "create_posts": True,
        "send_friend_requests": True,
        "accept_friend_requests": True,
        "message_friends": True,
        "discover_profiles": True,
        "share_posts": False  # Keep share_posts disabled for now
    }
    
    # Update all avatars
    print("\n🔄 Enabling all actions for all avatars...")
    updated_count = 0
    
    for avatar in avatars:
        avatar_id = avatar.get('id')
        avatar_name = avatar.get('avatar_name') or avatar.get('name', 'Unknown')
        
        # Get current actions or use defaults
        current_actions = avatar.get('avatar_actions_enabled', {})
        
        # Merge with defaults (keep existing True values, set missing ones)
        updated_actions = {**default_actions}
        for key, value in current_actions.items():
            if key in updated_actions and value is True:
                updated_actions[key] = True
        
        # Update avatar
        await db.users.update_one(
            {"id": avatar_id},
            {
                "$set": {
                    "avatar_actions_enabled": updated_actions,
                    "avatar_autonomous": True,
                    "avatar_activity_level": "hypo"
                }
            }
        )
        
        updated_count += 1
        if updated_count <= 5:
            print(f"   ✅ {avatar_name}: Enabled {sum(1 for v in updated_actions.values() if v)} actions")
    
    print(f"\n✅ Updated {updated_count} avatars")
    
    # Verify
    print("\n🔍 Verifying updates...")
    avatars_with_posts = await db.users.find({
        "avatar_actions_enabled.create_posts": True
    }).to_list(1000)
    
    print(f"✅ Verified: {len(avatars_with_posts)} avatars now have create_posts enabled")
    
    client.close()
    print("\n✅ Done! All avatars now have all actions enabled.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

