"""
Post Service
Handles post creation, retrieval, and interactions
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.graph.builder import GraphBuilder
import logging

logger = logging.getLogger(__name__)


class PostService:
    """Service for post operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase, graph_builder: Optional[GraphBuilder] = None):
        self.db = db
        self.graph_builder = graph_builder
    
    async def create_post(self, user_id: str, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new post"""
        # Determine post type (real or avatar)
        post_type = post_data.get('post_type', 'real')
        post_text = post_data.get('text', '')
        image_url = post_data.get('image_url', '')
        
        # Create post with full structure
        post_id = f"post-{user_id}-{datetime.now(timezone.utc).timestamp()}"
        new_post = {
            'id': post_id,
            'user_id': user_id,
            'text': post_text,
            'content': post_text,  # Backwards compatibility
            'post_type': post_type,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'likes': 0,
            'liked_by': [],  # Track who liked
            'comments': [],
            'comment_count': 0
        }
        
        # Add image if provided
        if image_url:
            new_post['image_url'] = image_url
            new_post['has_image'] = True
        
        # Add to posts collection (source of truth for feed)
        await self.db.posts.insert_one(new_post)
        
        # Also add to user document for backwards compatibility
        post_for_user = {k: v for k, v in new_post.items() if k != '_id'}
        if post_type == 'avatar':
            await self.db.users.update_one(
                {"id": user_id},
                {"$push": {"avatar_posts": post_for_user}}
            )
        else:
            await self.db.users.update_one(
                {"id": user_id},
                {"$push": {"posts": post_for_user}}
            )
        
        # Enrich knowledge graph from post content (for real posts only)
        if post_type == 'real' and post_text and self.graph_builder:
            try:
                await self.graph_builder.enrich_graph_from_post(post_text, user_id)
            except Exception as e:
                logger.error(f"Graph enrichment error: {str(e)}")
        
        # Remove _id for response
        new_post.pop('_id', None)
        return new_post
    
    async def get_user_posts(self, user_id: str, post_type: str = "real", limit: int = 100) -> List[Dict[str, Any]]:
        """Get user's posts"""
        posts_cursor = self.db.posts.find({
            "user_id": user_id,
            "post_type": post_type
        }).sort([("created_at", -1)]).limit(limit)
        
        posts = await posts_cursor.to_list(limit)
        
        # Remove _id fields for JSON serialization
        for post in posts:
            post.pop('_id', None)
        
        return posts
    
    async def get_feed_posts(self, user_id: str, post_type: str = "real", limit: int = 50) -> List[Dict[str, Any]]:
        """Get feed posts (posts from friends and user)"""
        # Get user's friends
        friendships = await self.db.friendships.find({
            "$or": [
                {"user_id": user_id},
                {"friend_id": user_id}
            ]
        }).to_list(1000)
        
        friend_ids = [user_id]  # Include own posts
        for f in friendships:
            if f['user_id'] == user_id:
                friend_ids.append(f['friend_id'])
            else:
                friend_ids.append(f['user_id'])
        
        # Get posts from friends
        posts_cursor = self.db.posts.find({
            "user_id": {"$in": friend_ids},
            "post_type": post_type
        }).sort([("created_at", -1)]).limit(limit)
        
        posts = await posts_cursor.to_list(limit)
        
        # Remove _id fields
        for post in posts:
            post.pop('_id', None)
        
        return posts
    
    async def delete_post(self, post_id: str, user_id: str) -> bool:
        """Delete a post"""
        result = await self.db.posts.delete_one({
            "id": post_id,
            "user_id": user_id
        })
        
        # Also remove from user document
        await self.db.users.update_one(
            {"id": user_id},
            {"$pull": {"posts": {"id": post_id}}}
        )
        await self.db.users.update_one(
            {"id": user_id},
            {"$pull": {"avatar_posts": {"id": post_id}}}
        )
        
        return result.deleted_count > 0
    
    async def like_post(self, post_id: str, user_id: str) -> Dict[str, Any]:
        """Like or unlike a post (toggle behavior)"""
        # Find the post
        post = await self.db.posts.find_one({"id": post_id})
        if not post:
            return {"success": False, "error": "Post not found"}
        
        liked_by = post.get('liked_by', [])
        is_liked = user_id in liked_by
        
        if is_liked:
            # Unlike: remove from liked_by and decrement likes
            await self.db.posts.update_one(
                {"id": post_id},
                {
                    "$pull": {"liked_by": user_id},
                    "$inc": {"likes": -1}
                }
            )
            
            # Also update in user document
            post_type = post.get("post_type", "real")
            field = "avatar_posts" if post_type == "avatar" else "posts"
            await self.db.users.update_one(
                {"id": post.get("user_id"), f"{field}.id": post_id},
                {
                    "$pull": {f"{field}.$.liked_by": user_id},
                    "$inc": {f"{field}.$.likes": -1}
                }
            )
            
            return {"success": True, "liked": False, "likes": max(0, post.get("likes", 0) - 1)}
        else:
            # Like: add to liked_by and increment likes
            await self.db.posts.update_one(
                {"id": post_id},
                {
                    "$addToSet": {"liked_by": user_id},
                    "$inc": {"likes": 1}
                }
            )
            
            # Also update in user document
            post_type = post.get("post_type", "real")
            field = "avatar_posts" if post_type == "avatar" else "posts"
            await self.db.users.update_one(
                {"id": post.get("user_id"), f"{field}.id": post_id},
                {
                    "$addToSet": {f"{field}.$.liked_by": user_id},
                    "$inc": {f"{field}.$.likes": 1}
                }
            )
            
            return {"success": True, "liked": True, "likes": post.get("likes", 0) + 1}
    
    async def comment_on_post(self, post_id: str, user_id: str, comment_text: str, user_name: str, user_picture: str = "") -> Dict[str, Any]:
        """Add a comment to a post"""
        post = await self.db.posts.find_one({"id": post_id})
        if not post:
            return {"success": False, "error": "Post not found"}
        
        # Get user's display name based on post type
        user_doc = await self.db.users.find_one({"id": user_id})
        post_type = post.get("post_type", "real")
        display_name = user_doc.get("avatar_name") if post_type == "avatar" else user_doc.get("name", user_name)
        display_picture = user_doc.get("avatar_picture") if post_type == "avatar" else user_doc.get("picture", user_picture)
        
        # Create comment
        comment = {
            "id": f"comment-{post_id}-{datetime.now(timezone.utc).timestamp()}",
            "user_id": user_id,
            "user_name": display_name or user_name,
            "user_picture": display_picture or user_picture,
            "text": comment_text,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add comment to post in posts collection
        await self.db.posts.update_one(
            {"id": post_id},
            {"$push": {"comments": comment}, "$inc": {"comment_count": 1}}
        )
        
        # Also update in user document
        field = "avatar_posts" if post_type == "avatar" else "posts"
        await self.db.users.update_one(
            {"id": post.get("user_id"), f"{field}.id": post_id},
            {
                "$push": {f"{field}.$.comments": comment},
                "$inc": {f"{field}.$.comment_count": 1}
            }
        )
        
        return {"success": True, "comment": comment}
    
    async def get_post_comments(self, post_id: str) -> Dict[str, Any]:
        """Get all comments for a post"""
        post = await self.db.posts.find_one({"id": post_id}, {"comments": 1, "comment_count": 1})
        if not post:
            return {"success": False, "error": "Post not found"}
        
        comments = post.get("comments", [])
        # Sort by created_at (newest first)
        comments.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {"success": True, "comments": comments, "count": len(comments)}
    
    async def get_post_likes(self, post_id: str) -> Dict[str, Any]:
        """Get list of users who liked a post"""
        post = await self.db.posts.find_one({"id": post_id}, {"liked_by": 1, "likes": 1})
        if not post:
            return {"success": False, "error": "Post not found"}
        
        liked_by_ids = post.get("liked_by", [])
        if not liked_by_ids:
            return {"success": True, "users": [], "count": post.get("likes", 0)}
        
        # Get user details
        users = await self.db.users.find(
            {"id": {"$in": liked_by_ids}},
            {"_id": 0, "id": 1, "name": 1, "avatar_name": 1, "picture": 1, "avatar_picture": 1}
        ).to_list(100)
        
        # Format users
        liked_users = []
        for u in users:
            liked_users.append({
                "id": u["id"],
                "name": u.get("avatar_name") or u.get("name"),
                "picture": u.get("avatar_picture") or u.get("picture")
            })
        
        return {"success": True, "users": liked_users, "count": len(liked_by_ids)}
    
    async def update_post(self, post_id: str, user_id: str, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a post"""
        update_fields = {}
        if 'text' in post_data:
            update_fields['text'] = post_data['text']
            update_fields['content'] = post_data['text']  # Backwards compatibility
        
        if not update_fields:
            return {"success": False, "error": "No fields to update"}
        
        result = await self.db.posts.update_one(
            {"id": post_id, "user_id": user_id},
            {"$set": update_fields}
        )
        
        if result.modified_count == 0:
            return {"success": False, "error": "Post not found or not updated"}
        
        return {"success": True, "message": "Post updated"}
    
    async def get_gallery_photos(self, user_id: str, post_type: str = "real", limit: int = 50) -> List[Dict[str, Any]]:
        """Get posts with images for gallery"""
        posts_cursor = self.db.posts.find({
            "user_id": user_id,
            "post_type": post_type,
            "has_image": True
        }).sort([("created_at", -1)]).limit(limit)
        
        posts = await posts_cursor.to_list(limit)
        logger.info(f"Found {len(posts)} posts with images for user {user_id}, type {post_type}")
        
        # Format for gallery
        gallery_items = []
        for post in posts:
            image_url = post.get("image_url")
            if image_url:  # Only include posts with valid image URLs
                gallery_items.append({
                    "id": post.get("id"),
                    "image_url": image_url,
                    "caption": post.get("text", ""),
                    "created_at": post.get("created_at"),
                    "post_id": post.get("id")
                })
            else:
                logger.warning(f"Post {post.get('id')} has has_image=True but no image_url")
        
        logger.info(f"Returning {len(gallery_items)} gallery items")
        return gallery_items

