#!/usr/bin/env python3
"""
Run activity cycles for the three new avatars: B11, Seven, _bLikker
Shows the state-aware decision-making process in action
"""
import asyncio
import os
import sys
import json
import boto3
from datetime import datetime, timezone

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from motor.motor_asyncio import AsyncIOMotorClient
from domain.avatar.state_aware_agent import StateAwareAgent


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


async def run_avatar_cycle(db, user_id, avatar_name):
    """Run a single cycle for an avatar and show results"""
    
    print(f"\n{'='*70}")
    print(f"🤖 Running Cycle for: {avatar_name}")
    print(f"{'='*70}\n")
    
    try:
        # Get user
        user = await db.users.find_one({"id": user_id})
        if not user:
            print(f"❌ User not found")
            return None
        
        # Create state-aware agent
        agent = StateAwareAgent(user, db)
        
        # Initialize agent
        print("📋 Initializing agent...")
        await agent.initialize()
        
        # Show initial state
        initial_summary = await agent.get_state_summary()
        if initial_summary:
            print(f"✅ Agent initialized")
            print(f"   Archetype: {agent.character_profile.get_archetype() if agent.character_profile else 'N/A'}")
            print(f"   Current State: {initial_summary.get('current_state', {}).get('top_level', 'N/A')}")
            
            internal = initial_summary.get('internal_state', {})
            print(f"   Energy: {internal.get('energy_level', 'N/A')}")
            print(f"   Mood: {internal.get('mood', 'N/A')}")
            print(f"   Social Desire: {internal.get('social_desire', 'N/A')}")
        
        # Run one cycle
        print(f"\n🚀 Running activity cycle...")
        start_time = datetime.now()
        
        await agent._run_single_cycle()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"✅ Cycle completed in {elapsed:.2f}s")
        
        # Get final state
        final_summary = await agent.get_state_summary()
        if final_summary:
            print(f"\n📊 Final State:")
            print(f"   State: {final_summary.get('current_state', {}).get('top_level', 'N/A')}")
            
            internal = final_summary.get('internal_state', {})
            print(f"   Energy: {internal.get('energy_level', 'N/A')}")
            print(f"   Mood: {internal.get('mood', 'N/A')}")
        
        # Check for recent activity
        activities = await db.autonomous_activities.find({
            "bot_id": user_id
        }).sort([("timestamp", -1)]).limit(1).to_list(1)
        
        if activities:
            activity = activities[0]
            print(f"\n🎯 Last Action Taken:")
            print(f"   Type: {activity.get('action_type', 'unknown')}")
            print(f"   Success: {'✅' if activity.get('success') else '❌'}")
            print(f"   Time: {activity.get('timestamp', 'N/A')}")
            if not activity.get('success'):
                print(f"   Error: {activity.get('error', 'Unknown error')}")
        
        # Check for new posts
        posts = await db.posts.find({
            "user_id": user_id,
            "post_type": "avatar"
        }).sort([("created_at", -1)]).limit(1).to_list(1)
        
        if posts:
            post = posts[0]
            created_at = post.get('created_at', '')
            # Check if post is recent (within last 5 minutes)
            try:
                post_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                age_seconds = (datetime.now(timezone.utc) - post_time).total_seconds()
                
                if age_seconds < 300:  # 5 minutes
                    print(f"\n📝 New Post Created:")
                    print(f"   Text: {post.get('text', '')[:100]}...")
                    print(f"   Created: {created_at}")
            except:
                pass
        
        return {
            'avatar': avatar_name,
            'status': 'success',
            'final_state': final_summary.get('current_state', {}).get('top_level', 'N/A') if final_summary else 'N/A'
        }
        
    except Exception as e:
        print(f"❌ Error running cycle: {e}")
        import traceback
        traceback.print_exc()
        return {
            'avatar': avatar_name,
            'status': 'error',
            'error': str(e)
        }


async def main():
    """Run cycles for all three avatars"""
    
    print("=" * 70)
    print("║  🤖 Running Activity Cycles for New Avatars                       ║")
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
        # Find user
        user = await db.users.find_one({
            "name": {"$regex": user_name, "$options": "i"}
        })
        
        if not user:
            print(f"\n❌ User '{user_name}' NOT FOUND")
            results.append({
                'avatar': avatar_name,
                'status': 'not_found'
            })
            continue
        
        user_id = user.get('id')
        
        # Run cycle
        result = await run_avatar_cycle(db, user_id, avatar_name)
        if result:
            results.append(result)
        
        # Small delay between cycles
        await asyncio.sleep(2)
    
    # Summary
    print(f"\n\n{'='*70}")
    print(f"📊 ACTIVITY SUMMARY")
    print(f"{'='*70}\n")
    
    success_count = sum(1 for r in results if r.get('status') == 'success')
    error_count = sum(1 for r in results if r.get('status') == 'error')
    not_found_count = sum(1 for r in results if r.get('status') == 'not_found')
    
    print(f"Total Avatars: {len(results)}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"⚠️  Not Found: {not_found_count}\n")
    
    if success_count > 0:
        print("Successful Cycles:")
        for r in results:
            if r.get('status') == 'success':
                print(f"   ✅ {r['avatar']}: Final state = {r['final_state']}")
    
    if error_count > 0:
        print("\nErrors:")
        for r in results:
            if r.get('status') == 'error':
                print(f"   ❌ {r['avatar']}: {r.get('error', 'Unknown error')}")
    
    print(f"\n💡 What Happened:")
    print(f"   Each avatar went through:")
    print(f"   1. State perception (saw friends, posts, etc.)")
    print(f"   2. Internal state update (energy, mood)")
    print(f"   3. State machine evaluation (ACTIVE/SOCIAL/CREATIVE)")
    print(f"   4. Decision making (chose best action)")
    print(f"   5. Action execution (did something)")
    
    print(f"\n🔍 Check Results:")
    print(f"   • Check autonomous_activities collection for recorded actions")
    print(f"   • Check posts collection for any new avatar posts")
    print(f"   • Run verify_state_aware_agents.py to see updated states")
    
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
