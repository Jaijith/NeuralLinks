"""
Quick script to check avatar autonomy configuration
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "neurallinks_local"

async def check_avatar_config():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Find all users (real users, not bots)
    real_users = await db.users.find({"is_bot": {"$ne": True}}, {"_id": 0}).to_list(100)
    
    print("\n" + "="*80)
    print("👤 REAL USER AVATAR CONFIGURATIONS")
    print("="*80)
    
    for user in real_users:
        user_id = user.get('id', 'unknown')
        name = user.get('name', 'Unknown')
        avatar_name = user.get('avatar_name', 'No avatar name')
        
        # Autonomy settings
        is_autonomous = user.get('avatar_autonomous', False)
        activity_level = user.get('avatar_activity_level', 'not set')
        archetype = user.get('archetype', 'not set')
        
        # Check if user has graph data
        graph_nodes = await db.graph_nodes.count_documents({"user_id": user_id})
        
        print(f"\n📋 User: {name}")
        print(f"   ID: {user_id}")
        print(f"   Avatar Name: {avatar_name}")
        print(f"   🤖 Autonomous: {'✅ YES' if is_autonomous else '❌ NO'}")
        print(f"   📊 Activity Level: {activity_level}")
        print(f"   🎭 Archetype: {archetype}")
        print(f"   🧠 Graph Nodes: {graph_nodes}")
        
        if is_autonomous:
            # Check recent activity
            recent_activity = await db.autonomous_activity.find(
                {"user_id": user_id}
            ).sort([("timestamp", -1)]).limit(3).to_list(3)
            
            if recent_activity:
                print(f"   📈 Recent Activity ({len(recent_activity)} actions):")
                for activity in recent_activity:
                    action = activity.get('action_type', 'unknown')
                    timestamp = activity.get('timestamp', 'unknown')
                    print(f"      • {action} at {timestamp}")
            else:
                print(f"   📈 Recent Activity: No activity logged yet")
    
    print("\n" + "="*80)
    print("🤖 BOT CONFIGURATIONS (for comparison)")
    print("="*80)
    
    bots = await db.users.find({"is_bot": True}, {"_id": 0}).limit(3).to_list(3)
    
    for bot in bots:
        bot_name = bot.get('avatar_name', bot.get('name', 'Unknown'))
        archetype = bot.get('archetype', 'not set')
        graph_nodes = await db.graph_nodes.count_documents({"user_id": bot['id']})
        
        print(f"\n🤖 Bot: {bot_name}")
        print(f"   🎭 Archetype: {archetype}")
        print(f"   🧠 Graph Nodes: {graph_nodes}")
    
    client.close()
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(check_avatar_config())




