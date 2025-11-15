"""
Check if ANY agents (bots or avatars) are posting
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "neurallinks_local"

async def check_all_activity():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("\n" + "="*80)
    print("🔍 CHECKING IF ANY AGENTS ARE POSTING")
    print("="*80)
    
    # Check recent posts by ANY user (last 5 minutes)
    five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    recent_posts = await db.posts.find({
        "created_at": {"$gte": five_min_ago.isoformat()}
    }).sort([("created_at", -1)]).to_list(20)
    
    print(f"\n📝 Recent Posts by ALL agents (last 5 min): {len(recent_posts)}")
    for post in recent_posts:
        user_id = post.get('user_id', 'unknown')[:20]
        text = post.get('text', post.get('content', 'No text'))[:50]
        created = post.get('created_at', 'unknown')
        print(f"   • {created}: User {user_id}... - {text}...")
    
    # Check last 10 posts overall
    all_recent_posts = await db.posts.find({}).sort([("created_at", -1)]).limit(10).to_list(10)
    print(f"\n📚 Last 10 Posts Overall (any time):")
    for post in all_recent_posts:
        user_id = post.get('user_id', 'unknown')[:20]
        text = post.get('text', post.get('content', 'No text'))[:50]
        created = post.get('created_at', 'unknown')
        print(f"   • {created}: User {user_id}... - {text}...")
    
    # Check autonomous activity logs (last 5 minutes)
    activity_logs = await db.autonomous_activity.find({
        "timestamp": {"$gte": five_min_ago.isoformat()}
    }).sort([("timestamp", -1)]).to_list(50)
    
    print(f"\n📊 Autonomous Activity Logs (last 5 min): {len(activity_logs)}")
    for log in activity_logs[:10]:  # Show first 10
        action = log.get('action_type', 'unknown')
        user_id = log.get('user_id', 'unknown')[:20]
        timestamp = log.get('timestamp', 'unknown')
        desc = log.get('description', '')[:40]
        print(f"   • {timestamp}: User {user_id}... - {action} - {desc}...")
    
    client.close()
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(check_all_activity())




