"""
Simple Reactive Agent - Phase 1 MVP
Quick implementation for immediate bot activity
No complex state machine - just reactive behaviors
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from intelligent_avatar import IntelligentAvatar
from autonomous_config import get_archetype_config, get_post_prompt


class SimpleReactiveAgent:
    """
    Minimal reactive bot agent - Phase 1 implementation
    
    Behaviors:
    - React to unseen posts (like/comment)
    - Create posts based on personality
    - Accept friend requests
    - Simple decision making (no complex AI)
    """
    
    def __init__(self, bot: Dict[str, Any], db: AsyncIOMotorDatabase, 
                 intelligent_avatar: IntelligentAvatar):
        self.bot = bot
        self.bot_id = bot['id']
        self.db = db
        self.intelligent_avatar = intelligent_avatar
        self.archetype = bot.get('archetype', 'casual_observer')
        self.config = get_archetype_config(self.archetype)
        
        # Track if this is a user avatar (not a bot)
        self.is_user_avatar = not bot.get('is_bot', False)
        
        # Activity tracking
        self.last_action_time = datetime.now(timezone.utc)
        self.actions_this_hour = 0
        self.max_actions_per_hour = 10  # Rate limiting
        
        # Seen posts tracking (in-memory for now)
        self.seen_posts = set()
        
        # Visual indicator for user avatars
        avatar_indicator = "✨" if self.is_user_avatar else "🤖"
        
        # Load action permissions
        self.actions_enabled = bot.get('avatar_actions_enabled', {
            'like_posts': True,
            'comment_posts': True,
            'create_posts': True,
            'send_friend_requests': True,
            'accept_friend_requests': True,
            'message_friends': True,
            'discover_profiles': True,
            'share_posts': False
        })
        
        print(f"{avatar_indicator} Initialized {bot.get('avatar_name', bot.get('name'))} ({self.archetype})")
    
    async def run_cycle(self):
        """Main activity cycle - runs every 10-15 minutes"""
        try:
            avatar_indicator = "✨ USER AVATAR" if self.is_user_avatar else "🤖"
            print(f"\n{'='*60}")
            print(f"🔄 {self.bot.get('avatar_name')} activity cycle {avatar_indicator}")
            print(f"{'='*60}")
            
            # Check if we're at action limit
            if self.actions_this_hour >= self.max_actions_per_hour:
                print(f"⏸️  Action limit reached for this hour")
                return
            
            # 1. React to posts (60% of time) - only if enabled
            if random.random() < 0.6 and (self._is_action_enabled('like_posts') or self._is_action_enabled('comment_posts')):
                await self._react_to_posts()
            
            # 2. Create own post (20% of time) - only if enabled
            if random.random() < 0.2 and self._is_action_enabled('create_posts'):
                await self._create_post()
            
            # 3. Check friend requests (30% of time) - only if enabled
            if random.random() < 0.3 and (self._is_action_enabled('accept_friend_requests') or self._is_action_enabled('send_friend_requests')):
                await self._check_friend_requests()
            
            # 4. Discover new profiles (10% of time) - only if enabled
            if random.random() < 0.1 and self._is_action_enabled('discover_profiles'):
                await self._discover_profiles()
            
            self.last_action_time = datetime.now(timezone.utc)
            
        except Exception as e:
            print(f"❌ Error in {self.bot.get('avatar_name')} cycle: {e}")
    
    def _is_action_enabled(self, action_key: str) -> bool:
        """Check if a specific action is enabled for this avatar"""
        return self.actions_enabled.get(action_key, True)  # Default to True if not set
    
    async def _react_to_posts(self):
        """React to unseen posts from friends"""
        try:
            # Get recent posts from friends (last 24 hours)
            posts = await self._get_friend_posts(limit=10)
            
            if not posts:
                print(f"   No new posts to react to")
                return
            
            print(f"   📬 Found {len(posts)} posts to consider")
            
            for post in posts:
                # Skip if already seen
                if post['id'] in self.seen_posts:
                    continue
                
                self.seen_posts.add(post['id'])
                
                # Decide if should react based on personality
                if await self._should_react_to_post(post):
                    reaction_type = await self._choose_reaction_type(post)
                    
                    if reaction_type == "like" and self._is_action_enabled('like_posts'):
                        await self._like_post(post)
                    elif reaction_type == "comment" and self._is_action_enabled('comment_posts'):
                        await self._comment_on_post(post)
                    elif reaction_type == "like" and not self._is_action_enabled('like_posts'):
                        # Skip if like is disabled
                        continue
                    elif reaction_type == "comment" and not self._is_action_enabled('comment_posts'):
                        # Fallback to like if comment is disabled but like is enabled
                        if self._is_action_enabled('like_posts'):
                            await self._like_post(post)
                        continue
                    
                    self.actions_this_hour += 1
                    
                    # Rate limiting
                    await asyncio.sleep(2)
                    
                    if self.actions_this_hour >= self.max_actions_per_hour:
                        break
        
        except Exception as e:
            print(f"   ❌ Error reacting to posts: {e}")
    
    async def _should_react_to_post(self, post: Dict) -> bool:
        """Decide if bot should react to this post"""
        # Don't react to own posts
        if post['user_id'] == self.bot_id:
            return False
        
        # Calculate interest match
        interest_score = self._calculate_interest_match(post)
        
        # Get personality reaction chance
        reaction_chance = self.config['reaction_behavior']['like_chance']
        
        # Combined probability
        final_chance = (interest_score * 0.6 + reaction_chance * 0.4)
        
        return random.random() < final_chance
    
    def _calculate_interest_match(self, post: Dict) -> float:
        """Calculate how much this post matches bot's interests"""
        # Simple keyword matching for now
        post_text = post.get('text', '').lower()
        bot_interests = [i.lower() for i in self.bot.get('interests', [])]
        
        # Check for interest keywords
        matches = sum(1 for interest in bot_interests if interest in post_text)
        
        if matches > 0:
            return min(matches / len(bot_interests), 1.0)
        
        # Base probability even without matches
        return 0.2
    
    async def _choose_reaction_type(self, post: Dict) -> str:
        """Choose: like or comment"""
        comment_chance = self.config['reaction_behavior']['comment_chance']
        
        if random.random() < comment_chance:
            return "comment"
        else:
            return "like"
    
    async def _like_post(self, post: Dict):
        """Like a post"""
        try:
            # Update post likes and track who liked
            await self.db.posts.update_one(
                {"id": post['id']},
                {
                    "$addToSet": {"liked_by": self.bot_id},  # Track who liked
                    "$inc": {"likes": 1}
                }
            )
            
            # Also update in user document if post is there
            post_type = post.get("post_type", "real")
            field = "avatar_posts" if post_type == "avatar" else "posts"
            await self.db.users.update_one(
                {"id": post.get("user_id"), f"{field}.id": post['id']},
                {
                    "$addToSet": {f"{field}.$.liked_by": self.bot_id},
                    "$inc": {f"{field}.$.likes": 1}
                }
            )
            
            print(f"   👍 Liked post by {post.get('user_id', 'unknown')[:20]}...")
            
            # Log activity
            await self._log_activity("post_like", {
                "post_id": post['id'],
                "post_author": post.get('user_id')
            })
            
        except Exception as e:
            print(f"   ❌ Error liking post: {e}")
    
    async def _comment_on_post(self, post: Dict):
        """Comment on a post"""
        try:
            # Generate a short comment using AI
            comment_text = await self._generate_comment(post)
            
            if not comment_text:
                # Fallback to like if comment generation fails
                await self._like_post(post)
                return
            
            # Add comment to post
            comment = {
                "id": f"comment-{datetime.now(timezone.utc).timestamp()}",
                "user_id": self.bot_id,
                "user_name": self.bot.get('avatar_name', self.bot.get('name')),
                "user_picture": self.bot.get('avatar_picture', self.bot.get('picture', '')),
                "text": comment_text,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.posts.update_one(
                {"id": post['id']},
                {"$push": {"comments": comment}, "$inc": {"comment_count": 1}}
            )
            
            print(f"   💬 Commented: \"{comment_text[:50]}...\"")
            
            # Log activity
            await self._log_activity("post_comment", {
                "post_id": post['id'],
                "comment_text": comment_text
            })
            
        except Exception as e:
            print(f"   ❌ Error commenting: {e}")
    
    async def _generate_comment(self, post: Dict) -> Optional[str]:
        """Generate a comment using AI"""
        try:
            # Use the intelligent avatar to generate a response
            post_text = post.get('text', post.get('content', ''))
            post_author = post.get('user_id', 'someone')
            
            # Generate a chat response as if replying to the post
            result = await self.intelligent_avatar.generate_chat_response(
                user_id=self.bot_id,
                other_user_id=post_author,
                conversation_history=[],
                last_message=post_text
            )
            
            if 'error' in result:
                return None
            
            # Extract comment text
            comment = result.get('response', '').strip()
            
            # Keep it short for a comment
            if len(comment) > 200:
                # Take first sentence
                sentences = comment.split('. ')
                comment = sentences[0] + '.'
            
            # Limit length
            if len(comment) > 200:
                comment = comment[:197] + "..."
            
            return comment
            
        except Exception as e:
            print(f"   ⚠️  Comment generation failed: {e}")
            return None
    
    async def _create_post(self):
        """Create a new post"""
        try:
            # Check if enough time has passed since last post
            last_post_cursor = self.db.posts.find(
                {"user_id": self.bot_id}
            ).sort([("created_at", -1)]).limit(1)
            
            last_posts = await last_post_cursor.to_list(1)
            
            if last_posts:
                last_post = last_posts[0]
                created_at = last_post.get('created_at', '')
                
                # Handle different datetime formats
                if isinstance(created_at, str):
                    created_at = created_at.replace('Z', '+00:00')
                    last_post_time = datetime.fromisoformat(created_at)
                else:
                    last_post_time = created_at
                
                # Ensure timezone awareness
                if last_post_time.tzinfo is None:
                    last_post_time = last_post_time.replace(tzinfo=timezone.utc)
                
                hours_since_last = (datetime.now(timezone.utc) - last_post_time).total_seconds() / 3600
                
                min_hours = float(self.config['posting_frequency']['min_hours'])
                if hours_since_last < min_hours:
                    print(f"   ⏸️  Too soon to post (last post {hours_since_last:.1f}h ago)")
                    return
            
            # Generate post content
            print(f"   📝 Generating post content...")
            post_content = await self._generate_post_content()
            
            if not post_content:
                print(f"   ⚠️ Post generation returned empty content (skipping)")
                return
            
            print(f"   ✅ Content generated ({len(post_content)} chars)")
            
            # Create post ONLY in Maya World (avatar world)
            # Autonomous agents should only interact as avatars, not as real people
            world_mode = 'avatar'
            
            post = {
                "id": f"post-{self.bot_id}-{datetime.now(timezone.utc).timestamp()}",
                "user_id": self.bot_id,
                "text": post_content,
                "content": post_content,  # Backwards compatibility
                "post_type": world_mode,
                "likes": 0,
                "liked_by": [],  # Track who liked
                "comments": [],
                "comment_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.posts.insert_one(post)
            
            # ALSO add to user document (for frontend feed)
            # Remove _id field before pushing to user document to avoid serialization issues
            post_for_user = {k: v for k, v in post.items() if k != '_id'}
            field_name = 'avatar_posts' if world_mode == 'avatar' else 'posts'
            await self.db.users.update_one(
                {"id": self.bot_id},
                {"$push": {field_name: post_for_user}}
            )
            
            print(f"   📝 Created post: \"{post_content[:60]}...\"")
            
            # Log activity
            await self._log_activity("post_created", {
                "post_id": post['id'],
                "world_mode": world_mode
            })
            
            self.actions_this_hour += 1
            
        except Exception as e:
            print(f"   ❌ Error creating post: {e}")
    
    async def _generate_post_content(self) -> Optional[str]:
        """Generate post content using AI"""
        try:
            # Use the avatar post generation
            result = await self.intelligent_avatar.generate_avatar_post(
                user_id=self.bot_id,
                post_type="general"
            )
            
            if 'error' in result:
                print(f"   ⚠️  Post generation failed: {result['error']}")
                return None
            
            # FIX: result has 'content' at top level, not nested under 'post'
            post = result.get('content', '')
            
            if not post:
                print(f"   ⚠️  Generated content is empty!")
                return None
            
            # Limit length
            if len(post) > 500:
                post = post[:497] + "..."
            
            return post
            
        except Exception as e:
            print(f"   ⚠️  Post generation failed: {e}")
            return None
    
    async def _check_friend_requests(self):
        """Check and respond to friend requests"""
        try:
            # Get pending friend requests
            # For now, we'll just check if there are profiles we're not friends with
            # and randomly accept some
            
            # Get current friends
            friendships = await self.db.friendships.find({
                "$or": [
                    {"user1_id": self.bot_id},
                    {"user2_id": self.bot_id}
                ]
            }).to_list(1000)
            
            friend_ids = set()
            for f in friendships:
                if f['user1_id'] == self.bot_id:
                    friend_ids.add(f['user2_id'])
                else:
                    friend_ids.add(f['user1_id'])
            
            # Find AVATARS we're not friends with (bots + user avatars, not real people)
            # Autonomous agents should only befriend other avatars
            all_avatars = await self.db.users.find({
                "$or": [
                    {"is_bot": True},  # All bots are avatars
                    {"avatar_autonomous": True}  # User avatars with autonomy
                ],
                "id": {"$ne": self.bot_id},
                "avatar_name": {"$exists": True}  # Must have avatar identity
            }).to_list(100)
            
            non_friends = [b for b in all_avatars if b['id'] not in friend_ids]
            
            if not non_friends:
                return
            
            # Consider befriending 1-2 compatible bots
            for _ in range(random.randint(0, 2)):
                if not non_friends:
                    break
                
                candidate = random.choice(non_friends)
                non_friends.remove(candidate)
                
                if await self._should_befriend(candidate):
                    # Only send friend request if enabled
                    if self._is_action_enabled('send_friend_requests'):
                        await self._send_friend_request(candidate)
                        self.actions_this_hour += 1
                        await asyncio.sleep(1)
                    else:
                        print(f"   ⏸️  Friend request sending disabled for this avatar")
        
        except Exception as e:
            print(f"   ❌ Error checking friend requests: {e}")
    
    async def _should_befriend(self, candidate: Dict) -> bool:
        """Decide if should befriend this user"""
        # Calculate interest overlap
        bot_interests = set(self.bot.get('interests', []))
        candidate_interests = set(candidate.get('interests', []))
        
        overlap = len(bot_interests & candidate_interests)
        
        if overlap >= 2:
            return random.random() < 0.7
        elif overlap == 1:
            return random.random() < 0.4
        else:
            return random.random() < 0.1
    
    async def _send_friend_request(self, target: Dict):
        """Send a friend request"""
        try:
            # Create friendship
            friendship = {
                "user1_id": self.bot_id,
                "user2_id": target['id'],
                "status": "accepted",  # For now, auto-accept
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.friendships.insert_one(friendship)
            
            print(f"   👥 Befriended {target.get('avatar_name', target.get('name'))}")
            
            # Log activity
            await self._log_activity("friend_request_sent", {
                "target_user_id": target['id']
            })
            
        except Exception as e:
            print(f"   ❌ Error sending friend request: {e}")
    
    async def _discover_profiles(self):
        """Discover and view new profiles (only avatars, not real people)"""
        try:
            # Get random AVATARS to "view" (not real people)
            # Autonomous agents should only interact with avatars
            users = await self.db.users.find({
                "id": {"$ne": self.bot_id},
                "$or": [
                    {"is_bot": True},  # All bots are avatars
                    {"avatar_autonomous": True}  # User avatars with autonomy enabled
                ],
                "avatar_name": {"$exists": True}  # Must have avatar identity
            }).to_list(5)
            
            if users:
                viewed = random.choice(users)
                print(f"   👀 Viewed profile: {viewed.get('avatar_name', viewed.get('name'))}")
                
                # Could log this for analytics
                await self._log_activity("profile_viewed", {
                    "viewed_user_id": viewed['id']
                })
        
        except Exception as e:
            print(f"   ❌ Error discovering profiles: {e}")
    
    async def _get_friend_posts(self, limit: int = 10) -> List[Dict]:
        """Get recent posts from friends"""
        try:
            # Get friend IDs
            friendships = await self.db.friendships.find({
                "$or": [
                    {"user1_id": self.bot_id},
                    {"user2_id": self.bot_id}
                ]
            }).to_list(1000)
            
            friend_ids = []
            for f in friendships:
                if f['user1_id'] == self.bot_id:
                    friend_ids.append(f['user2_id'])
                else:
                    friend_ids.append(f['user1_id'])
            
            if not friend_ids:
                # If no friends, get any recent AVATAR posts only
                # Autonomous agents should only interact with avatars, not real people
                posts = await self.db.posts.find({
                    "user_id": {"$ne": self.bot_id},
                    "post_type": "avatar"  # ONLY avatar posts
                }).sort([("created_at", -1)]).limit(limit).to_list(limit)
                return posts
            
            # Get recent AVATAR posts from friends (last 24 hours)
            # Autonomous agents should only interact with avatars, not real people
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            
            posts = await self.db.posts.find({
                "user_id": {"$in": friend_ids},
                "post_type": "avatar",  # ONLY avatar posts
                "created_at": {"$gte": cutoff.isoformat()}
            }).sort([("created_at", -1)]).limit(limit).to_list(limit)
            
            return posts
            
        except Exception as e:
            print(f"   ❌ Error getting friend posts: {e}")
            return []
    
    async def _log_activity(self, activity_type: str, details: Dict):
        """Log bot activity"""
        try:
            # Generate description based on activity type
            description = ""
            if activity_type == "post_created":
                world = details.get("world_mode", "unknown")
                description = f"Created post in {world} world"
            elif activity_type == "post_like":
                description = "Liked a post"
            elif activity_type == "post_comment":
                comment_text = details.get("comment_text", "")
                if comment_text:
                    description = f"Commented: \"{comment_text[:50]}...\""
                else:
                    description = "Commented on a post"
            elif activity_type == "friend_request_sent":
                target_id = details.get("target_user_id", "")
                description = f"Sent friend request"
            elif activity_type == "profile_viewed":
                viewed_id = details.get("viewed_user_id", "")
                description = f"Viewed a profile"
            else:
                description = activity_type.replace("_", " ").title()
            
            activity = {
                "bot_id": self.bot_id,
                "user_id": self.bot_id,  # Also add user_id for frontend compatibility
                "bot_name": self.bot.get('avatar_name', self.bot.get('name')),
                "action_type": activity_type,
                "activity_type": activity_type,  # Keep both for compatibility
                "description": description,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "archetype": self.archetype
            }
            
            await self.db.autonomous_activities.insert_one(activity)
            
        except Exception as e:
            # Don't fail the whole action if logging fails
            print(f"   ⚠️  Logging failed: {e}")
    
    def reset_hourly_limit(self):
        """Reset hourly action counter"""
        self.actions_this_hour = 0
        print(f"♻️  {self.bot.get('avatar_name')} action limit reset")

