"""
Trigger all avatars to create posts
Uses state-aware agent with forced 'create_post' action
Includes: _bLikker, B11, Seven, Aera, DOPE
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import boto3
import json
from motor.motor_asyncio import AsyncIOMotorClient
from domain.avatar.state_aware_agent import StateAwareAgent
from domain.avatar.intelligent import IntelligentAvatar
from domain.graph.rag import GraphRAG
from core.config import get_openai_client, OPENAI_MODEL

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

async def trigger_avatar_post(db, user_id: str, avatar_name: str):
    """Trigger a single avatar to create a post"""
    print(f"\n{'='*70}")
    print(f"🎨 Triggering Post Creation for: {avatar_name}")
    print(f"{'='*70}\n")
    
    # Get user
    user = await db.users.find_one({"id": user_id})
    if not user:
        print(f"❌ User not found: {user_id}")
        return False
    
    # Create intelligent avatar
    openai_client = get_openai_client()
    graph_rag = GraphRAG(db)
    intelligent_avatar = IntelligentAvatar(db, openai_client, OPENAI_MODEL, graph_rag)
    
    # Create state-aware agent
    agent = StateAwareAgent(
        bot=user,
        db=db,
        intelligent_avatar=intelligent_avatar
    )
    
    print("📋 Initializing agent...")
    await agent.initialize()
    
    archetype = user.get('avatar_archetype', 'Unknown')
    print(f"✅ Agent initialized")
    print(f"   Archetype: {archetype}")
    print(f"   Interests: {user.get('avatar_interests', [])[:3]}")
    print()
    
    print("🚀 Creating post (forced action)...")
    import time
    start = time.time()
    
    # Force create_post action (bypasses cooldown)
    await agent._run_single_cycle(force_action='create_post')
    
    elapsed = time.time() - start
    print(f"✅ Post creation completed in {elapsed:.2f}s\n")
    
    # Check if post was created
    recent_post = await db.posts.find_one(
        {"user_id": user_id},
        sort=[("created_at", -1)]
    )
    
    if recent_post:
        content = recent_post.get('content', '')
        created_at = recent_post.get('created_at')
        print(f"📝 Latest Post:")
        print(f"   Content: {content[:100]}{'...' if len(content) > 100 else ''}")
        print(f"   Created: {created_at}")
        print(f"   Post ID: {recent_post.get('id')}")
        return True
    else:
        print(f"⚠️  No post found (may have failed or been rate-limited)")
        return False

async def main():
    """Trigger posts for all three avatars"""
    mongo_url = get_mongo_url()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    print("\n" + "="*70)
    print("║  🎨 Triggering Post Creation for All Avatars")
    print("║  _bLikker, B11, Seven, Aera, ⚡DOPE⚡")
    print("="*70)
    
    print("\n🔌 Connecting to PRODUCTION MongoDB...")
    print("✅ Connected\n")
    
    # Define all avatars
    avatars = [
        ("Sreejith Sreekantan", "_bLikker"),
        ("Badusha", "B11"),
        ("Rafseena Sedeed", "Seven "),  # Note: has trailing space
        ("Dilna M.P", "Aera"),
        ("FAHEEM MOHAMMED ALI P", "⚡DOPE⚡")
    ]
    
    results = []
    
    for user_name, avatar_name in avatars:
        # Find user by name
        user = await db.users.find_one({"name": user_name})
        
        if not user:
            print(f"\n❌ User '{user_name}' not found")
            results.append(False)
            continue
        
        user_id = user.get('id')
        success = await trigger_avatar_post(db, user_id, avatar_name)
        results.append(success)
        
        # Small delay between avatars
        await asyncio.sleep(2)
    
    print("\n" + "="*70)
    print("📊 POST CREATION SUMMARY")
    print("="*70)
    print()
    print(f"Total Avatars: {len(avatars)}")
    print(f"✅ Successful: {sum(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}")
    print()
    
    if sum(results) > 0:
        print("✅ Posts created! Check the frontend to see them.")
    
    print("\n✅ Done!\n")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
