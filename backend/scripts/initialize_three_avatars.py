#!/usr/bin/env python3
"""
Initialize state-aware agents for the three existing avatars:
- Sreejith Sreekantan (_bLikker)
- Badusha (B11)
- Rafseena Sedeed (Seven)
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
from domain.avatar.initialization import initialize_state_aware_agent


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
    """Initialize state-aware agents for the three avatars"""
    
    print("=" * 70)
    print("║  🤖 Initializing State-Aware Agents                               ║")
    print("║  B11, Seven, _bLikker                                              ║")
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
    
    # Target users
    target_users = [
        ("Sreejith Sreekantan", "_bLikker"),
        ("Badusha", "B11"),
        ("Rafseena Sedeed", "Seven")
    ]
    
    results = []
    
    for user_name, avatar_name in target_users:
        print(f"\n{'='*70}")
        print(f"Initializing: {user_name} ({avatar_name})")
        print(f"{'='*70}\n")
        
        # Find user
        user = await db.users.find_one({
            "name": {"$regex": user_name, "$options": "i"}
        })
        
        if not user:
            print(f"❌ User '{user_name}' NOT FOUND")
            results.append({
                'user': user_name,
                'avatar': avatar_name,
                'status': 'not_found'
            })
            continue
        
        user_id = user.get('id')
        user_email = user.get('email')
        
        # Initialize state-aware agent
        success = await initialize_state_aware_agent(db, user_id, user_name, user_email)
        
        if success:
            print(f"✅ Successfully initialized {avatar_name}")
            results.append({
                'user': user_name,
                'avatar': avatar_name,
                'status': 'success'
            })
        else:
            print(f"❌ Failed to initialize {avatar_name}")
            results.append({
                'user': user_name,
                'avatar': avatar_name,
                'status': 'failed'
            })
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 INITIALIZATION SUMMARY")
    print(f"{'='*70}\n")
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    not_found_count = sum(1 for r in results if r['status'] == 'not_found')
    
    print(f"Total: {len(results)}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⚠️  Not Found: {not_found_count}\n")
    
    if success_count > 0:
        print("Successful initializations:")
        for r in results:
            if r['status'] == 'success':
                print(f"   ✅ {r['avatar']} ({r['user']})")
    
    if failed_count > 0 or not_found_count > 0:
        print("\nFailed/Not Found:")
        for r in results:
            if r['status'] in ['failed', 'not_found']:
                print(f"   ❌ {r['avatar']} ({r['user']}) - {r['status']}")
    
    print(f"\n💡 Next Steps:")
    if success_count == len(target_users):
        print("   ✅ All avatars initialized successfully!")
        print("   • Verify with: python scripts/verify_state_aware_agents.py")
        print("   • Start autonomous agent system to see them in action")
    else:
        print("   ⚠️  Some avatars need attention")
        print("   • Check logs above for details")
        print("   • Re-run script after fixing issues")
    
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
