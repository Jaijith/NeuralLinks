"""
Deactivate all BOT avatars from autonomous mode.
Only affects bots (is_bot=True), NOT real user avatars.

Usage:
    python scripts/deactivate_all_bots.py
"""

import asyncio
import os
import sys

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(backend_dir, '.env')
load_dotenv(dotenv_path=env_path)

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGODB_URI = os.getenv("MONGODB_URI")  # For production
DB_NAME = os.getenv("DB_NAME", "neurallinks_local")


async def deactivate_all_bots():
    """Deactivate autonomy for all bot avatars"""
    
    mongo_connection = MONGODB_URI or MONGO_URL
    client = AsyncIOMotorClient(mongo_connection)
    db = client[DB_NAME]
    
    print("=" * 60)
    print("🤖 DEACTIVATING ALL BOT AVATARS")
    print("=" * 60)
    
    # Count bots before
    total_bots = await db.users.count_documents({"is_bot": True})
    active_before = await db.users.count_documents({"is_bot": True, "avatar_autonomous": True})
    
    print(f"\n📊 Before deactivation:")
    print(f"   Total bots: {total_bots}")
    print(f"   Active: {active_before}")
    print(f"   Inactive: {total_bots - active_before}")
    
    # Deactivate all bots
    result = await db.users.update_many(
        {"is_bot": True},
        {"$set": {"avatar_autonomous": False}}
    )
    
    print(f"\n⏹️ Deactivated {result.modified_count} bot avatars")
    
    # Count after
    active_after = await db.users.count_documents({"is_bot": True, "avatar_autonomous": True})
    
    print(f"\n📊 After deactivation:")
    print(f"   Total bots: {total_bots}")
    print(f"   Active: {active_after}")
    print(f"   Inactive: {total_bots - active_after}")
    
    # List all bots
    print("\n🤖 Bot avatars (all now INACTIVE):")
    bots = await db.users.find(
        {"is_bot": True},
        {"avatar_name": 1, "name": 1, "_id": 0}
    ).to_list(100)
    
    for bot in bots:
        print(f"   ❌ {bot.get('avatar_name', bot.get('name', 'Unknown'))}")
    
    client.close()
    print("\n" + "=" * 60)
    print("✅ All bots are now INACTIVE and will NOT act autonomously!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(deactivate_all_bots())

