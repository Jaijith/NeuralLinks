#!/usr/bin/env python3
"""
Debug script to test Graph Context retrieval
"""

import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def debug_graph_context():
    # Connect to MongoDB directly
    mongo_url = "mongodb://localhost:27017"
    client = AsyncIOMotorClient(mongo_url)
    db = client["test_database"]
    
    user_id = "test-graphrag-user-1761825596222"
    
    print("=== Direct MongoDB Query ===")
    
    # Get all user's graph nodes directly
    nodes = await db.graph_nodes.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(1000)
    
    print(f"Found {len(nodes)} nodes in MongoDB")
    
    # Organize by type
    context = {
        "interests": [],
        "traits": [],
        "values": [],
        "experiences": [],
        "preferences": [],
        "demographics": []
    }
    
    for node in nodes:
        node_type = node.get("node_type", "interest")
        label = node.get("label", "")
        properties = node.get("properties", {})
        strength = properties.get("strength", 1.0)
        
        item = {
            "label": label,
            "strength": strength,
            "properties": properties
        }
        
        if node_type in context:
            context[node_type].append(item)
        else:
            # Handle unknown node types by adding to interests as fallback
            context["interests"].append(item)
            print(f"Unknown node type '{node_type}' added to interests")
    
    # Sort by strength
    for key in context:
        context[key] = sorted(context[key], key=lambda x: x.get("strength", 0), reverse=True)
    
    print("\n=== Organized Context ===")
    for key, items in context.items():
        print(f"{key}: {len(items)} items")
        for item in items[:3]:  # Show first 3
            print(f"  - {item['label']} (strength: {item['strength']})")
    
    print("\n=== API Test ===")
    
    # Test API
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        response = await http_client.get(
            "https://sense-maya.preview.emergentagent.com/api/graph/context",
            headers={"Authorization": "Bearer test_session_1761825596222"}
        )
        
        print(f"API Status: {response.status_code}")
        if response.status_code == 200:
            api_context = response.json()
            print("API Response:")
            for key, items in api_context.items():
                print(f"  {key}: {len(items)} items")
        else:
            print(f"API Error: {response.text}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(debug_graph_context())