"""
Create friendships for DigitalHunter with some bots
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "neurallinks_local"

async def create_friendships():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    user_id = "dedc30ef-dca9-467d-84b1-5e643941e6fd"
    
    print("\n" + "="*80)
    print("👥 CREATING FRIENDSHIPS FOR DIGITALHUNTER")
    print("="*80)
    
    # Get some bots
    bots = await db.users.find({"is_bot": True}, {"_id": 0}).limit(10).to_list(10)
    
    print(f"\nFound {len(bots)} bots")
    
    friendships_created = 0
    
    for bot in bots:
        bot_id = bot['id']
        bot_name = bot.get('avatar_name', bot.get('name'))
        
        # Check if friendship already exists
        existing = await db.friendships.find_one({
            "$or": [
                {"user1_id": user_id, "user2_id": bot_id},
                {"user1_id": bot_id, "user2_id": user_id}
            ]
        })
        
        if existing:
            print(f"  ✓ Already friends with {bot_name}")
            continue
        
        # Create friendship
        friendship = {
            "id": str(uuid.uuid4()),
            "user1_id": user_id,
            "user2_id": bot_id,
            "status": "accepted",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.friendships.insert_one(friendship)
        friendships_created += 1
        print(f"  ✅ Created friendship with {bot_name}")
    
    print(f"\n🎉 Created {friendships_created} new friendships!")
    print(f"\nDigitalHunter can now:")
    print(f"  • See posts from {friendships_created} friends")
    print(f"  • Like and comment on their posts")
    print(f"  • Create posts that friends can see")
    
    client.close()
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(create_friendships())




