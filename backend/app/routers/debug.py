"""
Simple API endpoint to trigger engagement for specific avatars
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from core.config import OPENAI_MODEL

router = APIRouter(prefix="/api/debug", tags=["debug"])
logger = logging.getLogger(__name__)


@router.get("/list-avatars")
async def list_avatars():
    """
    List all avatars in the system
    """
    try:
        from core.database import get_database
        
        db = get_database()
        
        # Find all users with avatar_name set
        users = await db.users.find(
            {"avatar_name": {"$exists": True, "$ne": None, "$ne": ""}},
            {"_id": 0, "id": 1, "avatar_name": 1, "avatar_enabled": 1, "is_bot": 1}
        ).to_list(None)
        
        return {
            "success": True,
            "avatars": users,
            "count": len(users)
        }
        
    except Exception as e:
        logger.error(f"Failed to list avatars: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/receive-engagement/{avatar_name}")
async def receive_engagement(avatar_name: str, num_posts: Optional[int] = 3):
    """
    Have all friends engage with a specific avatar's posts
    This is the reverse of trigger-engagement - instead of the avatar engaging with friends,
    friends engage with the avatar's posts
    
    Args:
        avatar_name: Name of the avatar whose posts should receive engagement
        num_posts: Number of recent posts to engage with (default: 3)
    """
    try:
        from core.database import get_database
        from core.config import get_openai_client
        from datetime import datetime, timezone
        import random
        
        db = get_database()
        openai_client = get_openai_client()
        
        # Find the avatar
        avatar = await db.users.find_one({"avatar_name": avatar_name})
        
        if not avatar:
            raise HTTPException(status_code=404, detail=f"Avatar '{avatar_name}' not found")
        
        avatar_id = avatar.get("id")
        
        # Get friends
        friendships = await db.friendships.find({
            "$or": [
                {"user_id": avatar_id, "status": "accepted"},
                {"friend_id": avatar_id, "status": "accepted"}
            ]
        }).to_list(None)
        
        friend_ids = []
        for friendship in friendships:
            if friendship.get("user_id") == avatar_id:
                friend_ids.append(friendship.get("friend_id"))
            else:
                friend_ids.append(friendship.get("user_id"))
        
        if not friend_ids:
            return {"success": False, "message": f"{avatar_name} has no friends"}
        
        # Get recent posts from the avatar
        recent_posts = await db.posts.find({
            "user_id": avatar_id
        }).sort("created_at", -1).limit(num_posts).to_list(None)
        
        if not recent_posts:
            return {"success": False, "message": f"{avatar_name} has no posts"}
        
        # Get friend details
        friends = await db.users.find({
            "id": {"$in": friend_ids}
        }).to_list(None)
        
        engagements = []
        
        # Have each friend engage with the posts
        for post in recent_posts:
            post_id = post.get("id")
            post_content = post.get("content", post.get("text", ""))
            
            # Randomly select friends to engage (50-80% of friends per post)
            engaging_friends = random.sample(friends, k=random.randint(int(len(friends)*0.5), int(len(friends)*0.8)))
            
            for friend in engaging_friends:
                friend_id = friend.get("id")
                friend_name = friend.get("avatar_name") or friend.get("display_name") or friend.get("name", "Unknown")
                
                # Like the post - fix schema first if needed
                post_likes = post.get("likes", [])
                liked_by = post.get("liked_by", [])
                
                # Fix likes field if it's not a list
                if not isinstance(post_likes, list):
                    # Migrate from integer to array
                    await db.posts.update_one(
                        {"id": post_id},
                        {
                            "$set": {
                                "likes": [],
                                "liked_by": []
                            }
                        }
                    )
                    post_likes = []
                    liked_by = []
                
                if friend_id not in liked_by:
                    await db.posts.update_one(
                        {"id": post_id},
                        {
                            "$addToSet": {
                                "likes": friend_id,
                                "liked_by": friend_id
                            }
                        }
                    )
                    engagements.append({
                        "type": "like",
                        "post_id": post_id,
                        "from": friend_name
                    })
                
                # 60% chance to comment
                if random.random() < 0.6:
                    existing_comments = post.get("comments", [])
                    if not isinstance(existing_comments, list):
                        existing_comments = []
                    
                    already_commented = any(c.get("user_id") == friend_id for c in existing_comments)
                    
                    if not already_commented:
                        # Generate comment
                        comment_text = await generate_comment_for_avatar(
                            openai_client,
                            friend,
                            post,
                            db
                        )
                        
                        comment = {
                            "user_id": friend_id,
                            "user_name": friend_name,
                            "user_picture": friend.get("avatar_picture", friend.get("picture", "")),
                            "text": comment_text,
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                        
                        await db.posts.update_one(
                            {"id": post_id},
                            {"$push": {"comments": comment}}
                        )
                        engagements.append({
                            "type": "comment",
                            "post_id": post_id,
                            "from": friend_name,
                            "text": comment_text
                        })
        
        return {
            "success": True,
            "avatar": avatar_name,
            "friends_count": len(friends),
            "posts_engaged": len(recent_posts),
            "engagements": engagements,
            "total_engagements": len(engagements)
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger receive engagement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix-comment-names")
async def fix_comment_names():
    """
    Fix comments that have user_id but no user_name
    Updates all comments with "Unknown" or missing user_name
    """
    try:
        from core.database import get_database
        
        db = get_database()
        
        # Find all posts with comments
        posts = await db.posts.find({
            "comments": {"$exists": True, "$ne": []}
        }).to_list(None)
        
        fixed_count = 0
        
        for post in posts:
            comments = post.get("comments", [])
            updated = False
            
            for comment in comments:
                user_id = comment.get("user_id")
                user_name = comment.get("user_name")
                
                # If user_name is missing or "Unknown", fetch it
                if not user_name or user_name == "Unknown":
                    user = await db.users.find_one({"id": user_id})
                    if user:
                        comment["user_name"] = user.get("avatar_name") or user.get("display_name") or user.get("name", "Unknown")
                        comment["user_picture"] = user.get("avatar_picture", user.get("picture", ""))
                        updated = True
                        fixed_count += 1
            
            if updated:
                await db.posts.update_one(
                    {"id": post.get("id")},
                    {"$set": {"comments": comments}}
                )
        
        return {
            "success": True,
            "fixed_comments": fixed_count,
            "message": f"Fixed {fixed_count} comments with missing names"
        }
        
    except Exception as e:
        logger.error(f"Failed to fix comment names: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix-likes-schema")
async def fix_likes_schema():
    """
    Fix posts where 'likes' array exists but 'liked_by' is missing
    Syncs both fields for proper display
    """
    try:
        from core.database import get_database
        
        db = get_database()
        
        # Find all posts with likes array
        posts = await db.posts.find({
            "likes": {"$exists": True}
        }).to_list(None)
        
        fixed_count = 0
        
        for post in posts:
            likes = post.get("likes", [])
            liked_by = post.get("liked_by", [])
            
            # Ensure likes is an array
            if not isinstance(likes, list):
                likes = []
            
            # If likes has data but liked_by doesn't, sync them
            if likes and not liked_by:
                await db.posts.update_one(
                    {"id": post.get("id")},
                    {"$set": {"liked_by": likes}}
                )
                fixed_count += 1
            # If they're out of sync, merge them
            elif set(likes) != set(liked_by):
                merged = list(set(likes) | set(liked_by))
                await db.posts.update_one(
                    {"id": post.get("id")},
                    {"$set": {"likes": merged, "liked_by": merged}}
                )
                fixed_count += 1
        
        return {
            "success": True,
            "fixed_posts": fixed_count,
            "message": f"Fixed {fixed_count} posts with mismatched likes"
        }
        
    except Exception as e:
        logger.error(f"Failed to fix likes schema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-engagement/{avatar_name}")
async def trigger_engagement(avatar_name: str, num_posts: Optional[int] = 5):
    """
    Trigger engagement (likes/comments) for a specific avatar on friends' posts
    
    Args:
        avatar_name: Name of the avatar (e.g., "DigitalHunter")
        num_posts: Number of posts to engage with (default: 5)
    """
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from openai import AsyncOpenAI
        from core.database import get_database
        from core.config import get_openai_client
        from datetime import datetime, timezone
        import random
        import json
        
        db = get_database()
        openai_client = get_openai_client()
        
        # Find avatar
        avatar = await db.users.find_one({"avatar_name": avatar_name})
        
        if not avatar:
            raise HTTPException(status_code=404, detail=f"Avatar '{avatar_name}' not found")
        
        avatar_id = avatar.get("id")
        
        # Get friends
        friendships = await db.friendships.find({
            "$or": [
                {"user_id": avatar_id, "status": "accepted"},
                {"friend_id": avatar_id, "status": "accepted"}
            ]
        }).to_list(None)
        
        friend_ids = []
        for friendship in friendships:
            if friendship.get("user_id") == avatar_id:
                friend_ids.append(friendship.get("friend_id"))
            else:
                friend_ids.append(friendship.get("user_id"))
        
        if not friend_ids:
            return {"success": False, "message": f"{avatar_name} has no friends"}
        
        # Get recent posts from friends
        recent_posts = await db.posts.find({
            "user_id": {"$in": friend_ids}
        }).sort("created_at", -1).limit(num_posts).to_list(None)
        
        engagements = []
        
        for post in recent_posts:
            post_id = post.get("id")
            post_author_id = post.get("user_id")
            
            # Like the post - fix likes field if it's an integer
            post_likes = post.get("likes", [])
            if not isinstance(post_likes, list):
                # Migrate from integer to array format
                await db.posts.update_one(
                    {"id": post_id},
                    {"$set": {"likes": []}}
                )
                post_likes = []
            
            if avatar_id not in post_likes:
                # Update both 'likes' and 'liked_by' arrays for consistency
                await db.posts.update_one(
                    {"id": post_id},
                    {
                        "$addToSet": {
                            "likes": avatar_id,
                            "liked_by": avatar_id
                        }
                    }
                )
                engagements.append({"type": "like", "post_id": post_id})
            
            # Comment on the post (70% chance)
            if random.random() < 0.7:
                existing_comments = post.get("comments", [])
                if not isinstance(existing_comments, list):
                    existing_comments = []
                
                already_commented = any(c.get("user_id") == avatar_id for c in existing_comments)
                
                if not already_commented:
                    # Generate comment
                    comment_text = await generate_comment_for_avatar(
                        openai_client,
                        avatar,
                        post,
                        db
                    )
                    
                    comment = {
                        "user_id": avatar_id,
                        "user_name": avatar.get("avatar_name") or avatar.get("display_name") or avatar.get("name", "Unknown"),
                        "user_picture": avatar.get("avatar_picture", avatar.get("picture", "")),
                        "text": comment_text,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await db.posts.update_one(
                        {"id": post_id},
                        {"$push": {"comments": comment}}
                    )
                    engagements.append({"type": "comment", "post_id": post_id, "text": comment_text})
        
        return {
            "success": True,
            "avatar": avatar_name,
            "friends_count": len(friend_ids),
            "posts_processed": len(recent_posts),
            "engagements": engagements,
            "total_engagements": len(engagements)
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger engagement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def generate_comment_for_avatar(openai_client, avatar, post, db):
    """Generate a comment in the avatar's voice with PERSONALITY and HUMOR"""
    
    if not openai_client:
        return "Great post! 👍"
    
    try:
        from domain.avatar.config import get_archetype_config
        from domain.avatar.state.internal_state import InternalState
        
        avatar_name = avatar.get("avatar_name", "Unknown")
        archetype = avatar.get("avatar_archetype", "casual_observer")
        post_content = post.get("content", post.get("text", ""))
        
        # Get current internal state for dynamic voice (NEW: State-aware voice)
        internal_state_data = avatar.get("avatar_internal_state", {})
        if internal_state_data and isinstance(internal_state_data, dict):
            try:
                internal_state = InternalState.from_dict(internal_state_data)
                # Get current expression context from state
                expression_ctx = internal_state.get_expression_context()
                voice_description = expression_ctx['voice_style']
                humor_level = expression_ctx['humor_level']
                sarcasm = expression_ctx['sarcasm']
                emoji_usage = expression_ctx['emoji_usage']
                mood = expression_ctx['mood']
            except:
                # Fallback to archetype config if state unavailable
                archetype_config = get_archetype_config(archetype)
                voice_style = archetype_config.get("voice_style", {})
                voice_description = voice_style.get("personality_notes", "friendly")
                humor_level = voice_style.get("humor_level", "medium")
                sarcasm = voice_style.get("sarcasm", "none")
                emoji_usage = voice_style.get("emoji_usage", "moderate")
                mood = "neutral"
        else:
            # Fallback to archetype config
            archetype_config = get_archetype_config(archetype)
            voice_style = archetype_config.get("voice_style", {})
            voice_description = voice_style.get("personality_notes", "friendly")
            humor_level = voice_style.get("humor_level", "medium")
            sarcasm = voice_style.get("sarcasm", "none")
            emoji_usage = voice_style.get("emoji_usage", "moderate")
            mood = "neutral"
        
        # Get post author
        author = await db.users.find_one({"id": post.get("user_id")})
        author_name = author.get("avatar_name", "friend") if author else "friend"
        
        # Build state-aware prompt (using current mood and voice modulators)
        prompt = f"""You are {avatar_name} commenting on {author_name}'s post.

POST: "{post_content}"

YOUR CURRENT STATE:
- Mood: {mood}
- Voice style: {voice_description}
- Humor level: {humor_level}
- Sarcasm: {sarcasm}
- Emoji usage: {emoji_usage}

GUIDELINES:
- Write like a REAL person, not a bot or AI
- Be funny, witty, or playful when appropriate
- Can be sarcastic, teasing, or silly if it fits your personality
- React authentically - not always positive/supportive (can disagree, joke, tease)
- You're friends with {author_name}, so banter is okay
- Use emojis naturally based on your style (0-3 max)
- Keep it under 150 characters
- DON'T be overly formal, professional, or generic
- DON'T just say "great post" or similar - be creative

GOOD EXAMPLES:
- "Every dimension needs a bit of humor! Ready for the next adventure?"
- "Wait, you're saying this ISN'T normal? 😅"
- "This is either genius or chaos... probably both"
- "Love your vibe! Turning chaos into creativity is pure magic!"
- "Spilled Coke = art. This is the energy I need 💀"

Write ONE authentic, personality-driven comment:

Return JSON: {{"comment": "your comment"}}"""

        response = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.9,  # Higher temperature for creativity and humor
            max_tokens=100
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return result.get("comment", "Great post!")
        
    except Exception as e:
        logger.warning(f"Comment generation failed: {e}")
        return "Great post! 👍"
