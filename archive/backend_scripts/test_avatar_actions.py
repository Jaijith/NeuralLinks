"""
Test script to verify that each avatar can perform all enabled actions
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'neurallinks_local')

# All available actions
ALL_ACTIONS = [
    'like_posts',
    'comment_posts',
    'create_posts',
    'send_friend_requests',
    'accept_friend_requests',
    'message_friends',
    'discover_profiles',
    'share_posts'
]

# Action descriptions
ACTION_DESCRIPTIONS = {
    'like_posts': 'Like posts from friends',
    'comment_posts': 'Comment on posts from friends',
    'create_posts': 'Create and publish new posts',
    'send_friend_requests': 'Send friend requests to other avatars',
    'accept_friend_requests': 'Accept incoming friend requests',
    'message_friends': 'Send messages to friends',
    'discover_profiles': 'Browse and view other profiles',
    'share_posts': 'Share posts (not yet implemented)'
}


async def get_all_avatars(db):
    """Get all avatars (bots + user avatars with autonomy)"""
    avatars = await db.users.find({
        "$or": [
            {"is_bot": True},
            {"avatar_autonomous": True}
        ],
        "avatar_name": {"$exists": True}
    }).to_list(1000)
    
    return avatars


async def check_action_implementation(action_key: str, db, avatar: Dict) -> Dict[str, Any]:
    """Check if an action is properly implemented and can be tested"""
    avatar_id = avatar['id']
    avatar_name = avatar.get('avatar_name', avatar.get('name', 'Unknown'))
    
    result = {
        'action': action_key,
        'enabled': avatar.get('avatar_actions_enabled', {}).get(action_key, True),
        'can_test': False,
        'test_result': None,
        'error': None,
        'details': {}
    }
    
    try:
        if action_key == 'like_posts':
            # Check if there are posts to like
            posts = await db.posts.find({
                "user_id": {"$ne": avatar_id},
                "post_type": "avatar",
                "liked_by": {"$ne": avatar_id}  # Not already liked
            }).limit(1).to_list(1)
            
            if posts:
                result['can_test'] = True
                result['test_result'] = '✅ Can test (posts available)'
                result['details'] = {'posts_available': len(posts)}
            else:
                result['can_test'] = False
                result['test_result'] = '⚠️  Cannot test (no posts available)'
                result['details'] = {'posts_available': 0}
        
        elif action_key == 'comment_posts':
            # Check if there are posts to comment on
            posts = await db.posts.find({
                "user_id": {"$ne": avatar_id},
                "post_type": "avatar"
            }).limit(1).to_list(1)
            
            if posts:
                result['can_test'] = True
                result['test_result'] = '✅ Can test (posts available)'
                result['details'] = {'posts_available': len(posts)}
            else:
                result['can_test'] = False
                result['test_result'] = '⚠️  Cannot test (no posts available)'
                result['details'] = {'posts_available': 0}
        
        elif action_key == 'create_posts':
            # Can always test post creation
            result['can_test'] = True
            result['test_result'] = '✅ Can test'
            result['details'] = {'always_available': True}
        
        elif action_key == 'send_friend_requests':
            # Check if there are potential friends
            # Get current friends
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
            
            # Find avatars not yet friends
            potential_friends = await db.users.find({
                "$or": [
                    {"is_bot": True},
                    {"avatar_autonomous": True}
                ],
                "id": {"$ne": avatar_id, "$nin": list(friend_ids)},
                "avatar_name": {"$exists": True}
            }).limit(1).to_list(1)
            
            if potential_friends:
                result['can_test'] = True
                result['test_result'] = '✅ Can test (potential friends available)'
                result['details'] = {'potential_friends': len(potential_friends)}
            else:
                result['can_test'] = False
                result['test_result'] = '⚠️  Cannot test (no potential friends)'
                result['details'] = {'potential_friends': 0}
        
        elif action_key == 'accept_friend_requests':
            # Check if there are pending friend requests
            # Note: The current implementation uses a different friendship model
            # Check for any pending requests
            pending_requests = await db.friendships.find({
                "$or": [
                    {"user1_id": avatar_id, "status": "pending"},
                    {"user2_id": avatar_id, "status": "pending"}
                ]
            }).limit(1).to_list(1)
            
            if pending_requests:
                result['can_test'] = True
                result['test_result'] = '✅ Can test (pending requests available)'
                result['details'] = {'pending_requests': len(pending_requests)}
            else:
                result['can_test'] = False
                result['test_result'] = '⚠️  Cannot test (no pending requests)'
                result['details'] = {'pending_requests': 0}
        
        elif action_key == 'message_friends':
            # Check if avatar has friends to message
            friendships = await db.friendships.find({
                "$or": [
                    {"user1_id": avatar_id},
                    {"user2_id": avatar_id}
                ]
            }).to_list(1000)
            
            if friendships:
                result['can_test'] = True
                result['test_result'] = '✅ Can test (has friends)'
                result['details'] = {'friends_count': len(friendships)}
            else:
                result['can_test'] = False
                result['test_result'] = '⚠️  Cannot test (no friends)'
                result['details'] = {'friends_count': 0}
        
        elif action_key == 'discover_profiles':
            # Can always test profile discovery
            other_avatars = await db.users.find({
                "$or": [
                    {"is_bot": True},
                    {"avatar_autonomous": True}
                ],
                "id": {"$ne": avatar_id},
                "avatar_name": {"$exists": True}
            }).limit(1).to_list(1)
            
            if other_avatars:
                result['can_test'] = True
                result['test_result'] = '✅ Can test (other avatars available)'
                result['details'] = {'other_avatars': len(other_avatars)}
            else:
                result['can_test'] = False
                result['test_result'] = '⚠️  Cannot test (no other avatars)'
                result['details'] = {'other_avatars': 0}
        
        elif action_key == 'share_posts':
            # Not yet implemented
            result['can_test'] = False
            result['test_result'] = '❌ Not implemented'
            result['details'] = {'implementation_status': 'not_implemented'}
        
    except Exception as e:
        result['error'] = str(e)
        result['test_result'] = f'❌ Error: {e}'
    
    return result


async def test_avatar_actions():
    """Main test function"""
    print("=" * 80)
    print("🧪 Avatar Actions Test Suite")
    print("=" * 80)
    print()
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Test connection
        await db.command("ping")
        print("✅ Connected to MongoDB")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return
    
    # Get all avatars
    print("📋 Fetching all avatars...")
    avatars = await get_all_avatars(db)
    print(f"✅ Found {len(avatars)} avatars")
    print()
    
    if not avatars:
        print("⚠️  No avatars found. Please create some avatars first.")
        return
    
    # Test each avatar
    results = []
    
    for avatar in avatars:
        avatar_id = avatar['id']
        avatar_name = avatar.get('avatar_name', avatar.get('name', 'Unknown'))
        is_bot = avatar.get('is_bot', False)
        avatar_type = "🤖 Bot" if is_bot else "✨ User Avatar"
        autonomous = avatar.get('avatar_autonomous', False)
        
        print("=" * 80)
        print(f"Testing: {avatar_name} ({avatar_type})")
        print("=" * 80)
        
        if not autonomous and not is_bot:
            print("⚠️  Autonomy not enabled - skipping")
            print()
            continue
        
        # Get action permissions
        actions_enabled = avatar.get('avatar_actions_enabled', {})
        
        print(f"\n📊 Action Permissions:")
        for action in ALL_ACTIONS:
            enabled = actions_enabled.get(action, True)
            status = "✅ Enabled" if enabled else "❌ Disabled"
            print(f"   {action:25s} {status}")
        
        print(f"\n🧪 Testing Actions:")
        
        avatar_results = {
            'avatar_id': avatar_id,
            'avatar_name': avatar_name,
            'avatar_type': avatar_type,
            'actions': []
        }
        
        for action in ALL_ACTIONS:
            enabled = actions_enabled.get(action, True)
            
            if not enabled:
                print(f"   ⏭️  {action:25s} - Skipped (disabled)")
                avatar_results['actions'].append({
                    'action': action,
                    'enabled': False,
                    'skipped': True
                })
                continue
            
            # Check if action can be tested
            test_result = await check_action_implementation(action, db, avatar)
            avatar_results['actions'].append(test_result)
            
            status_icon = "✅" if test_result['can_test'] else "⚠️ "
            print(f"   {status_icon} {action:25s} - {test_result['test_result']}")
            
            if test_result.get('error'):
                print(f"      Error: {test_result['error']}")
        
        results.append(avatar_results)
        print()
    
    # Summary
    print("=" * 80)
    print("📊 Summary")
    print("=" * 80)
    print()
    
    total_avatars = len(results)
    total_actions_tested = sum(len(r['actions']) for r in results)
    total_enabled = sum(
        sum(1 for a in r['actions'] if a.get('enabled', False))
        for r in results
    )
    total_testable = sum(
        sum(1 for a in r['actions'] if a.get('can_test', False))
        for r in results
    )
    
    print(f"Total Avatars Tested: {total_avatars}")
    print(f"Total Actions Checked: {total_actions_tested}")
    print(f"Actions Enabled: {total_enabled}")
    print(f"Actions Testable: {total_testable}")
    print()
    
    # Per-action summary
    print("📈 Per-Action Summary:")
    for action in ALL_ACTIONS:
        enabled_count = sum(
            sum(1 for a in r['actions'] if a.get('action') == action and a.get('enabled', False))
            for r in results
        )
        testable_count = sum(
            sum(1 for a in r['actions'] if a.get('action') == action and a.get('can_test', False))
            for r in results
        )
        
        print(f"   {action:25s} - Enabled: {enabled_count:3d} | Testable: {testable_count:3d}")
    
    print()
    print("=" * 80)
    print("✅ Test Complete")
    print("=" * 80)
    
    client.close()


if __name__ == "__main__":
    asyncio.run(test_avatar_actions())

