#!/usr/bin/env python3
"""
Check avatars in PRODUCTION database for Sreejith, Rafseena, and Badusha
"""
import asyncio
import os
import sys
import json
import boto3

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from motor.motor_asyncio import AsyncIOMotorClient

# Users to check (their avatars are B11, Seven, _bLikker)
TARGET_USERS = ["Sreejith Sreekantan", "Rafseena Sadeed", "Badusha"]
EXPECTED_AVATAR_NAMES = ["B11", "Seven", "_bLikker"]


def get_production_mongo_url():
    """Get MongoDB URL from AWS Secrets Manager"""
    try:
        print("🔐 Retrieving MongoDB URL from AWS Secrets Manager...")
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name='us-west-1'
        )
        
        secret_response = client.get_secret_value(SecretId='2n1/mongodb/uri')
        
        if 'SecretString' in secret_response:
            secret = secret_response['SecretString']
            # The secret might be JSON or plain string
            try:
                secret_dict = json.loads(secret)
                return secret_dict.get('uri') or secret_dict.get('MONGO_URL')
            except json.JSONDecodeError:
                return secret
        else:
            raise Exception("Secret not found in expected format")
            
    except Exception as e:
        print(f"❌ Error retrieving secret: {e}")
        sys.exit(1)


async def main():
    """Check avatars in production database"""
    
    print("=" * 70)
    print("║  🔍 Checking PRODUCTION Avatars: B11, Seven, _bLikker              ║")
    print("=" * 70)
    
    # Get production MongoDB URL
    mongo_url = get_production_mongo_url()
    print("✅ MongoDB URL retrieved\n")
    
    # Extract database name from URL or use default
    # Typically: mongodb+srv://user:pass@cluster/database
    db_name = "neurallinks_local"  # Adjust if different in production
    
    # Connect to MongoDB
    print(f"🔌 Connecting to PRODUCTION MongoDB...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        await db.command("ping")
        print("✅ PRODUCTION MongoDB connected\n")
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
            print(f"❌ User '{user_name}' NOT FOUND in production database")
            continue
        
        all_users.append(user)
        
        # Display user details
        print(f"✅ User FOUND in PRODUCTION!")
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
                print(f"   Traits: {', '.join(traits[:5])}")
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
        
        # Check current state
        current_state = user.get('avatar_current_state', 'N/A')
        print(f"\n🎭 Current State: {current_state}")
        
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
    print("📊 PRODUCTION SUMMARY")
    print(f"{'='*70}")
    
    print(f"\n✅ Found {len(all_users)} out of {len(TARGET_USERS)} users in PRODUCTION")
    
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
    
    # List avatars with issues
    print(f"\n⚠️  Issues Found:")
    issues = []
    for i, user in enumerate(all_users):
        user_name = TARGET_USERS[i]
        expected = EXPECTED_AVATAR_NAMES[i]
        actual = user.get('avatar_name', 'NOT SET')
        
        if actual != expected:
            issues.append(f"   • {user_name}: Avatar name is '{actual}' but should be '{expected}'")
        
        if not user.get('avatar_autonomous', False):
            issues.append(f"   • {user_name}: Autonomy NOT enabled")
        
        if not user.get('avatar_character_profile'):
            issues.append(f"   • {user_name}: Character profile NOT set")
    
    if issues:
        for issue in issues:
            print(issue)
    else:
        print("   None! All avatars are properly configured ✅")
    
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
