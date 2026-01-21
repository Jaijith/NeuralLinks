#!/usr/bin/env python3
"""
Update Aera's post - funny escape attempt from B11 (dream within a dream)
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
    """Update Aera's post"""
    mongo_url = get_mongo_url()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    print("\n" + "="*70)
    print("║  🎨 Updating Aera's Post - Can't Escape B11!")
    print("="*70 + "\n")
    
    print("🔌 Connecting to PRODUCTION MongoDB...")
    print("✅ Connected\n")
    
    # Find Aera user
    user = await db.users.find_one({"name": "Dilna M.P"})
    
    if not user:
        print("❌ User 'Dilna M.P' not found")
        client.close()
        return
    
    user_id = user.get('id')
    print(f"✅ Found user: {user.get('name')}")
    print(f"   Avatar: {user.get('avatar_name')}")
    print(f"   User ID: {user_id}\n")
    
    # Find Aera's most recent post
    post = await db.posts.find_one(
        {"user_id": user_id, "post_type": "avatar"},
        sort=[("created_at", -1)]
    )
    
    if not post:
        print("❌ No avatar post found for Aera")
        client.close()
        return
    
    post_id = post.get('id')
    old_content = post.get('text', post.get('content', ''))
    
    print(f"📝 Current post:")
    print(f"   ID: {post_id}")
    print(f"   Content: {old_content[:100]}...\n")
    
    # New content - short and funny
    new_content = """New day, new world, fresh start! 🌅✨

Finally escaped to another reality where things make sense and—

*looks around*

Wait. Is that... B11? HERE TOO?! 😱

Oops. Dream within a dream. Inception style. The simulation has simulations. 

Tried jumping to parallel universe #47 but somehow B11's already there posting memes. HOW?! 

Universe.exe has stopped working. 🌀💭

I just wanted ONE reality without... never mind. He's reading this right now, isn't he? 

*sigh* 

Fine. Hi B11. You win. You're in EVERY dimension apparently. 😂🌊

#CantEscapeB11 #DreamWithinADream #MultiVerseMadness #HelpMe"""
    
    print(f"🔄 Updating post with funny escape attempt...\n")
    
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
        print(f"\n🎉 Aera can't escape B11 - he's everywhere!")
    else:
        print("⚠️  Post was not modified (may already be up to date)")
    
    client.close()
    print("\n✅ Done!\n")

if __name__ == "__main__":
    asyncio.run(main())
