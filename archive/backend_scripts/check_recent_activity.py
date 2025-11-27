"""
Check recent avatar activity in the database
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "neurallinks_local"

async def check_activity():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("\n" + "="*80)
    print("🔍 CHECKING RECENT AUTONOMOUS ACTIVITY")
    print("="*80)
    
    # Check DigitalHunter specifically
    user_id = "dedc30ef-dca9-467d-84b1-5e643941e6fd"
    
    # Check recent posts (last 10 minutes)
    ten_min_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    recent_posts = await db.posts.find({
        "user_id": user_id,
        "created_at": {"$gte": ten_min_ago.isoformat()}
    }).to_list(10)
    
    print(f"\n📝 Recent Posts by DigitalHunter (last 10 min): {len(recent_posts)}")
    for post in recent_posts:
        text = post.get('text', post.get('content', 'No text'))[:60]
        created = post.get('created_at', 'unknown')
        print(f"   • {created}: {text}...")
    
    # Check all posts by DigitalHunter
    all_posts = await db.posts.find({"user_id": user_id}).sort([("created_at", -1)]).limit(5).to_list(5)
    print(f"\n📚 All Posts by DigitalHunter (last 5): {len(all_posts)}")
    for post in all_posts:
        text = post.get('text', post.get('content', 'No text'))[:60]
        created = post.get('created_at', 'unknown')
        print(f"   • {created}: {text}...")
    
    # Check autonomous activity logs
    activity_logs = await db.autonomous_activity.find({
        "user_id": user_id
    }).sort([("timestamp", -1)]).limit(10).to_list(10)
    
    print(f"\n📊 Autonomous Activity Logs: {len(activity_logs)}")
    for log in activity_logs:
        action = log.get('action_type', 'unknown')
        timestamp = log.get('timestamp', 'unknown')
        desc = log.get('description', '')[:50]
        print(f"   • {timestamp}: {action} - {desc}...")
    
    # Check if SimpleAgentManager is finding the user
    print("\n" + "="*80)
    print("🔍 CHECKING AGENT INITIALIZATION")
    print("="*80)
    
    user = await db.users.find_one({"id": user_id})
    print(f"\n✓ User found: {user.get('name')}")
    print(f"  • is_bot: {user.get('is_bot', 'not set')}")
    print(f"  • avatar_autonomous: {user.get('avatar_autonomous', 'not set')}")
    print(f"  • avatar_name: {user.get('avatar_name', 'not set')}")
    print(f"  • avatar_picture: {'✓ exists' if user.get('avatar_picture') else '✗ missing'}")
    
    # Check query that SimpleAgentManager uses
    print("\n" + "="*80)
    print("🔍 QUERY TEST: What SimpleAgentManager looks for")
    print("="*80)
    
    query = {
        "$or": [
            {"is_bot": True},  # All bots
            {"avatar_autonomous": True}  # Real users with autonomy enabled
        ],
        "avatar_name": {"$exists": True},
        "avatar_picture": {"$exists": True}
    }
    
    agents = await db.users.find(query, {"_id": 0, "id": 1, "avatar_name": 1, "is_bot": 1, "avatar_autonomous": 1}).to_list(100)
    
    print(f"\nFound {len(agents)} agents that match the criteria:")
    for agent in agents[:5]:  # Show first 5
        name = agent.get('avatar_name', 'unknown')
        is_bot = agent.get('is_bot', False)
        is_autonomous = agent.get('avatar_autonomous', False)
        agent_type = "🤖 Bot" if is_bot else "✨ User Avatar"
        print(f"  {agent_type}: {name}")
    
    if len(agents) > 5:
        print(f"  ... and {len(agents) - 5} more")
    
    # Check if DigitalHunter is in the list
    digital_hunter = next((a for a in agents if a.get('id') == user_id), None)
    if digital_hunter:
        print(f"\n✅ DigitalHunter IS being picked up by the autonomous system!")
    else:
        print(f"\n❌ DigitalHunter is NOT being picked up by the autonomous system!")
        print("\nDebugging info:")
        print(f"  • Query needs: is_bot=True OR avatar_autonomous=True")
        print(f"  • Query needs: avatar_name exists")
        print(f"  • Query needs: avatar_picture exists")
        print(f"\nDigitalHunter has:")
        print(f"  • is_bot: {user.get('is_bot', 'not set')}")
        print(f"  • avatar_autonomous: {user.get('avatar_autonomous', 'not set')}")
        print(f"  • avatar_name: {user.get('avatar_name', 'not set')}")
        print(f"  • avatar_picture exists: {'Yes' if user.get('avatar_picture') else 'No'}")
    
    client.close()
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(check_activity())




