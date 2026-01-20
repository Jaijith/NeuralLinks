#!/usr/bin/env python3
"""
Find Rafseena Sadeed (with spelling variations) and investigate activity failures
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


async def main():
    """Find Rafseena and check activity errors"""
    
    print("=" * 70)
    print("║  🔍 Finding Rafseena & Investigating Activity Failures             ║")
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
    
    # Search for Rafseena with various spellings
    print(f"{'='*70}")
    print("PART 1: Finding Rafseena Sadeed")
    print(f"{'='*70}\n")
    
    # Try different name variations
    name_variations = [
        "Rafseena Sadeed",
        "Rafseena",
        "Sadeed",
        "Rafeena",
        "Rafsina",
        "Seven"  # Try by avatar name
    ]
    
    print("Searching with multiple name variations...")
    found_users = []
    
    for name_var in name_variations:
        users = await db.users.find({
            "$or": [
                {"name": {"$regex": name_var, "$options": "i"}},
                {"username": {"$regex": name_var, "$options": "i"}},
                {"avatar_name": {"$regex": name_var, "$options": "i"}},
                {"email": {"$regex": name_var, "$options": "i"}}
            ]
        }).to_list(10)
        
        for user in users:
            if user not in found_users:
                found_users.append(user)
    
    if found_users:
        print(f"\n✅ Found {len(found_users)} potential matches:\n")
        
        for i, user in enumerate(found_users, 1):
            print(f"{i}. Name: {user.get('name', 'N/A')}")
            print(f"   Username: {user.get('username', 'N/A')}")
            print(f"   Email: {user.get('email', 'N/A')}")
            print(f"   Avatar Name: {user.get('avatar_name', 'N/A')}")
            print(f"   Autonomous: {user.get('avatar_autonomous', False)}")
            print(f"   Activity Level: {user.get('avatar_activity_level', 'N/A')}")
            print()
    else:
        print("\n❌ No users found matching 'Rafseena' variations")
        
        # List all users with avatar names containing "Seven"
        print("\n🔍 Searching for any avatar named 'Seven'...")
        seven_users = await db.users.find({
            "avatar_name": {"$regex": "Seven", "$options": "i"}
        }).to_list(10)
        
        if seven_users:
            print(f"Found {len(seven_users)} avatars named Seven:")
            for user in seven_users:
                print(f"   - {user.get('name', 'N/A')} ({user.get('email', 'N/A')})")
        else:
            print("   No avatars named 'Seven' found")
    
    # Now investigate activity failures
    print(f"\n{'='*70}")
    print("PART 2: Investigating Activity Failures")
    print(f"{'='*70}\n")
    
    # Check the three known users
    target_names = ["Sreejith Sreekantan", "Badusha"]
    target_avatars = ["_bLikker", "B11"]
    
    all_error_messages = []
    
    for i, user_name in enumerate(target_names):
        avatar_name = target_avatars[i]
        
        print(f"\n{'='*70}")
        print(f"Checking: {user_name} ({avatar_name})")
        print(f"{'='*70}")
        
        # Find user
        user = await db.users.find_one({
            "name": {"$regex": user_name, "$options": "i"}
        })
        
        if not user:
            print(f"❌ User not found")
            continue
        
        user_id = user.get('id')
        print(f"✅ User ID: {user_id}\n")
        
        # Get recent activities with errors
        activities = await db.autonomous_activities.find({
            "bot_id": user_id,
            "success": False
        }).sort([("timestamp", -1)]).limit(10).to_list(10)
        
        print(f"🔍 Recent Failed Activities: {len(activities)}")
        
        if activities:
            print("\nDetailed Error Analysis:")
            for j, activity in enumerate(activities, 1):
                action = activity.get('action_type', 'unknown')
                timestamp = activity.get('timestamp', 'Unknown')
                error = activity.get('error', 'No error message')
                details = activity.get('details', {})
                
                print(f"\n   {j}. Action: {action}")
                print(f"      Timestamp: {timestamp}")
                print(f"      Error: {error}")
                if details:
                    print(f"      Details: {json.dumps(details, indent=6)}")
                
                # Collect unique error messages
                if error not in all_error_messages and error != 'No error message':
                    all_error_messages.append(error)
        else:
            print("   ✅ No failed activities (or none recorded)")
        
        # Check user configuration issues
        print(f"\n🔧 Configuration Check:")
        
        # Check actions enabled
        actions = user.get('avatar_actions_enabled', {})
        enabled_count = sum(1 for v in actions.values() if v)
        print(f"   Actions enabled: {enabled_count}/4")
        if enabled_count < 4:
            disabled = [k for k, v in actions.items() if not v]
            print(f"   Disabled: {', '.join(disabled)}")
        
        # Check character profile
        character = user.get('avatar_character_profile', {})
        if not character:
            print(f"   ⚠️  Character profile NOT SET")
        else:
            print(f"   ✅ Character profile exists")
        
        # Check internal state
        internal = user.get('avatar_internal_state', {})
        if not internal:
            print(f"   ⚠️  Internal state NOT SET")
        else:
            print(f"   ✅ Internal state exists")
        
        # Check friend count
        friends_count = await db.friendships.count_documents({
            "$or": [
                {"user_id": user_id, "status": "accepted"},
                {"friend_id": user_id, "status": "accepted"}
            ]
        })
        print(f"   Friends: {friends_count}")
        
        # Check posts in feed
        posts_count = await db.posts.count_documents({
            "user_id": {"$ne": user_id}  # Posts from others
        })
        print(f"   Posts available in feed: {posts_count}")
    
    # Summary of errors
    print(f"\n{'='*70}")
    print("📊 ERROR SUMMARY")
    print(f"{'='*70}\n")
    
    if all_error_messages:
        print(f"Unique error messages found ({len(all_error_messages)}):\n")
        for i, error in enumerate(all_error_messages, 1):
            print(f"{i}. {error}\n")
    else:
        print("No error messages captured in failed activities")
    
    # Check if autonomous agent is running
    print("\n💡 RECOMMENDATIONS:")
    
    recent_activities = await db.autonomous_activities.find({}).sort([("timestamp", -1)]).limit(1).to_list(1)
    if recent_activities:
        last_activity = recent_activities[0].get('timestamp', 'Unknown')
        print(f"   • Last activity recorded: {last_activity}")
    else:
        print(f"   ⚠️  No activities found in database")
    
    print(f"   • Check if autonomous agent is running in production")
    print(f"   • Ensure all avatars have character profiles")
    print(f"   • Enable all actions for full autonomy")
    
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
