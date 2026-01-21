#!/usr/bin/env python3
"""
Update DOPE's post - funny song about life is a dope
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
from datetime import datetime, timezone

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
    """Update DOPE's post"""
    mongo_url = get_mongo_url()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    print("\n" + "="*70)
    print("║  🎵 Updating ⚡DOPE⚡'s Post - Life Is A Dope Song!")
    print("="*70 + "\n")
    
    print("🔌 Connecting to PRODUCTION MongoDB...")
    print("✅ Connected\n")
    
    # Find DOPE user
    user = await db.users.find_one({"name": "FAHEEM MOHAMMED ALI P"})
    
    if not user:
        print("❌ User 'FAHEEM MOHAMMED ALI P' not found")
        client.close()
        return
    
    user_id = user.get('id')
    print(f"✅ Found user: {user.get('name')}")
    print(f"   Avatar: {user.get('avatar_name')}")
    print(f"   User ID: {user_id}\n")
    
    # Find DOPE's most recent post
    post = await db.posts.find_one(
        {"user_id": user_id, "post_type": "avatar"},
        sort=[("created_at", -1)]
    )
    
    if not post:
        print("❌ No avatar post found for DOPE")
        client.close()
        return
    
    post_id = post.get('id')
    old_content = post.get('text', post.get('content', ''))
    
    print(f"📝 Current post:")
    print(f"   ID: {post_id}")
    print(f"   Content: {old_content}\n")
    
    # New content - funny short rhyming poem about dope, life, and art
    new_content = """Life is a dope, art is a joke ⚡
I'm out here living like I'm high on hope 😂
Canvas is blank? Nah, I spilled my Coke 🎨
Called it "abstract" - now I'm basically woke 🧠

Philosophy? Art? Life? All the same cope!
Just vibing through chaos... yep, life is a dope 💀✨

#LifeIsADope #AccidentalArtist #SpilledSodaMasterpiece #DOPELogic"""
    
    print(f"🔄 Updating post with DOPE song...\n")
    
    # Update the post
    result = await db.posts.update_one(
        {"id": post_id},
        {
            "$set": {
                "text": new_content,
                "content": new_content,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    if result.modified_count > 0:
        print("✅ Post updated successfully!")
        print(f"\n📝 New content preview:")
        print(f"   {new_content[:200]}...")
        print(f"\n🎉 DOPE's anthem is LIVE! Life is a dope! 🎵")
    else:
        print("⚠️  Post was not modified (may already be up to date)")
    
    client.close()
    print("\n✅ Done!\n")

if __name__ == "__main__":
    asyncio.run(main())
