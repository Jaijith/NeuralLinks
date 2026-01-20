#!/usr/bin/env python3
"""
Check avatars for specific users
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

# Users to check (their avatars are B11, Seven, _bLikker)
TARGET_USERS = ["Sreejith Sreekantan", "Rafseena Sadeed", "Badusha"]
EXPECTED_AVATAR_NAMES = ["B11", "Seven", "_bLikker"]


async def main():
    """Check avatars for Sreejith, Rafseena, and Badusha"""
    
    print("=" * 70)
    print("║  🔍 Checking Avatars: B11, Seven, _bLikker                        ║")
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
    
    all_users = []
    
    for i, user_name in enumerate(TARGET_USERS):
        expected_avatar = EXPECTED_AVATAR_NAMES[i]
        print(f"\n{'='*70}")
        print(f"Checking: {user_name} (Avatar should be: {expected_avatar})")
        print(f"{'='*70}")
        
        # Find user by name
        user = await db.users.find_one({
            "$or": [
                {"name": {"$regex": user_name, "$options": "i"}},
                {"username": {"$regex": user_name.split()[0], "$options": "i"}}
            ]
        })
        
        if not user:
            print(f"❌ User '{user_name}' NOT FOUND in database")
            continue
        
        all_users.append(user)
        
        # Display user details
        print(f"✅ User FOUND!")
        print(f"\n📋 User Details:")
        print(f"   ID: {user.get('id', 'N/A')}")
        print(f"   Name: {user.get('name', 'N/A')}")
        print(f"   Username: {user.get('username', 'N/A')}")
        print(f"   Email: {user.get('email', 'N/A')}")
        
        # Avatar details
        avatar_name = user.get('avatar_name', 'NOT SET')
        print(f"\n🤖 Avatar Details:")
        print(f"   Avatar Name: {avatar_name}")
        
        if avatar_name == expected_avatar:
            print(f"   ✅ Avatar name matches expected: {expected_avatar}")
        elif avatar_name == 'NOT SET':
            print(f"   ⚠️  Avatar name NOT SET (expected: {expected_avatar})")
        else:
            print(f"   ⚠️  Avatar name mismatch! Got '{avatar_name}', expected '{expected_avatar}'")
        
        print(f"   Autonomous: {user.get('avatar_autonomous', False)}")
        print(f"   Activity Level: {user.get('avatar_activity_level', 'N/A')}")
        
        # Check enabled actions
        actions_enabled = user.get('avatar_actions_enabled', {})
        print(f"\n🎯 Enabled Actions:")
        print(f"   create_posts: {actions_enabled.get('create_posts', False)}")
        print(f"   like_post: {actions_enabled.get('like_post', False)}")
        print(f"   comment_on_post: {actions_enabled.get('comment_on_post', False)}")
        print(f"   message_friend: {actions_enabled.get('message_friend', False)}")
        
        # Check character profile
        character = user.get('avatar_character_profile', {})
        if character:
            print(f"\n👤 Character Profile:")
            print(f"   Archetype: {character.get('archetype', 'N/A')}")
            traits = character.get('personality_traits', [])
            if traits:
                print(f"   Traits: {', '.join(traits)}")
            interests = character.get('interests', [])
            if interests:
                print(f"   Interests: {', '.join(interests[:5])}")
        else:
            print(f"\n👤 Character Profile: NOT SET")
        
        # Check internal state
        internal_state = user.get('avatar_internal_state', {})
        if internal_state:
            print(f"\n🧠 Internal State:")
            print(f"   Energy: {internal_state.get('energy_level', 'N/A')}")
            print(f"   Social Desire: {internal_state.get('social_desire', 'N/A')}")
            print(f"   Mood: {internal_state.get('mood', 'N/A')}")
        
        # Check recent posts
        user_id = user.get('id')
        recent_posts = await db.posts.find({
            "user_id": user_id,
            "post_type": "avatar"
        }).sort([("created_at", -1)]).limit(5).to_list(5)
        
        print(f"\n📝 Recent Avatar Posts: {len(recent_posts)}")
        if recent_posts:
            for j, post in enumerate(recent_posts, 1):
                text = post.get('text', '')[:60]
                created = post.get('created_at', 'Unknown')
                print(f"   {j}. {text}...")
                print(f"      Created: {created}")
        else:
            print("   ⚠️  No posts yet")
        
        # Check recent activities
        recent_activities = await db.autonomous_activities.find({
            "bot_id": user_id
        }).sort([("timestamp", -1)]).limit(5).to_list(5)
        
        print(f"\n🤖 Recent Activities: {len(recent_activities)}")
        if recent_activities:
            for j, activity in enumerate(recent_activities, 1):
                action = activity.get('action_type', 'unknown')
                timestamp = activity.get('timestamp', 'Unknown')
                success = activity.get('success', False)
                status = "✅" if success else "❌"
                print(f"   {j}. {status} {action} ({timestamp})")
        else:
            print("   ⚠️  No activities recorded yet")
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY")
    print(f"{'='*70}")
    
    print(f"\n✅ Found {len(all_users)} out of {len(TARGET_USERS)} users")
    
    with_avatar_name = sum(1 for u in all_users if u.get('avatar_name'))
    print(f"🏷️  {with_avatar_name} have set avatar names")
    
    autonomous = sum(1 for u in all_users if u.get('avatar_autonomous', False))
    print(f"🤖 {autonomous} have autonomy enabled")
    
    with_character = sum(1 for u in all_users if u.get('avatar_character_profile'))
    print(f"👤 {with_character} have character profiles")
    
    with_posts = 0
    for user in all_users:
        count = await db.posts.count_documents({
            "user_id": user.get('id'),
            "post_type": "avatar"
        })
        if count > 0:
            with_posts += 1
    
    print(f"📝 {with_posts} avatars have created posts")
    
    # Check if autonomous agent is running
    print(f"\n💡 TIP: For avatars to act autonomously, make sure the")
    print(f"    autonomous agent system is running:")
    print(f"    python scripts/run_autonomous_agents.py")
    
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
