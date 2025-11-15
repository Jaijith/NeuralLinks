"""
Script to list all users and their LinkedIn integrations
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def list_users():
    # Connect to MongoDB - use same env vars as server
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "neurallinks_local")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print(f"Connecting to: {mongo_url}")
    print(f"Database: {db_name}\n")
    
    print(f"\n{'='*80}")
    print("ALL USERS:")
    print(f"{'='*80}\n")
    
    # Get all users
    users = await db.users.find({}, {"id": 1, "name": 1, "email": 1}).to_list(100)
    
    print(f"Total Users: {len(users)}\n")
    
    for user in users:
        user_id = user.get("id")
        name = user.get("name", "N/A")
        email = user.get("email", "N/A")
        
        print(f"User ID: {user_id}")
        print(f"Name: {name}")
        print(f"Email: {email}")
        
        # Check LinkedIn integration
        integration = await db.user_integrations.find_one({
            "user_id": user_id,
            "platform_name": "linkedin"
        })
        
        if integration:
            print(f"LinkedIn: Connected (has token: {bool(integration.get('access_token'))})")
            profile_data = integration.get("profile_data", {})
            if profile_data:
                print(f"  Profile keys: {list(profile_data.keys())}")
        else:
            print("LinkedIn: Not connected")
        
        # Count graph nodes
        node_count = await db.graph_nodes.count_documents({"user_id": user_id})
        print(f"Graph Nodes: {node_count}")
        
        # Count LinkedIn nodes
        linkedin_node_count = await db.graph_nodes.count_documents({
            "user_id": user_id,
            "properties.source": "linkedin"
        })
        print(f"LinkedIn Nodes: {linkedin_node_count}")
        
        print("-" * 80)
        print()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(list_users())

