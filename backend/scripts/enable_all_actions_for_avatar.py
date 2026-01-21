#!/usr/bin/env python3
"""
Enable all actions for a specific avatar
Usage: python enable_all_actions_for_avatar.py <avatar_name>
Example: python enable_all_actions_for_avatar.py Dope
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


def get_production_mongo_url():
    """Get MongoDB URL from AWS Secrets Manager"""
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name='us-west-1'
        )
        
        secret_response = client.get_secret_value(SecretId='2n1/mongodb/uri')
        
        if 'SecretString' in secret_response:
            secret = secret_response['SecretString']
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


async def enable_all_actions(db, avatar_name):
    """Enable all actions for a specific avatar"""
    
    print(f"\n{'='*70}")
    print(f"🎯 Enabling All Actions for: {avatar_name}")
    print(f"{'='*70}")
    
    # Find avatar
    user = await db.users.find_one({
        "$or": [
            {"avatar_name": {"$regex": f"^{avatar_name}$", "$options": "i"}},
            {"name": {"$regex": avatar_name, "$options": "i"}}
        ]
    })
    
    if not user:
        print(f"\n❌ Avatar '{avatar_name}' not found in database")
        return False
    
    user_id = user.get('id')
    user_name = user.get('name', 'Unknown')
    avatar_name_actual = user.get('avatar_name', 'Unknown')
    
    print(f"\n✅ Avatar found!")
    print(f"   User ID: {user_id}")
    print(f"   Name: {user_name}")
    print(f"   Avatar Name: {avatar_name_actual}")
    
    # Check current actions
    current_actions = user.get('avatar_actions_enabled', {})
    
    print(f"\n📋 Current Action Status:")
    all_actions = [
        'create_posts',
        'like_posts',
        'comment_posts',
        'message_friends',
        'discover_profiles',
        'profile_viewed',
        'read_messages',
        'send_friend_requests',
        'accept_friend_requests'
    ]
    
    for action in all_actions:
        is_enabled = current_actions.get(action, False)
        status = "✅" if is_enabled else "❌"
        print(f"   {status} {action}: {is_enabled}")
    
    # Enable all actions
    print(f"\n🔧 Enabling all actions...")
    
    # Set actions in the correct format (object with boolean values)
    update_doc = {
        "$set": {
            "avatar_actions_enabled.create_posts": True,
            "avatar_actions_enabled.like_posts": True,
            "avatar_actions_enabled.comment_posts": True,
            "avatar_actions_enabled.message_friends": True,
            "avatar_actions_enabled.discover_profiles": True,
            "avatar_actions_enabled.profile_viewed": True,
            "avatar_actions_enabled.read_messages": True,
            "avatar_actions_enabled.send_friend_requests": True,
            "avatar_actions_enabled.accept_friend_requests": True,
            # Also set array format for compatibility
            "avatar_enabled_actions": all_actions
        }
    }
    
    result = await db.users.update_one(
        {"id": user_id},
        update_doc
    )
    
    if result.modified_count > 0:
        print(f"   ✅ Successfully updated!")
    else:
        print(f"   ℹ️  No changes needed (already configured)")
    
    # Verify the update
    updated_user = await db.users.find_one({"id": user_id})
    updated_actions = updated_user.get('avatar_actions_enabled', {})
    
    print(f"\n✅ Verification - Updated Action Status:")
    all_enabled = True
    for action in all_actions:
        is_enabled = updated_actions.get(action, False)
        status = "✅" if is_enabled else "❌"
        print(f"   {status} {action}: {is_enabled}")
        if not is_enabled:
            all_enabled = False
    
    if all_enabled:
        print(f"\n🎉 SUCCESS! All actions are now enabled for '{avatar_name_actual}'")
        return True
    else:
        print(f"\n⚠️  Warning: Some actions may not have been enabled properly")
        return False


async def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print("Usage: python enable_all_actions_for_avatar.py <avatar_name>")
        print("\nExample:")
        print("  python enable_all_actions_for_avatar.py Dope")
        print("  python enable_all_actions_for_avatar.py B11")
        sys.exit(1)
    
    avatar_name = sys.argv[1]
    
    print("=" * 70)
    print("║     🔧 ENABLE ALL ACTIONS FOR AVATAR                              ║")
    print("=" * 70)
    
    # Get production MongoDB URL
    mongo_url = get_production_mongo_url()
    
    # Connect to MongoDB
    print(f"\n🔌 Connecting to PRODUCTION MongoDB...")
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    try:
        await db.command("ping")
        print("✅ Connected\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)
    
    # Enable all actions
    success = await enable_all_actions(db, avatar_name)
    
    client.close()
    
    if success:
        print("\n✅ Done!")
    else:
        print("\n❌ Operation completed with warnings")


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
