"""
Debug why DigitalHunter isn't posting
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "neurallinks_local"

async def debug_digital_hunter():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    user_id = "dedc30ef-dca9-467d-84b1-5e643941e6fd"
    
    print("\n" + "="*80)
    print("🔍 DEBUGGING DIGITALHUNTER")
    print("="*80)
    
    # Get user
    user = await db.users.find_one({"id": user_id})
    print(f"\n✓ User: {user.get('avatar_name')}")
    print(f"  • Autonomous: {user.get('avatar_autonomous')}")
    print(f"  • Activity Level: {user.get('avatar_activity_level')}")
    print(f"  • Archetype: {user.get('archetype')}")
    
    # Check friendships
    friendships = await db.friendships.find({
        "$or": [
            {"user1_id": user_id},
            {"user2_id": user_id}
        ]
    }).to_list(100)
    
    print(f"\n👥 Friendships: {len(friendships)}")
    for f in friendships[:5]:
        friend_id = f['user2_id'] if f['user1_id'] == user_id else f['user1_id']
        friend = await db.users.find_one({"id": friend_id}, {"avatar_name": 1, "name": 1})
        print(f"  • {friend.get('avatar_name', friend.get('name'))}")
    
    # Check posts from friends
    if friendships:
        friend_ids = [
            f['user2_id'] if f['user1_id'] == user_id else f['user1_id']
            for f in friendships
        ]
        
        posts = await db.posts.find({
            "user_id": {"$in": friend_ids}
        }).sort([("created_at", -1)]).limit(5).to_list(5)
        
        print(f"\n📬 Posts from friends: {len(posts)}")
        for post in posts:
            text = post.get('text', post.get('content', 'No text'))[:50]
            print(f"  • {text}...")
    else:
        print(f"\n⚠️  NO FRIENDS! Avatar has no posts to react to")
    
    # Check graph nodes
    graph_nodes = await db.graph_nodes.count_documents({"user_id": user_id})
    print(f"\n🧠 Graph Nodes: {graph_nodes}")
    
    # Show some graph nodes
    if graph_nodes > 0:
        nodes = await db.graph_nodes.find({"user_id": user_id}).limit(5).to_list(5)
        print("  Sample nodes:")
        for node in nodes:
            print(f"  • {node.get('node_type')}: {node.get('label')}")
    
    # Check last autonomous activity
    last_activities = await db.autonomous_activity.find(
        {"user_id": user_id}
    ).sort([("timestamp", -1)]).limit(5).to_list(5)
    
    print(f"\n📊 Last Activities: {len(last_activities)}")
    for activity in last_activities:
        action = activity.get('action_type', 'unknown')
        desc = activity.get('description', 'no description')
        timestamp = activity.get('timestamp', 'unknown')
        print(f"  • {timestamp}: {action} - {desc}")
    
    client.close()
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(debug_digital_hunter())




