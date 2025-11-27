#!/usr/bin/env python3
"""
Script to change all avatars from 'hypo' activity level to 'low' activity level
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
env_path = backend_dir / '.env'
load_dotenv(dotenv_path=env_path)

async def change_avatars_from_hypo():
    """Change all avatars from hypo to low activity level"""
    
    print("="*60)
    print("║     🔧 Change Avatars from Hypo to Low Activity Level    ║")
    print("="*60)
    
    # Connect to MongoDB
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    # Find all avatars with hypo activity level
    hypo_avatars = await db.users.find({
        "avatar_activity_level": "hypo",
        "avatar_name": {"$exists": True}
    }).to_list(1000)
    
    print(f"\n📊 Found {len(hypo_avatars)} avatars with 'hypo' activity level")
    
    if len(hypo_avatars) == 0:
        print("\n✅ No avatars with 'hypo' activity level found. Nothing to change.")
        client.close()
        return
    
    # Show avatars that will be changed
    print("\n📋 Avatars to change:")
    for i, avatar in enumerate(hypo_avatars[:10], 1):  # Show first 10
        name = avatar.get('avatar_name', 'Unknown')
        is_bot = avatar.get('is_bot', False)
        avatar_type = "🤖 Bot" if is_bot else "✨ User Avatar"
        print(f"   {i}. {name} ({avatar_type})")
    
    if len(hypo_avatars) > 10:
        print(f"   ... and {len(hypo_avatars) - 10} more")
    
    # Update all to 'low' activity level
    print("\n🔄 Changing all avatars from 'hypo' to 'low' activity level...")
    
    result = await db.users.update_many(
        {"avatar_activity_level": "hypo"},
        {"$set": {"avatar_activity_level": "low"}}
    )
    
    print(f"✅ Updated {result.modified_count} avatars")
    
    # Verify the change
    remaining_hypo = await db.users.count_documents({"avatar_activity_level": "hypo"})
    low_avatars = await db.users.count_documents({"avatar_activity_level": "low"})
    
    print(f"\n📊 Verification:")
    print(f"   - Avatars with 'hypo': {remaining_hypo}")
    print(f"   - Avatars with 'low': {low_avatars}")
    
    if remaining_hypo == 0:
        print("\n✅ Success! All avatars have been changed from 'hypo' to 'low' activity level.")
    else:
        print(f"\n⚠️  Warning: {remaining_hypo} avatars still have 'hypo' activity level")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(change_avatars_from_hypo())

