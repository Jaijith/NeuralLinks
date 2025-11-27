"""
Initialize knowledge graphs for real users (non-bots)
This creates starter graph nodes based on user profile data
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

async def initialize_user_graph(db, user):
    """Initialize graph for a single user"""
    user_id = user['id']
    name = user.get('name', 'User')
    
    # Check if graph already exists
    existing_nodes = await db.graph_nodes.count_documents({"user_id": user_id})
    
    if existing_nodes > 0:
        print(f"✓ {name} already has {existing_nodes} graph nodes, skipping...")
        return
    
    print(f"\n📝 Initializing graph for {name}...")
    
    # Extract interests from avatar profile
    avatar_interests = user.get('avatar_interests', [])
    interests = user.get('interests', [])
    all_interests = list(set(avatar_interests + interests))
    
    # If no interests, use generic tech/social interests
    if not all_interests:
        all_interests = [
            "technology", "social media", "innovation", 
            "learning", "connecting with others"
        ]
        print(f"   No interests found, using defaults: {all_interests}")
    
    nodes_created = 0
    
    # Create interest nodes
    for interest in all_interests:
        node = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'node_type': 'interest',
            'label': interest,
            'properties': {
                'importance': 8.0,
                'source': 'profile',
                'strength': 7.5
            },
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.graph_nodes.insert_one(node)
        nodes_created += 1
        print(f"   ✓ Created interest: {interest}")
    
    # Create some default personality traits
    traits = [
        "friendly",
        "curious", 
        "authentic",
        "open-minded"
    ]
    
    for trait in traits:
        node = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'node_type': 'trait',
            'label': trait,
            'properties': {
                'importance': 7.0,
                'source': 'default',
                'strength': 6.5
            },
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.graph_nodes.insert_one(node)
        nodes_created += 1
        print(f"   ✓ Created trait: {trait}")
    
    # Create some default values
    values = [
        "authenticity",
        "growth",
        "connection"
    ]
    
    for value in values:
        node = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'node_type': 'value',
            'label': value,
            'properties': {
                'importance': 8.0,
                'source': 'default',
                'strength': 7.0
            },
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.graph_nodes.insert_one(node)
        nodes_created += 1
        print(f"   ✓ Created value: {value}")
    
    print(f"✅ Created {nodes_created} graph nodes for {name}")
    
    return nodes_created

async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║      🧠 Initialize Real User Knowledge Graphs               ║
║                                                              ║
║      This creates starter graph data for real users         ║
║      so their avatars have context to work with             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        await db.command("ping")
        print("✅ MongoDB connected\n")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return
    
    # Find all real users (not bots)
    real_users = await db.users.find({"is_bot": {"$ne": True}}).to_list(100)
    
    if not real_users:
        print("⚠️  No real users found in database")
        client.close()
        return
    
    print(f"Found {len(real_users)} real user(s)\n")
    print("="*70)
    
    total_nodes_created = 0
    for user in real_users:
        nodes = await initialize_user_graph(db, user)
        if nodes:
            total_nodes_created += nodes
    
    print("\n" + "="*70)
    print(f"\n🎉 Complete! Created {total_nodes_created} total graph nodes")
    print("\nYour avatars now have starter knowledge graphs to work with!")
    print("These graphs will be enriched as you use the platform.\n")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())




