#!/usr/bin/env python3
"""
Check if specific new avatars are active
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

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

# New avatars to check
NEW_AVATARS = ["B11", "Seven", "_bLikker"]


async def main():
    """Check if new avatars are active"""
    
    print("=" * 70)
    print("║     🔍 Checking New Avatars: B11, Seven, _bLikker                  ║")
    print("=" * 70)
    
    # Connect to MongoDB
    print("\n🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        await db.command("ping")
        print("✅ MongoDB connected\n")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        sys.exit(1)
    
    # Check each avatar
    for avatar_name in NEW_AVATARS:
        print(f"\n{'='*70}")
        print(f"Checking: {avatar_name}")
        print(f"{'='*70}")
        
        # Find avatar by username or avatar_name
        avatar = await db.users.find_one({
            "$or": [
                {"username": avatar_name},
                {"avatar_name": avatar_name}
            ]
        })
        
        if not avatar:
            print(f"❌ Avatar '{avatar_name}' NOT FOUND in database")
            continue
        
        # Display avatar details
        print(f"✅ Avatar FOUND!")
        print(f"\n📋 Details:")
        print(f"   ID: {avatar.get('id', 'N/A')}")
        print(f"   Username: {avatar.get('username', 'N/A')}")
        print(f"   Avatar Name: {avatar.get('avatar_name', 'N/A')}")
        print(f"   Is Bot: {avatar.get('is_bot', False)}")
        print(f"   Autonomous: {avatar.get('avatar_autonomous', False)}")
        print(f"   Activity Level: {avatar.get('avatar_activity_level', 'N/A')}")
        
        # Check enabled actions
        actions_enabled = avatar.get('avatar_actions_enabled', {})
        print(f"\n🎯 Enabled Actions:")
        print(f"   create_posts: {actions_enabled.get('create_posts', False)}")
        print(f"   like_post: {actions_enabled.get('like_post', False)}")
        print(f"   comment_on_post: {actions_enabled.get('comment_on_post', False)}")
        print(f"   message_friend: {actions_enabled.get('message_friend', False)}")
        
        # Check character profile
        character = avatar.get('avatar_character_profile', {})
        if character:
            print(f"\n👤 Character Profile:")
            print(f"   Archetype: {character.get('archetype', 'N/A')}")
            print(f"   Traits: {character.get('personality_traits', [])}")
            print(f"   Interests: {character.get('interests', [])}")
        
        # Check recent posts
        avatar_id = avatar.get('id')
        recent_posts = await db.posts.find({
            "user_id": avatar_id,
            "post_type": "avatar"
        }).sort([("created_at", -1)]).limit(5).to_list(5)
        
        print(f"\n📝 Recent Posts: {len(recent_posts)}")
        if recent_posts:
            for i, post in enumerate(recent_posts, 1):
                text = post.get('text', '')[:60]
                created = post.get('created_at', 'Unknown')
                print(f"   {i}. {text}...")
                print(f"      Created: {created}")
        else:
            print("   ⚠️  No posts yet")
        
        # Check recent activities
        recent_activities = await db.autonomous_activities.find({
            "bot_id": avatar_id
        }).sort([("timestamp", -1)]).limit(5).to_list(5)
        
        print(f"\n🤖 Recent Activities: {len(recent_activities)}")
        if recent_activities:
            for i, activity in enumerate(recent_activities, 1):
                action = activity.get('action_type', 'unknown')
                timestamp = activity.get('timestamp', 'Unknown')
                success = activity.get('success', False)
                status = "✅" if success else "❌"
                print(f"   {i}. {status} {action} ({timestamp})")
        else:
            print("   ⚠️  No activities recorded yet")
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY")
    print(f"{'='*70}")
    
    all_avatars = []
    for avatar_name in NEW_AVATARS:
        avatar = await db.users.find_one({
            "$or": [
                {"username": avatar_name},
                {"avatar_name": avatar_name}
            ]
        })
        if avatar:
            all_avatars.append(avatar)
    
    print(f"\n✅ Found {len(all_avatars)} out of {len(NEW_AVATARS)} avatars")
    
    active_count = sum(1 for a in all_avatars if a.get('avatar_autonomous', False))
    print(f"🤖 {active_count} avatars have autonomy enabled")
    
    with_posts = 0
    for avatar in all_avatars:
        posts = await db.posts.count_documents({
            "user_id": avatar.get('id'),
            "post_type": "avatar"
        })
        if posts > 0:
            with_posts += 1
    
    print(f"📝 {with_posts} avatars have created posts")
    
    client.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
