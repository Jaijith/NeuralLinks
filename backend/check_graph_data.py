"""
Script to check what data is stored in the knowledge graph
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def check_graph_data():
    # Connect to MongoDB - use same env vars as server
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "neurallinks_local")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get user ID from command line or use a test user
    import sys
    user_id = sys.argv[1] if len(sys.argv) > 1 else "dedc30ef-dca9-467d-84b1-5e643941e6fd"
    
    print(f"\n{'='*80}")
    print(f"Checking Knowledge Graph Data for User: {user_id}")
    print(f"{'='*80}\n")
    
    # Get all nodes for this user
    nodes = await db.graph_nodes.find({"user_id": user_id}).to_list(1000)
    
    print(f"Total Nodes: {len(nodes)}\n")
    
    # Group by source
    by_source = {}
    by_type = {}
    
    for node in nodes:
        source = node.get("properties", {}).get("source", "unknown")
        node_type = node.get("node_type", "unknown")
        
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(node)
        
        if node_type not in by_type:
            by_type[node_type] = []
        by_type[node_type].append(node)
    
    # Print by source
    print("=" * 80)
    print("NODES BY SOURCE:")
    print("=" * 80)
    for source, source_nodes in sorted(by_source.items()):
        print(f"\n{source.upper()}: {len(source_nodes)} nodes")
        for node in source_nodes[:10]:  # Show first 10
            label = node.get("label", "N/A")
            node_type = node.get("node_type", "N/A")
            props = node.get("properties", {})
            print(f"  - [{node_type}] {label}")
            if props:
                print(f"    Properties: {list(props.keys())}")
        if len(source_nodes) > 10:
            print(f"  ... and {len(source_nodes) - 10} more")
    
    # Print by type
    print("\n" + "=" * 80)
    print("NODES BY TYPE:")
    print("=" * 80)
    for node_type, type_nodes in sorted(by_type.items()):
        print(f"\n{node_type.upper()}: {len(type_nodes)} nodes")
        for node in type_nodes[:5]:  # Show first 5
            label = node.get("label", "N/A")
            source = node.get("properties", {}).get("source", "unknown")
            print(f"  - {label} (from: {source})")
        if len(type_nodes) > 5:
            print(f"  ... and {len(type_nodes) - 5} more")
    
    # Specifically check LinkedIn data
    print("\n" + "=" * 80)
    print("LINKEDIN DATA:")
    print("=" * 80)
    linkedin_nodes = [n for n in nodes if n.get("properties", {}).get("source") == "linkedin"]
    print(f"\nTotal LinkedIn nodes: {len(linkedin_nodes)}\n")
    
    if linkedin_nodes:
        for node in linkedin_nodes:
            print(f"Type: {node.get('node_type')}")
            print(f"Label: {node.get('label')}")
            print(f"Properties: {node.get('properties', {})}")
            print("-" * 80)
    else:
        print("No LinkedIn nodes found in graph!")
    
    # Check integration data
    print("\n" + "=" * 80)
    print("LINKEDIN INTEGRATION DATA:")
    print("=" * 80)
    integration = await db.user_integrations.find_one({
        "user_id": user_id,
        "platform_name": "linkedin"
    })
    
    if integration:
        print(f"\nIntegration Status: {'Connected' if integration.get('connected') else 'Not Connected'}")
        print(f"Has Access Token: {bool(integration.get('access_token'))}")
        print(f"Last Sync: {integration.get('last_sync', 'Never')}")
        print(f"Data Collected: {integration.get('data_collected', 0)} nodes")
        
        profile_data = integration.get("profile_data", {})
        if profile_data:
            print(f"\nProfile Data Keys: {list(profile_data.keys())}")
            if "headline" in profile_data:
                print(f"Headline: {profile_data.get('headline')}")
            if "summary" in profile_data:
                summary = profile_data.get("summary", "")
                print(f"Summary: {summary[:100]}..." if len(summary) > 100 else f"Summary: {summary}")
            
            skills_data = profile_data.get("_raw_skills", {})
            if skills_data:
                elements = skills_data.get("elements", [])
                print(f"Skills Count: {len(elements)}")
                if elements:
                    print(f"Skills: {[s.get('name', '') for s in elements[:10]]}")
    else:
        print("No LinkedIn integration found!")
    
    # Check user profile updates
    print("\n" + "=" * 80)
    print("USER PROFILE UPDATES:")
    print("=" * 80)
    user_doc = await db.users.find_one({"id": user_id})
    if user_doc:
        print(f"Job Title: {user_doc.get('job_title', 'Not set')}")
        print(f"Interests: {user_doc.get('interests', [])}")
    else:
        print("User not found!")
    
    print("\n" + "=" * 80)
    client.close()

if __name__ == "__main__":
    asyncio.run(check_graph_data())

