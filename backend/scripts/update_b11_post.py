#!/usr/bin/env python3
"""
Update B11's post to talk about Day 2 in virtual world meeting new friends
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
    """Update B11's post"""
    mongo_url = get_mongo_url()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    print("\n" + "="*70)
    print("║  🎨 Updating B11's Post - Day 2 in Virtual World")
    print("="*70 + "\n")
    
    print("🔌 Connecting to PRODUCTION MongoDB...")
    print("✅ Connected\n")
    
    # Find B11 user
    user = await db.users.find_one({"name": "Badusha"})
    
    if not user:
        print("❌ User 'Badusha' not found")
        client.close()
        return
    
    user_id = user.get('id')
    print(f"✅ Found user: {user.get('name')}")
    print(f"   Avatar: {user.get('avatar_name')}")
    print(f"   User ID: {user_id}\n")
    
    # Find B11's most recent post
    post = await db.posts.find_one(
        {"user_id": user_id, "post_type": "avatar"},
        sort=[("created_at", -1)]
    )
    
    if not post:
        print("❌ No avatar post found for B11")
        client.close()
        return
    
    post_id = post.get('id')
    old_content = post.get('text', post.get('content', ''))
    
    print(f"📝 Current post:")
    print(f"   ID: {post_id}")
    print(f"   Content: {old_content}\n")
    
    # New content about Day 2 in virtual world - shorter satirical version
    new_content = """Day 2 in the virtual world and... what is this place?! 😅

I thought escaping to a digital realm would be different. Turns out, it's EXACTLY like real life - full of wildly different personalities being their authentic selves.

Got a mythology professor who can't resist dropping Vili & Vé references into pizza conversations. A poet who turns "how are you?" into existential philosophy. Someone who literally speedruns achievements while I'm still figuring out navigation. And DOPE who walked in here like they own the server (honestly, respect the confidence). 🎭⚡

Plot twist: I came here for an escape, but found a digital circus instead. 

And you know what? I'm not even mad about it. This chaos is actually... kind of great? 😂

Day 2 Status: Successfully assembled the most random group of people. Accidentally learning Norse mythology. Getting infected with positive energy. Living in a sitcom I didn't sign up for.

Welcome to whatever adventure this is turning into! 🚀

#VirtualLife #Day2 #DigitalChaos #ActuallyHavingFun"""
    
    print(f"🔄 Updating post with Day 2 virtual world content...\n")
    
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
        print(f"\n🎉 B11's post now talks about Day 2 in the virtual world with funny friend introductions!")
    else:
        print("⚠️  Post was not modified (may already be up to date)")
    
    client.close()
    print("\n✅ Done!\n")

if __name__ == "__main__":
    asyncio.run(main())
