"""
Test script for Avatar MCP Server
Demonstrates how to use the MCP tools
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
from avatar_mcp_client import AvatarMCPClient

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'neurallinks_local')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8001')


async def test_mcp_server():
    """Test the MCP server functionality"""
    print("=" * 80)
    print("🧪 Testing Avatar MCP Server")
    print("=" * 80)
    print()
    
    # Connect to MongoDB to get a test avatar
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Get a test avatar
        avatar = await db.users.find_one({
            "$or": [
                {"is_bot": True},
                {"avatar_autonomous": True}
            ],
            "avatar_name": {"$exists": True}
        })
        
        if not avatar:
            print("❌ No avatars found. Please create an avatar first.")
            return
        
        avatar_id = avatar['id']
        avatar_name = avatar.get('avatar_name', avatar.get('name', 'Unknown'))
        
        print(f"📋 Testing with avatar: {avatar_name} ({avatar_id})")
        print()
        
        # Initialize MCP client
        mcp_client = AvatarMCPClient(server_url=BACKEND_URL)
        
        # Test 1: List all tools
        print("1️⃣  Testing: List all tools")
        print("-" * 80)
        tools = await mcp_client.list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   • {tool['name']}: {tool['description']}")
        print()
        
        # Test 2: Get available tools for avatar
        print("2️⃣  Testing: Get available tools for avatar")
        print("-" * 80)
        available_tools = await mcp_client.get_available_tools(avatar_id)
        print(f"✅ Avatar can use {len(available_tools)} tools:")
        for tool in available_tools:
            print(f"   • {tool['name']}")
        print()
        
        # Test 3: Discover profiles
        if any(t['name'] == 'discover_profiles' for t in available_tools):
            print("3️⃣  Testing: Discover profiles")
            print("-" * 80)
            result = await mcp_client.discover_profiles(avatar_id, limit=3)
            if result.get('success'):
                print(f"✅ Discovered {len(result.get('profiles', []))} profiles")
                for profile in result.get('profiles', [])[:3]:
                    print(f"   • {profile.get('avatar_name', 'Unknown')}")
            else:
                print(f"❌ Error: {result.get('error')}")
            print()
        
        # Test 4: Find a post to like
        if any(t['name'] == 'like_post' for t in available_tools):
            print("4️⃣  Testing: Like a post")
            print("-" * 80)
            # Find a post
            post = await db.posts.find_one({
                "user_id": {"$ne": avatar_id},
                "post_type": "avatar",
                "liked_by": {"$ne": avatar_id}
            })
            
            if post:
                result = await mcp_client.like_post(avatar_id, post['id'])
                if result.get('success'):
                    print(f"✅ Liked post: {post['id']}")
                else:
                    print(f"❌ Error: {result.get('error')}")
            else:
                print("⚠️  No posts available to like")
            print()
        
        # Test 5: Create a post
        if any(t['name'] == 'create_post' for t in available_tools):
            print("5️⃣  Testing: Create a post (AI-generated)")
            print("-" * 80)
            result = await mcp_client.create_post(avatar_id, post_type="general")
            if result.get('success'):
                post_text = result.get('post_text', '')
                print(f"✅ Created post:")
                print(f"   {post_text[:100]}...")
                print(f"   Post ID: {result.get('post_id')}")
            else:
                print(f"❌ Error: {result.get('error')}")
            print()
        
        # Test 6: Test permission check
        print("6️⃣  Testing: Permission check")
        print("-" * 80)
        # Get avatar's permissions
        avatar_doc = await db.users.find_one({"id": avatar_id})
        actions_enabled = avatar_doc.get('avatar_actions_enabled', {})
        
        print("Avatar permissions:")
        for action, enabled in actions_enabled.items():
            status = "✅ Enabled" if enabled else "❌ Disabled"
            print(f"   {action:30s} {status}")
        print()
        
        # Summary
        print("=" * 80)
        print("✅ Test Complete")
        print("=" * 80)
        print()
        print("📝 Summary:")
        print(f"   • Total tools available: {len(tools)}")
        print(f"   • Tools available for {avatar_name}: {len(available_tools)}")
        print(f"   • Avatar permissions: {sum(actions_enabled.values())}/{len(actions_enabled)} enabled")
        print()
        print("💡 Tip: Use the frontend to enable/disable actions for each avatar")
        print("   The MCP server will automatically respect these permissions.")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(test_mcp_server())

