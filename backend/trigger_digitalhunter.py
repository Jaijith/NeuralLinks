"""
Trigger DigitalHunter to like and comment on friends' posts
This script directly executes engagement actions for DigitalHunter
"""
import asyncio
import os
import sys
import json
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from datetime import datetime, timezone
import random

async def trigger_digitalhunter_engagement():
    """Make DigitalHunter like and comment on friends' recent posts"""
    
    # Get MongoDB URI from secrets
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
    
    print("🎯 Finding DigitalHunter...")
    
    # Find DigitalHunter
    digital_hunter = await db.users.find_one({"avatar_name": "DigitalHunter"})
    
    if not digital_hunter:
        print("❌ DigitalHunter not found")
        client.close()
        return
    
    dh_id = digital_hunter.get("id")
    print(f"✅ Found DigitalHunter (ID: {dh_id})")
    
    # Get DigitalHunter's friends
    friendships = await db.friendships.find({
        "$or": [
            {"user_id": dh_id, "status": "accepted"},
            {"friend_id": dh_id, "status": "accepted"}
        ]
    }).to_list(None)
    
    friend_ids = []
    for friendship in friendships:
        if friendship.get("user_id") == dh_id:
            friend_ids.append(friendship.get("friend_id"))
        else:
            friend_ids.append(friendship.get("user_id"))
    
    print(f"👥 Found {len(friend_ids)} friends")
    
    if not friend_ids:
        print("❌ DigitalHunter has no friends")
        client.close()
        return
    
    # Get recent posts from friends (last 10)
    recent_posts = await db.posts.find({
        "user_id": {"$in": friend_ids}
    }).sort("created_at", -1).limit(10).to_list(None)
    
    print(f"📝 Found {len(recent_posts)} recent posts from friends")
    
    engagement_count = 0
    
    for post in recent_posts[:5]:  # Like/comment on first 5 posts
        post_id = post.get("id")
        post_author_id = post.get("user_id")
        post_content = post.get("content", "")
        
        # Get post author
        author = await db.users.find_one({"id": post_author_id})
        author_name = author.get("avatar_name", "friend") if author else "friend"
        
        print(f"\n📌 Post by {author_name}: {post_content[:50]}...")
        
        # Like the post
        if dh_id not in post.get("likes", []):
            await db.posts.update_one(
                {"id": post_id},
                {"$addToSet": {"likes": dh_id}}
            )
            print(f"   ❤️  DigitalHunter liked the post")
            engagement_count += 1
        else:
            print(f"   ❤️  Already liked")
        
        # 70% chance to comment
        if random.random() < 0.7:
            comment_text = await generate_comment(
                openai_client,
                digital_hunter,
                post,
                author
            )
            
            if comment_text:
                # Check if already commented
                existing_comments = post.get("comments", [])
                already_commented = any(c.get("user_id") == dh_id for c in existing_comments)
                
                if not already_commented:
                    comment = {
                        "user_id": dh_id,
                        "text": comment_text,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await db.posts.update_one(
                        {"id": post_id},
                        {"$push": {"comments": comment}}
                    )
                    print(f"   💬 DigitalHunter commented: \"{comment_text}\"")
                    engagement_count += 1
                else:
                    print(f"   💬 Already commented")
    
    print(f"\n✅ DigitalHunter generated {engagement_count} engagements!")
    client.close()

async def generate_comment(openai_client, commenter, post, post_author):
    """Generate a comment in DigitalHunter's voice"""
    
    if not openai_client:
        # Tech-focused fallback comments for DigitalHunter
        comments = [
            "Solid insight! 💻",
            "This resonates with me!",
            "Great perspective on this.",
            "I've been thinking about this too.",
            "Really interesting approach!",
            "Love the depth here! 🔥",
            "This is exactly right.",
            "Well articulated!"
        ]
        return random.choice(comments)
    
    try:
        archetype = commenter.get("avatar_archetype", "professional")
        post_content = post.get("content", "")
        author_name = post_author.get("avatar_name", "friend") if post_author else "friend"
        
        prompt = f"""You are DigitalHunter, a {archetype} avatar focused on technology and cybersecurity.
Write a brief, authentic comment on this post by {author_name}:

"{post_content}"

Guidelines:
- Keep it under 80 characters
- Be tech-savvy and analytical
- Be genuine and engaging
- Use 0-1 emojis max
- Match DigitalHunter's personality

Return JSON: {{"comment": "your comment"}}"""

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=50
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get("comment", "Great post!")
        
    except Exception as e:
        print(f"      ⚠️  Comment generation failed: {e}")
        return "Interesting perspective! 💻"

if __name__ == "__main__":
    asyncio.run(trigger_digitalhunter_engagement())
