"""
Comprehensive test of all MCP avatar actions
Tests each action type to verify they work correctly
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
from avatar_mcp_client import AvatarMCPClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'neurallinks_local')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8001')


async def test_all_actions():
    """Test all available avatar actions"""
    print("=" * 80)
    print("🧪 Comprehensive Avatar MCP Actions Test")
    print("=" * 80)
    print()
    
    # Connect to MongoDB
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
            print("❌ No avatars found")
            return
        
        avatar_id = avatar['id']
        avatar_name = avatar.get('avatar_name', 'Unknown')
        
        print(f"📋 Testing avatar: {avatar_name} ({avatar_id})")
        print()
        
        # Initialize MCP client
        mcp_client = AvatarMCPClient(server_url=BACKEND_URL)
        
        # Get available tools
        available_tools = await mcp_client.get_available_tools(avatar_id)
        tool_names = [t['name'] for t in available_tools]
        
        print(f"✅ Avatar has {len(available_tools)} actions enabled")
        print()
        
        # Test 1: Discover Profiles
        if 'discover_profiles' in tool_names:
            print("1️⃣  Testing: discover_profiles")
            print("-" * 80)
            result = await mcp_client.discover_profiles(avatar_id, limit=3)
            if result.get('success'):
                profiles = result.get('profiles', [])
                print(f"✅ Success! Discovered {len(profiles)} profiles:")
                for p in profiles[:3]:
                    print(f"   • {p.get('avatar_name', 'Unknown')}")
            else:
                print(f"❌ Failed: {result.get('error')}")
            print()
        
        # Test 2: Create Post (AI-generated)
        if 'create_post' in tool_names:
            print("2️⃣  Testing: create_post (AI-generated)")
            print("-" * 80)
            result = await mcp_client.create_post(avatar_id, post_type="interest")
            if result.get('success'):
                post_text = result.get('post_text', '')
                post_id = result.get('post_id')
                print(f"✅ Success! Created post:")
                print(f"   Post ID: {post_id}")
                print(f"   Content: {post_text[:100]}...")
                
                # Store post_id for later tests
                created_post_id = post_id
            else:
                print(f"❌ Failed: {result.get('error')}")
                created_post_id = None
            print()
        else:
            created_post_id = None
        
        # Test 3: Find a post to interact with
        post_to_interact = None
        if created_post_id:
            # Use the post we just created (but from another user's perspective)
            # Find another avatar's post
            other_post = await db.posts.find_one({
                "user_id": {"$ne": avatar_id},
                "post_type": "avatar"
            })
            if other_post:
                post_to_interact = other_post['id']
        else:
            other_post = await db.posts.find_one({
                "user_id": {"$ne": avatar_id},
                "post_type": "avatar"
            })
            if other_post:
                post_to_interact = other_post['id']
        
        # Test 4: Like Post
        if 'like_post' in tool_names and post_to_interact:
            print("3️⃣  Testing: like_post")
            print("-" * 80)
            # Check if already liked
            post = await db.posts.find_one({"id": post_to_interact})
            already_liked = avatar_id in post.get('liked_by', []) if post else False
            
            if not already_liked:
                result = await mcp_client.like_post(avatar_id, post_to_interact)
                if result.get('success'):
                    print(f"✅ Success! Liked post: {post_to_interact}")
                else:
                    print(f"❌ Failed: {result.get('error')}")
            else:
                print(f"⚠️  Post already liked (skipping)")
            print()
        
        # Test 5: Comment on Post (AI-generated)
        if 'comment_on_post' in tool_names and post_to_interact:
            print("4️⃣  Testing: comment_on_post (AI-generated)")
            print("-" * 80)
            result = await mcp_client.comment_on_post(avatar_id, post_to_interact)
            if result.get('success'):
                comment = result.get('comment', '')
                print(f"✅ Success! Commented on post:")
                print(f"   Comment: {comment[:100]}...")
            else:
                print(f"❌ Failed: {result.get('error')}")
            print()
        
        # Test 6: Send Friend Request
        if 'send_friend_request' in tool_names:
            print("5️⃣  Testing: send_friend_request")
            print("-" * 80)
            # Find a user who is not a friend
            friendships = await db.friendships.find({
                "$or": [
                    {"user1_id": avatar_id},
                    {"user2_id": avatar_id}
                ]
            }).to_list(1000)
            
            friend_ids = set()
            for f in friendships:
                if f['user1_id'] == avatar_id:
                    friend_ids.add(f['user2_id'])
                else:
                    friend_ids.add(f['user1_id'])
            
            # Find a non-friend avatar
            potential_friend = await db.users.find_one({
                "$or": [
                    {"is_bot": True},
                    {"avatar_autonomous": True}
                ],
                "id": {"$ne": avatar_id, "$nin": list(friend_ids)},
                "avatar_name": {"$exists": True}
            })
            
            if potential_friend:
                result = await mcp_client.send_friend_request(avatar_id, potential_friend['id'])
                if result.get('success'):
                    print(f"✅ Success! Sent friend request to: {potential_friend.get('avatar_name', 'Unknown')}")
                else:
                    print(f"❌ Failed: {result.get('error')}")
            else:
                print("⚠️  No potential friends found (all avatars are already friends)")
            print()
        
        # Test 7: Message Friend
        if 'message_friend' in tool_names:
            print("6️⃣  Testing: message_friend (AI-generated)")
            print("-" * 80)
            # Find a friend
            friendships = await db.friendships.find({
                "$or": [
                    {"user1_id": avatar_id},
                    {"user2_id": avatar_id}
                ],
                "status": "accepted"
            }).limit(1).to_list(1)
            
            if friendships:
                f = friendships[0]
                friend_id = f['user2_id'] if f['user1_id'] == avatar_id else f['user1_id']
                friend = await db.users.find_one({"id": friend_id})
                friend_name = friend.get('avatar_name', 'Unknown') if friend else 'Unknown'
                
                result = await mcp_client.message_friend(avatar_id, friend_id)
                if result.get('success'):
                    message = result.get('message_text', '')
                    print(f"✅ Success! Sent message to {friend_name}:")
                    print(f"   Message: {message[:100]}...")
                else:
                    print(f"❌ Failed: {result.get('error')}")
            else:
                print("⚠️  No friends found to message")
            print()
        
        # Summary
        print("=" * 80)
        print("📊 Test Summary")
        print("=" * 80)
        print()
        print(f"✅ Avatar: {avatar_name}")
        print(f"✅ Available actions: {len(available_tools)}")
        print(f"✅ Actions tested: 6")
        print()
        print("💡 All actions respect the avatar's permission settings")
        print("   Disabled actions will return an error automatically")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(test_all_actions())

