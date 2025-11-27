import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

async def fix_bot_avatar_fields():
    """Update existing bot profiles to use avatar_ prefix instead of maya_ prefix"""
    
    print("🔧 Fixing bot avatar field names...")
    print("=" * 60)
    
    # Find all dual-world bots
    bots = await db.users.find({'is_bot': True, 'bot_type': 'dual_world'}).to_list(length=100)
    
    print(f"Found {len(bots)} dual-world bots to update\n")
    
    updated_count = 0
    
    for bot in bots:
        update_fields = {}
        
        # Copy maya_ fields to avatar_ fields
        if 'maya_nickname' in bot and 'avatar_name' not in bot:
            update_fields['avatar_name'] = bot['maya_nickname']
        
        if 'maya_picture' in bot and 'avatar_picture' not in bot:
            update_fields['avatar_picture'] = bot['maya_picture']
        
        if 'maya_bio' in bot and 'avatar_bio' not in bot:
            update_fields['avatar_bio'] = bot['maya_bio']
        
        if 'maya_interests' in bot and 'avatar_interests' not in bot:
            update_fields['avatar_interests'] = bot['maya_interests']
        
        # Add job title and location to avatar profile if missing
        if 'job_title' in bot and 'avatar_job_title' not in bot:
            update_fields['avatar_job_title'] = bot['job_title']
        
        if 'location' in bot and 'avatar_location' not in bot:
            update_fields['avatar_location'] = bot['location']
        
        # Update the bot if there are fields to update
        if update_fields:
            await db.users.update_one(
                {'id': bot['id']},
                {'$set': update_fields}
            )
            updated_count += 1
            print(f"✅ Updated: {bot.get('name', 'Unknown')} -> {update_fields.get('avatar_name', 'N/A')}")
    
    print("\n" + "=" * 60)
    print(f"🎉 Successfully updated {updated_count} bot profiles!")
    print("=" * 60)
    
    # Verify the update
    print("\n📊 Verification:")
    bots_with_avatar_name = await db.users.count_documents({
        'is_bot': True, 
        'bot_type': 'dual_world',
        'avatar_name': {'$exists': True}
    })
    print(f"   Bots with avatar_name field: {bots_with_avatar_name}")
    
    bots_with_avatar_picture = await db.users.count_documents({
        'is_bot': True, 
        'bot_type': 'dual_world',
        'avatar_picture': {'$exists': True}
    })
    print(f"   Bots with avatar_picture field: {bots_with_avatar_picture}")

if __name__ == '__main__':
    asyncio.run(fix_bot_avatar_fields())


