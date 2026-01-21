"""
Post Service
Handles post creation, retrieval, and interactions
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.graph.builder import GraphBuilder
import logging
import asyncio

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
        # Run in background to avoid blocking the response
        if post_type == 'real' and post_text and self.graph_builder:
            asyncio.create_task(self._enrich_graph_background(post_text, user_id))
            logger.info(f"Started background graph enrichment for post {post_id}")
        
        # Remove _id for response
        new_post.pop('_id', None)
        return new_post
    
    async def _enrich_graph_background(self, post_text: str, user_id: str):
        """
        Background task to enrich knowledge graph from post content.
        This runs asynchronously without blocking the post creation response.
        """
        try:
            await self.graph_builder.enrich_graph_from_post(post_text, user_id)
            logger.info(f"Background graph enrichment completed for user {user_id}")
        except Exception as e:
            logger.error(f"Background graph enrichment error for user {user_id}: {str(e)}")
    
    async def get_user_posts(self, user_id: str, post_type: str = "real", limit: int = 20, skip: int = 0) -> Dict[str, Any]:
        """Get user's posts with pagination"""
        # Count total posts
        total_count = await self.db.posts.count_documents({
            "user_id": user_id,
            "post_type": post_type
        })
        
        # Fetch larger batch to handle sorting issues (mixed types)
        # Use $natural sort (insertion order) descending to get the most recently inserted documents
        # This avoids issues where created_at sort fails due to mixed types (String vs Date)
        fetch_limit = min(total_count, 5000)
        
        posts_cursor = self.db.posts.find({
            "user_id": user_id,
            "post_type": post_type
        }).sort("$natural", -1).limit(fetch_limit)
        
        all_posts = await posts_cursor.to_list(fetch_limit)
        
        # Remove _id fields and normalize created_at format
        posts_processed = []
        for post in all_posts:
            post.pop('_id', None)
            
            # Normalize created_at to datetime object for sorting
            created_at = post.get('created_at')
            if isinstance(created_at, str):
                try:
                    if 'T' in created_at:
                        # ISO format
                        try:
                            iso_str = created_at
                            if '+' in iso_str and not iso_str.endswith('+00:00'):
                                parts = iso_str.split('+')
                                if len(parts) == 2:
                                    iso_str = parts[0] + '+00:00'
                            elif 'Z' in iso_str:
                                iso_str = iso_str.replace('Z', '+00:00')
                            post['created_at'] = datetime.fromisoformat(iso_str)
                        except:
                            # Fallback
                            date_part = created_at.split('T')[0]
                            post['created_at'] = datetime.strptime(date_part, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    else:
                        # Old format
                        dt = datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
                        post['created_at'] = dt.replace(tzinfo=timezone.utc)
                except Exception:
                    pass
            
            # Ensure datetime objects have timezone
            if isinstance(post.get('created_at'), datetime) and post['created_at'].tzinfo is None:
                post['created_at'] = post['created_at'].replace(tzinfo=timezone.utc)
                
            posts_processed.append(post)
        
        # Re-sort posts by actual date
        def safe_sort_key(post):
            created_at = post.get('created_at')
            if created_at is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(created_at, datetime):
                return created_at
            return datetime.min.replace(tzinfo=timezone.utc)
        
        posts_processed.sort(key=safe_sort_key, reverse=True)
        
        # Apply pagination in Python
        posts = posts_processed[skip:skip + limit]
        
        # Enrich posts with author information
        # Get user info for the post author
        user = await self.db.users.find_one(
            {"id": user_id},
            {"id": 1, "name": 1, "avatar_name": 1, "picture": 1, "avatar_picture": 1, "is_bot": 1}
        )
        
        # Add author info to each post
        for post in posts:
            if user:
                post['author_name'] = user.get('name', 'Unknown')
                post['author_avatar_name'] = user.get('avatar_name', user.get('name', 'Unknown'))
                post['author_picture'] = user.get('picture')
                post['author_avatar_picture'] = user.get('avatar_picture', user.get('picture'))
                post['author_is_bot'] = user.get('is_bot', False)
            
            # Normalize likes field to always be a number for display
            likes = post.get('likes', 0)
            if isinstance(likes, list):
                post['likes'] = len(likes)
            elif not isinstance(likes, (int, float)):
                post['likes'] = 0
        
        # Convert datetime objects back to ISO strings
        for post in posts:
            if isinstance(post.get('created_at'), datetime):
                post['created_at'] = post['created_at'].isoformat()
        
        # Calculate has_more
        has_more = (skip + len(posts)) < total_count
        
        return {
            "posts": posts,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": has_more
        }
    
    async def get_feed_posts(self, user_id: str, post_type: str = "real", limit: int = 20, skip: int = 0) -> Dict[str, Any]:
        """Get feed posts (posts from friends and user) with pagination"""
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
        
        # Count total posts
        total_count = await self.db.posts.count_documents({
            "user_id": {"$in": friend_ids},
            "post_type": post_type
        })
        
        # Get posts from friends
        # OPTIMIZED: Limit fetch to reasonable amount to avoid timeouts
        # We fetch more than needed to account for sorting issues with mixed date formats
        fetch_limit = min(skip + limit + 100, 300)  # Fetch at most 300 posts
        
        # Try MongoDB sort first, then fall back to Python sort if needed
        posts_cursor = self.db.posts.find({
            "user_id": {"$in": friend_ids},
            "post_type": post_type
        }).sort("created_at", -1).limit(fetch_limit)
        
        all_posts = await posts_cursor.to_list(fetch_limit)
        
        logger.info(f"Fetched {len(all_posts)} posts for feed (total available: {total_count}, fetch_limit: {fetch_limit})")
        
        # Remove _id fields and convert all dates to datetime objects for proper sorting
        posts_processed = []
        for post in all_posts:
            post.pop('_id', None)
            created_at = post.get('created_at')
            
            # Convert to datetime object if it's a string
            if isinstance(created_at, str):
                try:
                    if 'T' in created_at:
                        # ISO format: "2025-11-17T13:37:38.160979+00:00"
                        # Use datetime.fromisoformat which handles ISO format
                        try:
                            # Clean up the string for parsing
                            iso_str = created_at
                            if '+' in iso_str and not iso_str.endswith('+00:00'):
                                # Extract timezone offset
                                parts = iso_str.split('+')
                                if len(parts) == 2:
                                    iso_str = parts[0] + '+00:00'
                            elif 'Z' in iso_str:
                                iso_str = iso_str.replace('Z', '+00:00')
                            post['created_at'] = datetime.fromisoformat(iso_str)
                        except Exception as parse_error:
                            # Fallback: try simpler parsing
                            try:
                                # Just get the date part and add default time
                                date_part = created_at.split('T')[0]
                                post['created_at'] = datetime.strptime(date_part, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                            except:
                                logger.warning(f"Could not parse ISO date {created_at}: {parse_error}")
                                continue
                    else:
                        # Old format: "2025-10-25 09:20:32.884000"
                        dt = datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
                        post['created_at'] = dt.replace(tzinfo=timezone.utc)
                except Exception as e:
                    logger.warning(f"Failed to parse date {created_at}: {e}")
                    # Skip posts with unparseable dates
                    continue
            
            # Ensure datetime objects have timezone
            if isinstance(post.get('created_at'), datetime) and post['created_at'].tzinfo is None:
                post['created_at'] = post['created_at'].replace(tzinfo=timezone.utc)
            
            posts_processed.append(post)
        
        # Sort by actual datetime (newest first)
        # Use a safe sort key that handles None values
        def safe_sort_key(post):
            created_at = post.get('created_at')
            if created_at is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(created_at, datetime):
                return created_at
            # Should not happen after processing, but just in case
            return datetime.min.replace(tzinfo=timezone.utc)
        
        posts_processed.sort(key=safe_sort_key, reverse=True)
        
        # Log first few posts for debugging
        if posts_processed:
            logger.info(f"Feed posts after sorting - First 3 dates: {[p.get('created_at') for p in posts_processed[:3]]}")
        
        # Apply pagination after sorting
        posts = posts_processed[skip:skip + limit]
        
        # Enrich posts with author information
        # Get unique user IDs from posts
        post_user_ids = list(set(p.get('user_id') for p in posts if p.get('user_id')))
        
        # Fetch user info for all post authors
        users_cursor = self.db.users.find(
            {"id": {"$in": post_user_ids}},
            {"id": 1, "name": 1, "avatar_name": 1, "picture": 1, "avatar_picture": 1, "is_bot": 1}
        )
        users_map = {u['id']: u async for u in users_cursor}
        
        # Add author info to each post
        for post in posts:
            author = users_map.get(post.get('user_id'), {})
            post['author_name'] = author.get('name', 'Unknown')
            post['author_avatar_name'] = author.get('avatar_name', author.get('name', 'Unknown'))
            post['author_picture'] = author.get('picture')
            post['author_avatar_picture'] = author.get('avatar_picture', author.get('picture'))
            post['author_is_bot'] = author.get('is_bot', False)
        
        # Convert datetime objects back to ISO strings for JSON serialization
        for post in posts:
            if isinstance(post.get('created_at'), datetime):
                post['created_at'] = post['created_at'].isoformat()
        
        # Calculate has_more correctly:
        # - If we fetched fewer posts than total, check if we've shown all fetched posts
        # - If we fetched all posts, check if we've shown all of them
        total_fetched = len(posts_processed)
        posts_returned = len(posts)
        has_more = (skip + posts_returned) < min(total_fetched, total_count)
        
        logger.info(f"Feed pagination: skip={skip}, returned={posts_returned}, total_fetched={total_fetched}, total_count={total_count}, has_more={has_more}")
        
        return {
            "posts": posts,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": has_more
        }
    
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
        
        # Normalize likes field if it's an array (legacy data)
        likes_field = post.get('likes', 0)
        if isinstance(likes_field, list):
            # Fix the schema: convert array to count, use liked_by for user IDs
            likes_count = len(likes_field)
            await self.db.posts.update_one(
                {"id": post_id},
                {
                    "$set": {
                        "likes": likes_count,
                        "liked_by": likes_field
                    }
                }
            )
            post['likes'] = likes_count
            post['liked_by'] = likes_field
        
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
        
        # Filter out None/empty IDs
        valid_ids = [uid for uid in liked_by_ids if uid]
        if not valid_ids:
            return {"success": True, "users": [], "count": post.get("likes", 0)}
        
        # Get user details
        users = await self.db.users.find(
            {"id": {"$in": valid_ids}},
            {"_id": 0, "id": 1, "name": 1, "avatar_name": 1, "picture": 1, "avatar_picture": 1}
        ).to_list(100)
        
        # Format users - ensure all fields are present
        liked_users = []
        for u in users:
            if not u.get("id"):
                continue  # Skip users without ID
            user_name = u.get("avatar_name") or u.get("name") or "Unknown User"
            user_picture = u.get("avatar_picture") or u.get("picture") or ""
            liked_users.append({
                "id": u["id"],
                "name": user_name,
                "picture": user_picture
            })
        
        logger.info(f"Found {len(liked_users)} users who liked post {post_id} out of {len(valid_ids)} IDs")
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

