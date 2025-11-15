"""
Comprehensive Social Network System Check
Tests all features: posting, liking, commenting, messaging in both worlds
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta

async def comprehensive_check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['neurallinks_local']
    
    your_id = 'dedc30ef-dca9-467d-84b1-5e643941e6fd'
    
    print('='*80)
    print('🔍 COMPREHENSIVE SOCIAL NETWORK SYSTEM CHECK')
    print('='*80)
    print()
    
    # ============================================================================
    # 1. USER & AVATAR CHECK
    # ============================================================================
    print('1️⃣ YOUR PROFILE CHECK')
    print('-'*80)
    you = await db.users.find_one({'id': your_id})
    if you:
        print(f'✅ User found: {you.get("email")}')
        print(f'   Name: {you.get("name")}')
        print(f'   Avatar: {you.get("avatar_name", "NOT SET")}')
        print(f'   Friends: {len(you.get("friends", []))}')
        print(f'   Avatar Autonomous: {you.get("avatar_autonomous", False)}')
        print(f'   Activity Level: {you.get("avatar_activity_level", "NOT SET")}')
        print(f'   Archetype: {you.get("archetype", "NOT SET")}')
    else:
        print('❌ User not found!')
        return
    print()
    
    # ============================================================================
    # 2. POSTS CHECK (BOTH WORLDS)
    # ============================================================================
    print('2️⃣ POSTS CHECK')
    print('-'*80)
    
    # Your posts
    your_posts = await db.posts.find({'user_id': your_id}).to_list(100)
    print(f'Your posts in collection: {len(your_posts)}')
    print(f'Your posts in user doc - Sense World: {len(you.get("posts", []))}')
    print(f'Your posts in user doc - Maya World: {len(you.get("avatar_posts", []))}')
    
    if your_posts:
        print('\n  Last 3 posts:')
        for post in your_posts[-3:]:
            print(f'  • [{post.get("created_at", "")[:19]}] ({post.get("post_type")}) {post.get("text", "")[:50]}...')
    else:
        print('  ⚠️ No posts from you yet')
    print()
    
    # Friends' posts
    friends = you.get('friends', [])
    print(f'📊 Checking {len(friends)} friends for posts...')
    
    friends_with_posts = []
    for friend_id in friends:
        friend = await db.users.find_one({'id': friend_id})
        if friend:
            friend_posts = friend.get('posts', []) + friend.get('avatar_posts', [])
            if friend_posts:
                friends_with_posts.append({
                    'name': friend.get('avatar_name', friend.get('name')),
                    'posts': len(friend_posts),
                    'latest': friend_posts[-1] if friend_posts else None
                })
    
    print(f'\n  Friends with posts: {len(friends_with_posts)}/{len(friends)}')
    for friend in friends_with_posts[:5]:
        print(f'  • {friend["name"]}: {friend["posts"]} posts')
        if friend['latest']:
            print(f'    Latest: "{friend["latest"].get("text", "")[:50]}..."')
    print()
    
    # ============================================================================
    # 3. LIKES CHECK
    # ============================================================================
    print('3️⃣ LIKES CHECK')
    print('-'*80)
    
    posts_with_likes = await db.posts.count_documents({'likes': {'$gt': 0}})
    print(f'Posts with likes: {posts_with_likes}')
    
    if posts_with_likes > 0:
        sample = await db.posts.find_one({'likes': {'$gt': 0}})
        if sample:
            print(f'  Sample: Post by {sample.get("user_id")[:20]} has {sample.get("likes", 0)} likes')
    else:
        print('  ⚠️ No likes yet in the system')
    print()
    
    # ============================================================================
    # 4. COMMENTS CHECK
    # ============================================================================
    print('4️⃣ COMMENTS CHECK')
    print('-'*80)
    
    posts_with_comments = await db.posts.count_documents({'comments.0': {'$exists': True}})
    print(f'Posts with comments: {posts_with_comments}')
    
    if posts_with_comments > 0:
        sample = await db.posts.find_one({'comments.0': {'$exists': True}})
        if sample:
            print(f'  Sample: Post has {len(sample.get("comments", []))} comments')
            if sample['comments']:
                print(f'  First comment: "{sample["comments"][0].get("text", "")[:50]}..."')
    else:
        print('  ⚠️ No comments yet in the system')
    print()
    
    # ============================================================================
    # 5. MESSAGES CHECK
    # ============================================================================
    print('5️⃣ MESSAGES CHECK')
    print('-'*80)
    
    # Check if conversations collection exists
    conversations = await db.conversations.count_documents({})
    print(f'Total conversations: {conversations}')
    
    your_conversations = await db.conversations.count_documents({
        '$or': [
            {'participants': your_id}
        ]
    })
    print(f'Your conversations: {your_conversations}')
    
    if your_conversations > 0:
        conv = await db.conversations.find_one({'participants': your_id})
        if conv:
            messages = conv.get('messages', [])
            print(f'  Sample conversation has {len(messages)} messages')
    else:
        print('  ⚠️ No conversations yet')
    print()
    
    # ============================================================================
    # 6. AUTONOMOUS ACTIVITY CHECK
    # ============================================================================
    print('6️⃣ AUTONOMOUS ACTIVITY CHECK (Last 30 min)')
    print('-'*80)
    
    time_cutoff = datetime.utcnow() - timedelta(minutes=30)
    recent_posts = await db.posts.find({
        'created_at': {'$gte': time_cutoff.isoformat()}
    }).to_list(100)
    
    print(f'Posts created in last 30 min: {len(recent_posts)}')
    
    # Group by user
    post_by_user = {}
    for post in recent_posts:
        user_id = post.get('user_id')
        post_by_user[user_id] = post_by_user.get(user_id, 0) + 1
    
    print(f'Active users posting: {len(post_by_user)}')
    
    # Check if DigitalHunter posted
    if your_id in post_by_user:
        print(f'  ✅ DigitalHunter posted {post_by_user[your_id]} times')
    else:
        print(f'  ⚠️ DigitalHunter has NOT posted in last 30 min')
    
    # Show most active
    sorted_users = sorted(post_by_user.items(), key=lambda x: x[1], reverse=True)
    print(f'\n  Most active posters:')
    for user_id, count in sorted_users[:5]:
        user = await db.users.find_one({'id': user_id})
        name = user.get('avatar_name', user.get('name', 'Unknown')) if user else 'Unknown'
        icon = '✨' if user_id == your_id else '🤖'
        print(f'  {icon} {name}: {count} posts')
    print()
    
    # ============================================================================
    # 7. SYSTEM CONFIGURATION CHECK
    # ============================================================================
    print('7️⃣ SYSTEM CONFIGURATION')
    print('-'*80)
    
    total_users = await db.users.count_documents({})
    bots = await db.users.count_documents({'is_bot': True})
    real_users = total_users - bots
    autonomous_avatars = await db.users.count_documents({'avatar_autonomous': True})
    
    print(f'Total users: {total_users}')
    print(f'  Bots: {bots}')
    print(f'  Real users: {real_users}')
    print(f'  Autonomous avatars: {autonomous_avatars}')
    print()
    
    # ============================================================================
    # 8. ISSUES SUMMARY
    # ============================================================================
    print('='*80)
    print('📋 ISSUES SUMMARY')
    print('='*80)
    
    issues = []
    
    if len(you.get('friends', [])) == 0:
        issues.append('❌ You have no friends - feed will be empty')
    
    if not you.get('avatar_autonomous'):
        issues.append('❌ Avatar autonomy is OFF - DigitalHunter won\'t post automatically')
    
    if your_id not in post_by_user:
        issues.append('⚠️ DigitalHunter hasn\'t posted in last 30 min (may need more cycles)')
    
    if posts_with_likes == 0:
        issues.append('⚠️ No likes in the system yet (autonomous agents need to like posts)')
    
    if posts_with_comments == 0:
        issues.append('⚠️ No comments yet (autonomous agents need to comment)')
    
    if conversations == 0:
        issues.append('⚠️ No messages yet (messaging system not tested)')
    
    if len(friends_with_posts) < len(friends):
        issues.append(f'⚠️ Only {len(friends_with_posts)}/{len(friends)} friends have posts')
    
    if issues:
        for issue in issues:
            print(issue)
    else:
        print('✅ ALL SYSTEMS OPERATIONAL!')
    
    print()
    print('='*80)
    
    client.close()

if __name__ == '__main__':
    asyncio.run(comprehensive_check())




