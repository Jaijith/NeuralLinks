"""
Fix likes tracking - Initialize liked_by arrays for posts that have likes but no tracking
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_likes():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['neurallinks_local']
    
    print('🔧 FIXING LIKES TRACKING')
    print('='*80)
    print()
    
    # Find posts with likes but no liked_by array
    posts_to_fix = await db.posts.find({
        'likes': {'$gt': 0},
        '$or': [
            {'liked_by': {'$exists': False}},
            {'liked_by': []}
        ]
    }).to_list(1000)
    
    print(f'Found {len(posts_to_fix)} posts with likes but no liked_by tracking')
    print()
    
    # For each post, we can't recover who liked (data is lost)
    # But we can initialize the array so future likes work
    fixed = 0
    for post in posts_to_fix:
        # Initialize liked_by as empty array (we don't know who liked before)
        await db.posts.update_one(
            {'id': post['id']},
            {'$set': {'liked_by': []}}
        )
        fixed += 1
    
    print(f'✅ Initialized liked_by arrays for {fixed} posts')
    print()
    print('⚠️ Note: Old likes cannot be recovered, but NEW likes will track properly!')
    print()
    
    # Verify recent posts have proper tracking
    recent_posts = await db.posts.find({
        'created_at': {'$regex': '^2025-11-04'}
    }).limit(10).to_list(10)
    
    print(f'📊 Recent posts (today) tracking:')
    for post in recent_posts:
        has_array = 'liked_by' in post
        likes = post.get('likes', 0)
        liked_by_count = len(post.get('liked_by', []))
        status = '✅' if has_array else '❌'
        print(f'{status} Post {post.get("id", "")[:20]}... - likes={likes}, tracked={liked_by_count}')
    
    client.close()

if __name__ == '__main__':
    asyncio.run(fix_likes())




