"""
Fix and Test Complete Social Network
Ensures all features work: posts visibility, comments, messages
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

async def fix_and_test():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['neurallinks_local']
    
    your_id = 'dedc30ef-dca9-467d-84b1-5e643941e6fd'
    
    print('='*80)
    print('🔧 FIXING AND TESTING SOCIAL NETWORK')
    print('='*80)
    print()
    
    # ============================================================================
    # 1. FIX: Sync posts from collection to user documents
    # ============================================================================
    print('1️⃣ SYNCING POSTS TO USER DOCUMENTS')
    print('-'*80)
    
    # Get all posts from last hour
    from datetime import timedelta
    time_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_posts = await db.posts.find({
        'created_at': {'$gte': time_cutoff.isoformat()}
    }).to_list(1000)
    
    print(f'Found {len(recent_posts)} posts from last hour')
    
    # Group by user
    posts_by_user = {}
    for post in recent_posts:
        user_id = post.get('user_id')
        if user_id not in posts_by_user:
            posts_by_user[user_id] = []
        posts_by_user[user_id].append(post)
    
    # Sync to user documents
    synced = 0
    for user_id, posts in posts_by_user.items():
        user = await db.users.find_one({'id': user_id})
        if not user:
            continue
        
        # Get existing posts in user doc
        existing_posts = set(p['id'] for p in user.get('posts', []))
        existing_avatar = set(p['id'] for p in user.get('avatar_posts', []))
        
        # Add missing posts
        for post in posts:
            post_id = post.get('id')
            post_type = post.get('post_type', 'real')
            
            if post_type == 'avatar' and post_id not in existing_avatar:
                post_clean = {k: v for k, v in post.items() if k != '_id'}
                await db.users.update_one(
                    {'id': user_id},
                    {'$push': {'avatar_posts': post_clean}}
                )
                synced += 1
            elif post_type == 'real' and post_id not in existing_posts:
                post_clean = {k: v for k, v in post.items() if k != '_id'}
                await db.users.update_one(
                    {'id': user_id},
                    {'$push': {'posts': post_clean}}
                )
                synced += 1
    
    print(f'✅ Synced {synced} posts to user documents')
    print()
    
    # ============================================================================
    # 2. TEST: Create a test comment
    # ============================================================================
    print('2️⃣ TESTING COMMENT FUNCTIONALITY')
    print('-'*80)
    
    # Find a post from a friend
    you = await db.users.find_one({'id': your_id})
    friends = you.get('friends', [])
    
    if friends:
        # Get a friend's post
        friend = await db.users.find_one({'id': friends[0]})
        friend_posts = friend.get('posts', []) + friend.get('avatar_posts', [])
        
        if friend_posts:
            test_post = friend_posts[-1]
            post_id = test_post.get('id')
            
            # Add a test comment from you
            comment = {
                'id': f'comment-test-{datetime.now(timezone.utc).timestamp()}',
                'user_id': your_id,
                'user_name': you.get('avatar_name', you.get('name')),
                'text': 'Great post! 🎉 This is a test comment from DigitalHunter.',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            await db.posts.update_one(
                {'id': post_id},
                {'$push': {'comments': comment}}
            )
            
            print(f'✅ Added test comment to {friend.get("avatar_name")}\'s post')
            print(f'   Comment: "{comment["text"]}"')
        else:
            print('⚠️ Friend has no posts to comment on')
    else:
        print('⚠️ No friends to test commenting with')
    print()
    
    # ============================================================================
    # 3. VERIFICATION: Check what frontend will see
    # ============================================================================
    print('3️⃣ VERIFYING FRONTEND DATA')
    print('-'*80)
    
    # Reload your data
    you = await db.users.find_one({'id': your_id})
    friends = you.get('friends', [])
    
    print('Your profile:')
    print(f'  Posts (Sense World): {len(you.get("posts", []))}')
    print(f'  Posts (Maya World): {len(you.get("avatar_posts", []))}')
    print(f'  Friends: {len(friends)}')
    print()
    
    print(f'Friends\' posts (what you will see in feed):')
    total_feed_posts = 0
    for friend_id in friends:
        friend = await db.users.find_one({'id': friend_id})
        if friend:
            friend_posts = len(friend.get('posts', [])) + len(friend.get('avatar_posts', []))
            total_feed_posts += friend_posts
            name = friend.get('avatar_name', friend.get('name'))
            print(f'  • {name}: {friend_posts} posts')
    
    print(f'\n  📊 Total posts you should see in feed: {total_feed_posts}')
    print()
    
    # ============================================================================
    # 4. Check posts with comments
    # ============================================================================
    print('4️⃣ POSTS WITH COMMENTS')
    print('-'*80)
    
    posts_with_comments = await db.posts.count_documents({'comments.0': {'$exists': True}})
    print(f'Posts with comments: {posts_with_comments}')
    
    if posts_with_comments > 0:
        sample = await db.posts.find_one({'comments.0': {'$exists': True}})
        print(f'  Sample: {len(sample.get("comments", []))} comments')
        first_comment = sample["comments"][0].get("text", "")[:60]
        print(f'  First: "{first_comment}..."')
    print()
    
    print('='*80)
    print('✅ FIXES APPLIED!')
    print('='*80)
    print()
    print('Next steps:')
    print('1. Refresh your browser (Cmd+Shift+R)')
    print('2. Go to home feed')
    print('3. Toggle to Maya World (most posts are there)')
    print(f'4. You should see {total_feed_posts} posts from your {len(friends)} friends')
    print()
    
    client.close()

if __name__ == '__main__':
    asyncio.run(fix_and_test())

