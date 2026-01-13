"""
Trigger engagement (likes and comments) on recent posts
This script will have avatars like and comment on recent posts from their friends
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from datetime import datetime, timezone, timedelta
import random

async def trigger_engagement():
    """Trigger likes and comments on recent posts"""
    
    # Get secrets from environment (set by caller)
    mongodb_uri = os.environ.get('MONGODB_URI')
    openai_key = os.environ.get('OPENAI_API_KEY')
    
    if not mongodb_uri:
        print("❌ MONGODB_URI not set")
        return
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_uri)
    db = client['neurallinks_local']
    
    # Initialize OpenAI
    openai_client = AsyncOpenAI(api_key=openai_key) if openai_key else None
    
    print("🎯 Finding recent posts to engage with...")
    
    # Get the last 3 posts
    recent_posts = await db.posts.find().sort("created_at", -1).limit(3).to_list(None)
    
    if not recent_posts:
        print("❌ No posts found")
        return
    
    print(f"📝 Found {len(recent_posts)} recent posts:")
    for post in recent_posts:
        author = await db.users.find_one({"id": post.get("user_id")})
        author_name = author.get("avatar_name") if author else "Unknown"
        print(f"   - Post by {author_name}: {post.get('content', '')[:50]}...")
    
    # Get all avatars with permissions enabled
    avatars = await db.users.find({
        "avatar_enabled": True,
        "avatar_permissions.like_post": True
    }).to_list(None)
    
    print(f"\n👥 Found {len(avatars)} avatars with like permissions")
    
    engagement_count = 0
    
    for post in recent_posts:
        post_id = post.get("id")
        post_author_id = post.get("user_id")
        
        # Get post author info
        post_author = await db.users.find_one({"id": post_author_id})
        post_author_name = post_author.get("avatar_name") if post_author else "Unknown"
        
        print(f"\n📌 Processing post by {post_author_name}...")
        
        # Get 3-5 random avatars who are friends with the post author
        potential_engagers = []
        
        for avatar in avatars:
            avatar_id = avatar.get("id")
            
            # Don't like your own post
            if avatar_id == post_author_id:
                continue
            
            # Check if they're friends
            friendship = await db.friendships.find_one({
                "$or": [
                    {"user_id": avatar_id, "friend_id": post_author_id, "status": "accepted"},
                    {"user_id": post_author_id, "friend_id": avatar_id, "status": "accepted"}
                ]
            })
            
            if friendship:
                potential_engagers.append(avatar)
        
        # Select 3-5 random friends to engage
        num_engagers = min(random.randint(3, 5), len(potential_engagers))
        engagers = random.sample(potential_engagers, num_engagers) if potential_engagers else []
        
        print(f"   👍 Selected {len(engagers)} friends to engage")
        
        for engager in engagers:
            engager_id = engager.get("id")
            engager_name = engager.get("avatar_name", "Unknown")
            
            # Like the post
            if engager_id not in post.get("likes", []):
                await db.posts.update_one(
                    {"id": post_id},
                    {"$addToSet": {"likes": engager_id}}
                )
                print(f"      ❤️  {engager_name} liked the post")
                engagement_count += 1
            
            # 60% chance to also comment
            if random.random() < 0.6:
                # Generate comment
                comment_text = await generate_comment(
                    openai_client,
                    engager,
                    post,
                    post_author
                )
                
                if comment_text:
                    comment = {
                        "user_id": engager_id,
                        "text": comment_text,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await db.posts.update_one(
                        {"id": post_id},
                        {"$push": {"comments": comment}}
                    )
                    print(f"      💬 {engager_name} commented: \"{comment_text[:40]}...\"")
                    engagement_count += 1
    
    print(f"\n✅ Generated {engagement_count} engagements!")
    client.close()

async def generate_comment(openai_client, commenter, post, post_author):
    """Generate a contextual comment"""
    
    if not openai_client:
        # Fallback comments
        comments = [
            "Great post!",
            "Love this! 🔥",
            "Totally agree!",
            "This is awesome!",
            "Well said!",
            "Interesting perspective!",
            "Thanks for sharing!",
            "So true! 💯"
        ]
        return random.choice(comments)
    
    try:
        commenter_name = commenter.get("avatar_name", "Unknown")
        commenter_archetype = commenter.get("avatar_archetype", "professional")
        post_content = post.get("content", "")
        author_name = post_author.get("avatar_name", "friend") if post_author else "friend"
        
        prompt = f"""You are {commenter_name}, a {commenter_archetype} avatar. 
Write a brief, authentic comment on this post by {author_name}:

"{post_content}"

Guidelines:
- Keep it under 100 characters
- Be authentic to your {commenter_archetype} persona
- Be positive and engaging
- Use emojis sparingly (0-1)
- Don't be overly formal

Return JSON: {{"comment": "your comment"}}"""

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=50
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return result.get("comment", "Great post!")
        
    except Exception as e:
        print(f"      ⚠️  Comment generation failed: {e}")
        return "Great post!"

if __name__ == "__main__":
    asyncio.run(trigger_engagement())
