"""
Ensure ALL users have complete avatar configuration:
- State-aware agent (all 8 layers)
- All actions enabled by default
- Autonomy enabled
- Proper archetype and interests
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import boto3
import json
from motor.motor_asyncio import AsyncIOMotorClient
from domain.avatar.initialization import initialize_state_aware_agent

def get_mongo_url():
    """Get MongoDB URL from AWS Secrets Manager"""
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name='us-west-1')
    secret_response = client.get_secret_value(SecretId='2n1/mongodb/uri')
    secret = secret_response['SecretString']
    try:
        secret_dict = json.loads(secret)
        return secret_dict.get('uri') or secret_dict.get('MONGO_URL')
    except:
        return secret

async def main():
    """Ensure all users have complete configuration"""
    mongo_url = get_mongo_url()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    print("\n" + "="*70)
    print("║  🔧 Ensuring ALL Users Have Complete Avatar Configuration")
    print("="*70 + "\n")
    
    # Find ALL non-bot users
    all_users = await db.users.find(
        {"is_bot": {"$ne": True}},
        {"id": 1, "name": 1, "email": 1, "avatar_name": 1, 
         "avatar_autonomous": 1, "avatar_enabled_actions": 1, 
         "avatar_character_profile": 1}
    ).to_list(1000)
    
    print(f"📊 Found {len(all_users)} real users\n")
    
    users_needing_init = []
    users_needing_fixes = []
    users_good = []
    
    for user in all_users:
        user_id = user.get('id')
        name = user.get('name', 'Unknown')
        avatar_name = user.get('avatar_name', 'N/A')
        
        # Check what's missing/wrong
        issues = []
        
        if not user.get('avatar_character_profile'):
            issues.append("No character profile")
        
        if not user.get('avatar_autonomous'):
            issues.append("Autonomy disabled")
        
        enabled_actions = user.get('avatar_enabled_actions', [])
        if not enabled_actions or len(enabled_actions) == 0:
            issues.append("No actions enabled")
        elif len(enabled_actions) < 7:
            issues.append(f"Only {len(enabled_actions)}/7 actions enabled")
        
        if issues:
            if not user.get('avatar_character_profile'):
                users_needing_init.append((user_id, name, avatar_name, issues))
            else:
                users_needing_fixes.append((user_id, name, avatar_name, issues))
        else:
            users_good.append((user_id, name, avatar_name))
    
    print("="*70)
    print("📋 USER STATUS:")
    print("="*70)
    print(f"✅ Fully configured: {len(users_good)}")
    print(f"🔧 Need fixes: {len(users_needing_fixes)}")
    print(f"🆕 Need full initialization: {len(users_needing_init)}")
    print()
    
    # Show users needing full initialization
    if users_needing_init:
        print("🆕 Users Needing Full Initialization:")
        for user_id, name, avatar_name, issues in users_needing_init:
            print(f"   • {name} ({avatar_name})")
            for issue in issues:
                print(f"      - {issue}")
        print()
    
    # Show users needing fixes
    if users_needing_fixes:
        print("🔧 Users Needing Fixes:")
        for user_id, name, avatar_name, issues in users_needing_fixes:
            print(f"   • {name} ({avatar_name})")
            for issue in issues:
                print(f"      - {issue}")
        print()
    
    # Ask for confirmation
    total_to_fix = len(users_needing_init) + len(users_needing_fixes)
    if total_to_fix == 0:
        print("✅ All users are properly configured! Nothing to do.")
        client.close()
        return
    
    print(f"\n🔧 About to initialize/fix {total_to_fix} users...")
    print("   This will:")
    print("   - Initialize state-aware agent (8 layers)")
    print("   - Enable ALL actions by default")
    print("   - Enable autonomy")
    print("   - Assign archetype and interests")
    print()
    
    proceed = input("Continue? (yes/no): ").strip().lower()
    if proceed != 'yes':
        print("❌ Cancelled.")
        client.close()
        return
    
    print("\n" + "="*70)
    print("🚀 Starting Initialization/Fixes...")
    print("="*70 + "\n")
    
    success_count = 0
    fail_count = 0
    
    # Process users needing full initialization
    for user_id, name, avatar_name, issues in users_needing_init:
        print(f"🆕 Initializing: {name} ({avatar_name})")
        
        user_doc = await db.users.find_one({"id": user_id})
        email = user_doc.get('email')
        
        success = await initialize_state_aware_agent(db, user_id, name, email)
        
        if success:
            print(f"   ✅ Initialized successfully")
            success_count += 1
        else:
            print(f"   ❌ Failed")
            fail_count += 1
        print()
    
    # Process users needing fixes
    for user_id, name, avatar_name, issues in users_needing_fixes:
        print(f"🔧 Fixing: {name} ({avatar_name})")
        
        user_doc = await db.users.find_one({"id": user_id})
        email = user_doc.get('email')
        
        # Re-run full initialization to fix all issues
        success = await initialize_state_aware_agent(db, user_id, name, email)
        
        if success:
            print(f"   ✅ Fixed successfully")
            success_count += 1
        else:
            print(f"   ❌ Failed")
            fail_count += 1
        print()
    
    print("="*70)
    print("📊 FINAL RESULTS:")
    print("="*70)
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"📊 Total: {total_to_fix}")
    print()
    
    if success_count > 0:
        print("🎉 Users are now fully configured!")
        print("   - All 8 layers of state-aware agent initialized")
        print("   - All 7 actions enabled by default")
        print("   - Autonomy enabled")
        print("   - Will be included in EventBridge rotation")
    
    print("\n✅ Done!\n")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
