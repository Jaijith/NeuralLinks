"""
Simple Reactive Agent - Phase 1 MVP
Uses MCP (Model Context Protocol) clients for all actions
Orchestration pipeline selects available tools and performs actions
Random selection for now - will be replaced by state machine later
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.avatar.intelligent import IntelligentAvatar
from domain.avatar.config import get_archetype_config, get_post_prompt
from domain.avatar.mcp.server import mcp_server


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
        
        # MCP Server reference (all actions go through MCP tools)
        self.mcp_server = mcp_server
        
        # Available tools cache (refreshed each cycle)
        self.available_tools: List[Dict[str, Any]] = []
        
        print(f"{avatar_indicator} Initialized {bot.get('avatar_name', bot.get('name'))} ({self.archetype})")
    
    async def run_cycle(self):
        """Main activity cycle - runs every 10-15 minutes"""
        try:
            # Check if autonomy is still enabled
            if not await self._check_autonomy_enabled():
                return
            
            avatar_indicator = "✨ USER AVATAR" if self.is_user_avatar else "🤖"
            print(f"\n{'='*60}")
            print(f"🔄 {self.bot.get('avatar_name')} activity cycle {avatar_indicator}")
            print(f"{'='*60}")
            
            # Check if we're at action limit
            if self.actions_this_hour >= self.max_actions_per_hour:
                print(f"⏸️  Action limit reached for this hour")
                return
            
            # Refresh available MCP tools (based on enabled actions)
            await self._refresh_available_tools()
            
            if not self.available_tools:
                print(f"   ⏸️  No actions enabled for this avatar")
                return
            
            # Orchestration pipeline: Select and execute actions using MCP tools
            await self._orchestrate_actions()
            
            self.last_action_time = datetime.now(timezone.utc)
            
        except Exception as e:
            print(f"❌ Error in {self.bot.get('avatar_name')} cycle: {e}")
    
    async def _check_autonomy_enabled(self) -> bool:
        """Check if autonomy is still enabled for this avatar"""
        try:
            user = await self.db.users.find_one(
                {"id": self.bot_id},
                {"avatar_autonomous": 1}
            )
            
            if user and self.is_user_avatar:
                if not user.get('avatar_autonomous', False):
                    print(f"   ⏸️  Autonomy disabled for this avatar - skipping cycle")
                    return False
            
            return True
        except Exception as e:
            print(f"   ⚠️  Error checking autonomy: {e}")
            return True  # Continue anyway
    
    async def _refresh_available_tools(self):
        """Refresh list of available MCP tools for this avatar"""
        try:
            # Get available tools from MCP server (filters by permissions)
            self.available_tools = await self.mcp_server.get_available_tools_for_avatar(self.bot_id)
            
            tool_names = [tool.get('name') for tool in self.available_tools]
            if tool_names:
                print(f"   🔧 Available MCP tools: {', '.join(tool_names)}")
            else:
                print(f"   ⚠️  No MCP tools available (all actions disabled)")
        except Exception as e:
            print(f"   ⚠️  Error refreshing available tools: {e}")
            self.available_tools = []
    
    async def _orchestrate_actions(self):
        """
        Orchestration pipeline: Select and execute actions using MCP tools
        Currently uses random selection - will be replaced by state machine
        """
        try:
            # Group tools by category for weighted selection
            reaction_tools = [t for t in self.available_tools if t['name'] in ['like_post', 'comment_on_post']]
            creation_tools = [t for t in self.available_tools if t['name'] == 'create_post']
            social_tools = [t for t in self.available_tools if t['name'] in ['send_friend_request', 'accept_friend_request', 'message_friend']]
            discovery_tools = [t for t in self.available_tools if t['name'] == 'discover_profiles']
            
            # Random selection with weights (will be replaced by state machine)
            # For "hypo" activity level, prioritize posting to ensure all avatars post
            activity_level = self.bot.get('avatar_activity_level', 'medium')
            is_hypo = activity_level == 'hypo'
            
            # 1. Create post (reduced activity: 10% chance for hypo, 5% for others)
            post_chance = 0.1 if is_hypo else 0.05
            if random.random() < post_chance and creation_tools:
                await self._execute_creation_action(creation_tools[0])
            
            # 2. React to posts (reduced activity: 20% chance)
            if random.random() < 0.2 and reaction_tools:
                await self._execute_reaction_action(reaction_tools)
            
            # 3. Social actions (reduced activity: 10% chance)
            if random.random() < 0.1 and social_tools:
                await self._execute_social_action(social_tools)
            
            # 4. Discovery (reduced activity: 5% chance)
            if random.random() < 0.05 and discovery_tools:
                await self._execute_discovery_action(discovery_tools[0])
                
        except Exception as e:
            print(f"   ❌ Error in orchestration: {e}")
    
    async def _execute_reaction_action(self, reaction_tools: List[Dict[str, Any]]):
        """Execute reaction action using MCP tools (like_post or comment_on_post)"""
        try:
            # Get recent posts from friends
            posts = await self._get_friend_posts(limit=10)
            
            if not posts:
                print(f"   📬 No new posts to react to")
                return
            
            print(f"   📬 Found {len(posts)} posts to consider")
            
            # Select a tool (prefer comment if available, fallback to like)
            tool = None
            if any(t['name'] == 'comment_on_post' for t in reaction_tools):
                tool = next(t for t in reaction_tools if t['name'] == 'comment_on_post')
            elif any(t['name'] == 'like_post' for t in reaction_tools):
                tool = next(t for t in reaction_tools if t['name'] == 'like_post')
            
            if not tool:
                return
            
            # Find a post to react to
            for post in posts:
                if post['id'] in self.seen_posts or post['user_id'] == self.bot_id:
                    continue
                
                if await self._should_react_to_post(post):
                    self.seen_posts.add(post['id'])
                    
                    # Call MCP tool
                    arguments = {"post_id": post['id']}
                    if tool['name'] == 'comment_on_post':
                        # Comment tool will generate comment text if not provided
                        arguments["comment_text"] = None
                    
                    result = await self.mcp_server.call_tool(tool['name'], self.bot_id, arguments)
                    
                    if result.get('success'):
                        print(f"   ✅ {tool['name']} on post {post['id'][:20]}...")
                        self.actions_this_hour += 1
                        await asyncio.sleep(2)
                        
                        if self.actions_this_hour >= self.max_actions_per_hour:
                            break
                    else:
                        print(f"   ⚠️  {tool['name']} failed: {result.get('error', 'Unknown error')}")
                    
                    break  # One reaction per cycle
        
        except Exception as e:
            print(f"   ❌ Error executing reaction action: {e}")
    
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
    
    
    async def _execute_creation_action(self, tool: Dict[str, Any]):
        """Execute post creation using MCP tool"""
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
                
                # Increased cooldown periods to reduce activity
                activity_level = self.bot.get('avatar_activity_level', 'medium')
                if activity_level == 'hypo':
                    # Hypo mode: allow posting every 6 hours minimum (reduced activity)
                    min_hours = 6.0
                else:
                    # Other modes: use config min_hours but add 12 hours minimum
                    config_min = float(self.config['posting_frequency']['min_hours'])
                    min_hours = max(config_min, 12.0)  # At least 12 hours between posts
                
                if hours_since_last < min_hours:
                    print(f"   ⏸️  Too soon to post (last post {hours_since_last:.1f}h ago, need {min_hours}h)")
                    return
            
            # Call MCP tool to create post (tool will generate content)
            arguments = {
                "post_type": "general",
                "post_text": None  # Let MCP tool generate it
            }
            
            result = await self.mcp_server.call_tool(tool['name'], self.bot_id, arguments)
            
            if result.get('success'):
                print(f"   ✅ Created post via MCP: {result.get('post_id', 'unknown')[:20]}...")
                self.actions_this_hour += 1
            else:
                print(f"   ⚠️  Post creation failed: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            print(f"   ❌ Error executing creation action: {e}")
    
    async def _execute_social_action(self, social_tools: List[Dict[str, Any]]):
        """Execute social action using MCP tools (friend requests, messaging)"""
        try:
            # Prefer send_friend_request, then message_friend, then accept_friend_request
            tool = None
            if any(t['name'] == 'send_friend_request' for t in social_tools):
                # Try to send friend request
                tool = next(t for t in social_tools if t['name'] == 'send_friend_request')
                
                # Get current friends
                friendships = await self.db.friendships.find({
                    "$or": [
                        {"user_id": self.bot_id, "status": "accepted"},
                        {"friend_id": self.bot_id, "status": "accepted"}
                    ]
                }).to_list(1000)
                
                friend_ids = set()
                for f in friendships:
                    if f['user_id'] == self.bot_id:
                        friend_ids.add(f['friend_id'])
                    else:
                        friend_ids.add(f['user_id'])
                
                # Find AVATARS we're not friends with
                all_avatars = await self.db.users.find({
                    "$or": [
                        {"is_bot": True},
                        {"avatar_autonomous": True}
                    ],
                    "id": {"$ne": self.bot_id, "$nin": list(friend_ids)},
                    "avatar_name": {"$exists": True}
                }).to_list(10)
                
                if all_avatars:
                    candidate = random.choice(all_avatars)
                    if await self._should_befriend(candidate):
                        arguments = {"target_user_id": candidate['id']}
                        result = await self.mcp_server.call_tool(tool['name'], self.bot_id, arguments)
                        
                        if result.get('success'):
                            print(f"   ✅ Sent friend request via MCP")
                            self.actions_this_hour += 1
                        else:
                            print(f"   ⚠️  Friend request failed: {result.get('error', 'Unknown error')}")
                        return
            
            elif any(t['name'] == 'message_friend' for t in social_tools):
                # Try to message a friend
                tool = next(t for t in social_tools if t['name'] == 'message_friend')
                
                # Get friends
                friendships = await self.db.friendships.find({
                    "$or": [
                        {"user_id": self.bot_id, "status": "accepted"},
                        {"friend_id": self.bot_id, "status": "accepted"}
                    ]
                }).to_list(1000)
                
                friend_ids = []
                for f in friendships:
                    if f['user_id'] == self.bot_id:
                        friend_ids.append(f['friend_id'])
                    else:
                        friend_ids.append(f['user_id'])
                
                if friend_ids:
                    friend_id = random.choice(friend_ids)
                    arguments = {"friend_id": friend_id, "message_text": None}
                    result = await self.mcp_server.call_tool(tool['name'], self.bot_id, arguments)
                    
                    if result.get('success'):
                        print(f"   ✅ Sent message via MCP")
                        self.actions_this_hour += 1
                    else:
                        print(f"   ⚠️  Messaging failed: {result.get('error', 'Unknown error')}")
            
            elif any(t['name'] == 'accept_friend_request' for t in social_tools):
                # Accept friend requests (placeholder for now)
                print(f"   ✅ Checked for pending friend requests (accept enabled)")
        
        except Exception as e:
            print(f"   ❌ Error executing social action: {e}")
    
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
    
    async def _execute_discovery_action(self, tool: Dict[str, Any]):
        """Execute profile discovery using MCP tool"""
        try:
            arguments = {"limit": 5}
            result = await self.mcp_server.call_tool(tool['name'], self.bot_id, arguments)
            
            if result.get('success'):
                print(f"   ✅ Discovered profiles via MCP")
                self.actions_this_hour += 1
            else:
                print(f"   ⚠️  Profile discovery failed: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            print(f"   ❌ Error executing discovery action: {e}")
    
    async def _get_friend_posts(self, limit: int = 10) -> List[Dict]:
        """Get recent posts from friends"""
        try:
            # Get friend IDs (using correct schema: user_id and friend_id)
            friendships = await self.db.friendships.find({
                "$or": [
                    {"user_id": self.bot_id, "status": "accepted"},
                    {"friend_id": self.bot_id, "status": "accepted"}
                ]
            }).to_list(1000)
            
            friend_ids = []
            for f in friendships:
                if f['user_id'] == self.bot_id:
                    friend_ids.append(f['friend_id'])
                else:
                    friend_ids.append(f['user_id'])
            
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

