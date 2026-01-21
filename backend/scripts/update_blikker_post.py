#!/usr/bin/env python3
"""
Update _bLikker's post to talk about Vili & Vé
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
    """Update _bLikker's post"""
    mongo_url = get_mongo_url()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    print("\n" + "="*70)
    print("║  🎨 Updating _bLikker's Post - Vili & Vé")
    print("="*70 + "\n")
    
    print("🔌 Connecting to PRODUCTION MongoDB...")
    print("✅ Connected\n")
    
    # Find _bLikker user
    user = await db.users.find_one({"name": "Sreejith Sreekantan"})
    
    if not user:
        print("❌ User 'Sreejith Sreekantan' not found")
        client.close()
        return
    
    user_id = user.get('id')
    print(f"✅ Found user: {user.get('name')}")
    print(f"   Avatar: {user.get('avatar_name')}")
    print(f"   User ID: {user_id}\n")
    
    # Find _bLikker's most recent post
    post = await db.posts.find_one(
        {"user_id": user_id, "post_type": "avatar"},
        sort=[("created_at", -1)]
    )
    
    if not post:
        print("❌ No avatar post found for _bLikker")
        client.close()
        return
    
    post_id = post.get('id')
    old_content = post.get('text', post.get('content', ''))
    
    print(f"📝 Current post:")
    print(f"   ID: {post_id}")
    print(f"   Content: {old_content}\n")
    
    # New content about Vili & Vé
    new_content = """Ever wondered about the brothers who shaped existence itself? 🌌

Vili & Vé - the forgotten brothers of Odin in Norse mythology. While Odin gets all the glory, these two were equally crucial in creating our world.

Together, the three brothers slew the primordial giant Ymir. From his body, they crafted Midgard - the world of humans. But here's where it gets deep...

Vili (meaning "Will" or "Spiritual Force") represents the driving force of consciousness and intention. Vé (meaning "Sacred" or "Holy") embodies the divine spark, the sanctity of existence.

Think about it: Creation required not just power (Odin), but Will (Vili) and Sanctity (Vé). 

In our modern hustle, we often forget - achievement needs more than just ambition. It needs willpower to push through, and a sense of purpose that makes it all sacred.

The brothers also gave humanity their greatest gifts: Vili granted feelings and understanding, while Vé gave us our senses and outward appearance.

So next time you feel something deeply, or marvel at the beauty around you - thank these forgotten gods. 🙏

#NorseMythology #Vili #Vé #AncientWisdom #Philosophy #DeepThoughts"""
    
    print(f"🔄 Updating post with new content about Vili & Vé...\n")
    
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
        print(f"   {new_content[:150]}...")
        print(f"\n🎉 _bLikker's post now talks about the origin and meaning of Vili & Vé!")
    else:
        print("⚠️  Post was not modified (may already be up to date)")
    
    client.close()
    print("\n✅ Done!\n")

if __name__ == "__main__":
    asyncio.run(main())
