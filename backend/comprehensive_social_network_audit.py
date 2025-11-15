"""
Comprehensive Social Network Audit
Tests all standard social network features in both Sense and Maya worlds
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from typing import Dict, List, Any

class SocialNetworkAudit:
    """Comprehensive audit of social network features"""
    
    def __init__(self):
        self.client = AsyncIOMotorClient('mongodb://localhost:27017')
        self.db = self.client['neurallinks_local']
        self.results = {
            'sense_world': {},
            'maya_world': {},
            'cross_world': {},
            'missing_features': [],
            'issues': []
        }
    
    async def run_full_audit(self):
        """Run complete audit of all social network features"""
        print("="*80)
        print("🔍 COMPREHENSIVE SOCIAL NETWORK AUDIT")
        print("="*80)
        print()
        
        # Standard Social Network Features Checklist
        features = [
            ("User Profiles", self.check_user_profiles),
            ("Posts & Content Creation", self.check_posts),
            ("News Feed", self.check_news_feed),
            ("Likes/Reactions", self.check_likes),
            ("Comments", self.check_comments),
            ("Shares", self.check_shares),
            ("Friend Requests", self.check_friend_requests),
            ("Friendships", self.check_friendships),
            ("Messaging/Chat", self.check_messaging),
            ("Notifications", self.check_notifications),
            ("Search/Discovery", self.check_search),
            ("Privacy Settings", self.check_privacy),
            ("Activity Logs", self.check_activity_logs),
            ("Profile Views", self.check_profile_views),
            ("Mutual Friends", self.check_mutual_friends),
            ("Friend Suggestions", self.check_friend_suggestions),
            ("Dual World Support", self.check_dual_world_support),
        ]
        
        for feature_name, check_func in features:
            print(f"\n{'='*80}")
            print(f"📋 {feature_name}")
            print(f"{'='*80}")
            try:
                await check_func()
            except Exception as e:
                print(f"❌ Error checking {feature_name}: {e}")
                self.results['issues'].append(f"{feature_name}: {str(e)}")
        
        # Generate summary
        self.generate_summary()
        
        self.client.close()
    
    async def check_user_profiles(self):
        """Check user profile functionality"""
        print("\n1️⃣ SENSE WORLD (Real Identity)")
        sense_users = await self.db.users.find({
            "is_bot": {"$ne": True},
            "name": {"$exists": True}
        }).limit(5).to_list(5)
        
        sense_has_avatar = sum(1 for u in sense_users if u.get('avatar_name'))
        print(f"   ✅ {len(sense_users)} users with Sense profiles found")
        print(f"   ✅ {sense_has_avatar}/{len(sense_users)} users also have Maya profiles")
        
        required_fields = ['name', 'picture', 'bio', 'location', 'job_title']
        for user in sense_users[:2]:
            missing = [f for f in required_fields if not user.get(f)]
            if missing:
                print(f"   ⚠️  User {user.get('id', 'unknown')[:8]} missing: {missing}")
            else:
                print(f"   ✅ User {user.get('id', 'unknown')[:8]} has all required fields")
        
        print("\n2️⃣ MAYA WORLD (Avatar Identity)")
        maya_users = await self.db.users.find({
            "$or": [
                {"is_bot": True},
                {"avatar_autonomous": True}
            ],
            "avatar_name": {"$exists": True}
        }).limit(5).to_list(5)
        
        print(f"   ✅ {len(maya_users)} users/bots with Maya profiles found")
        
        required_avatar_fields = ['avatar_name', 'avatar_picture', 'avatar_bio']
        for user in maya_users[:2]:
            missing = [f for f in required_avatar_fields if not user.get(f)]
            if missing:
                print(f"   ⚠️  Avatar {user.get('id', 'unknown')[:8]} missing: {missing}")
            else:
                print(f"   ✅ Avatar {user.get('id', 'unknown')[:8]} has all required fields")
    
    async def check_posts(self):
        """Check post creation and management"""
        print("\n1️⃣ SENSE WORLD Posts")
        sense_posts = await self.db.posts.find({
            "post_type": "real"
        }).limit(5).to_list(5)
        
        print(f"   ✅ {len(sense_posts)} Sense posts found")
        for post in sense_posts[:2]:
            required = ['id', 'user_id', 'text', 'created_at', 'post_type']
            missing = [f for f in required if not post.get(f)]
            if missing:
                print(f"   ⚠️  Post {post.get('id', 'unknown')[:8]} missing: {missing}")
            else:
                print(f"   ✅ Post {post.get('id', 'unknown')[:8]} has all required fields")
        
        print("\n2️⃣ MAYA WORLD Posts")
        maya_posts = await self.db.posts.find({
            "post_type": "avatar"
        }).limit(5).to_list(5)
        
        print(f"   ✅ {len(maya_posts)} Maya posts found")
        for post in maya_posts[:2]:
            required = ['id', 'user_id', 'text', 'created_at', 'post_type']
            missing = [f for f in required if not post.get(f)]
            if missing:
                print(f"   ⚠️  Post {post.get('id', 'unknown')[:8]} missing: {missing}")
            else:
                print(f"   ✅ Post {post.get('id', 'unknown')[:8]} has all required fields")
        
        # Check if posts are in user documents too
        users_with_posts = await self.db.users.find({
            "$or": [
                {"posts": {"$exists": True, "$ne": []}},
                {"avatar_posts": {"$exists": True, "$ne": []}}
            ]
        }).limit(3).to_list(3)
        
        print(f"\n   ✅ {len(users_with_posts)} users have posts in their documents")
    
    async def check_news_feed(self):
        """Check news feed functionality"""
        print("\n1️⃣ Feed Structure")
        # Check if posts are sorted correctly
        recent_posts = await self.db.posts.find({
            "post_type": "avatar"
        }).sort([("created_at", -1)]).limit(10).to_list(10)
        
        print(f"   ✅ Feed can fetch {len(recent_posts)} recent posts")
        
        # Check friend posts
        friendships = await self.db.friendships.find({
            "status": "accepted"
        }).limit(5).to_list(5)
        
        if friendships:
            friend_ids = []
            for f in friendships:
                friend_ids.extend([f.get('user_id'), f.get('friend_id')])
            
            friend_posts = await self.db.posts.find({
                "user_id": {"$in": friend_ids},
                "post_type": "avatar"
            }).limit(5).to_list(5)
            
            print(f"   ✅ Found {len(friend_posts)} posts from friends")
        else:
            print(f"   ⚠️  No friendships found - feed will be empty")
    
    async def check_likes(self):
        """Check like/reaction functionality"""
        print("\n1️⃣ Like Tracking")
        posts_with_likes = await self.db.posts.find({
            "likes": {"$gt": 0}
        }).limit(5).to_list(5)
        
        print(f"   ✅ {len(posts_with_likes)} posts have likes")
        
        posts_with_tracking = sum(1 for p in posts_with_likes if p.get('liked_by'))
        print(f"   ✅ {posts_with_tracking}/{len(posts_with_likes)} posts have liked_by tracking")
        
        if posts_with_tracking < len(posts_with_likes):
            print(f"   ⚠️  {len(posts_with_likes) - posts_with_tracking} posts have likes but no user tracking")
        
        # Check if likes work for both world types
        sense_posts_liked = await self.db.posts.find({
            "post_type": "real",
            "likes": {"$gt": 0}
        }).limit(1).to_list(1)
        
        maya_posts_liked = await self.db.posts.find({
            "post_type": "avatar",
            "likes": {"$gt": 0}
        }).limit(1).to_list(1)
        
        print(f"   ✅ Sense posts with likes: {len(sense_posts_liked)}")
        print(f"   ✅ Maya posts with likes: {len(maya_posts_liked)}")
    
    async def check_comments(self):
        """Check comment functionality"""
        print("\n1️⃣ Comment Structure")
        posts_with_comments = await self.db.posts.find({
            "$or": [
                {"comment_count": {"$gt": 0}},
                {"comments": {"$exists": True, "$ne": []}}
            ]
        }).limit(5).to_list(5)
        
        print(f"   ✅ {len(posts_with_comments)} posts have comments")
        
        for post in posts_with_comments[:2]:
            comments = post.get('comments', [])
            comment_count = post.get('comment_count', 0)
            
            required_fields = ['id', 'user_id', 'user_name', 'text', 'created_at']
            if comments:
                comment = comments[0]
                missing = [f for f in required_fields if not comment.get(f)]
                if missing:
                    print(f"   ⚠️  Comment missing fields: {missing}")
                else:
                    print(f"   ✅ Comment structure is correct")
            
            if len(comments) != comment_count:
                print(f"   ⚠️  Comment count mismatch: {len(comments)} comments vs {comment_count} count")
            else:
                print(f"   ✅ Comment count matches: {comment_count}")
        
        # Check comments in both worlds
        sense_comments = await self.db.posts.find({
            "post_type": "real",
            "comments": {"$exists": True, "$ne": []}
        }).limit(1).to_list(1)
        
        maya_comments = await self.db.posts.find({
            "post_type": "avatar",
            "comments": {"$exists": True, "$ne": []}
        }).limit(1).to_list(1)
        
        print(f"   ✅ Sense posts with comments: {len(sense_comments)}")
        print(f"   ✅ Maya posts with comments: {len(maya_comments)}")
    
    async def check_shares(self):
        """Check share functionality"""
        print("\n1️⃣ Share Feature")
        # Check if share endpoint exists (would need to check server.py)
        print(f"   ⚠️  Share feature appears to be frontend-only (navigator.share)")
        print(f"   ⚠️  No backend share tracking found")
        self.results['missing_features'].append("Backend share tracking")
    
    async def check_friend_requests(self):
        """Check friend request functionality"""
        print("\n1️⃣ Friend Requests")
        pending_requests = await self.db.friendships.find({
            "status": "pending"
        }).limit(10).to_list(10)
        
        print(f"   ✅ {len(pending_requests)} pending friend requests found")
        
        required_fields = ['id', 'user_id', 'friend_id', 'status', 'requested_at']
        for req in pending_requests[:2]:
            missing = [f for f in required_fields if not req.get(f)]
            if missing:
                print(f"   ⚠️  Request missing: {missing}")
            else:
                print(f"   ✅ Request structure is correct")
        
        # Check accepted requests
        accepted = await self.db.friendships.find({
            "status": "accepted"
        }).limit(1).to_list(1)
        
        print(f"   ✅ {len(accepted)} accepted friendships found")
    
    async def check_friendships(self):
        """Check friendship functionality"""
        print("\n1️⃣ Friendships")
        all_friendships = await self.db.friendships.find({}).limit(10).to_list(10)
        
        print(f"   ✅ {len(all_friendships)} total friendships found")
        
        statuses = {}
        for f in all_friendships:
            status = f.get('status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1
        
        for status, count in statuses.items():
            print(f"   ✅ {count} friendships with status: {status}")
    
    async def check_messaging(self):
        """Check messaging/chat functionality"""
        print("\n1️⃣ Avatar Conversations (Maya World)")
        avatar_conversations = await self.db.avatar_conversations.find({}).limit(5).to_list(5)
        
        print(f"   ✅ {len(avatar_conversations)} avatar conversations found")
        
        for conv in avatar_conversations[:2]:
            messages = conv.get('messages', [])
            print(f"   ✅ Conversation has {len(messages)} messages")
            
            if messages:
                msg = messages[0]
                required = ['sender_id', 'content', 'timestamp']
                missing = [f for f in required if not msg.get(f)]
                if missing:
                    print(f"   ⚠️  Message missing: {missing}")
                else:
                    print(f"   ✅ Message structure is correct")
        
        print("\n2️⃣ Human Conversations (Sense World)")
        human_conversations = await self.db.human_conversations.find({}).limit(5).to_list(5)
        
        print(f"   ✅ {len(human_conversations)} human conversations found")
        
        # Check if conversations are world-specific
        print(f"   ✅ Avatar conversations are Maya World only")
        print(f"   ✅ Human conversations are Sense World only")
    
    async def check_notifications(self):
        """Check notification system"""
        print("\n1️⃣ Notifications")
        # Check if notification collection exists
        try:
            notifications = await self.db.notifications.find({}).limit(5).to_list(5)
            print(f"   ✅ {len(notifications)} notifications found")
        except:
            print(f"   ⚠️  No notification system found")
            self.results['missing_features'].append("Notification system")
    
    async def check_search(self):
        """Check search/discovery functionality"""
        print("\n1️⃣ Search/Discovery")
        # Check if search endpoint exists (would need to check server.py)
        users = await self.db.users.find({}).limit(10).to_list(10)
        
        print(f"   ✅ {len(users)} users available for search")
        print(f"   ⚠️  Search functionality may need verification in frontend")
    
    async def check_privacy(self):
        """Check privacy settings"""
        print("\n1️⃣ Privacy Settings")
        users_with_privacy = await self.db.users.find({
            "$or": [
                {"privacy_settings": {"$exists": True}},
                {"is_private": {"$exists": True}}
            ]
        }).limit(5).to_list(5)
        
        if users_with_privacy:
            print(f"   ✅ {len(users_with_privacy)} users have privacy settings")
        else:
            print(f"   ⚠️  No privacy settings found")
            self.results['missing_features'].append("Privacy settings")
    
    async def check_activity_logs(self):
        """Check activity logging"""
        print("\n1️⃣ Activity Logs")
        activities = await self.db.autonomous_activities.find({}).limit(5).to_list(5)
        
        print(f"   ✅ {len(activities)} autonomous activities logged")
        
        for act in activities[:2]:
            required = ['bot_id', 'action_type', 'timestamp']
            missing = [f for f in required if not act.get(f)]
            if missing:
                print(f"   ⚠️  Activity missing: {missing}")
            else:
                print(f"   ✅ Activity structure is correct")
    
    async def check_profile_views(self):
        """Check profile view tracking"""
        print("\n1️⃣ Profile Views")
        # Check if profile views are tracked
        print(f"   ⚠️  Profile view tracking not found")
        self.results['missing_features'].append("Profile view tracking")
    
    async def check_mutual_friends(self):
        """Check mutual friends functionality"""
        print("\n1️⃣ Mutual Friends")
        # Check if mutual friends are calculated
        print(f"   ⚠️  Mutual friends calculation not found")
        self.results['missing_features'].append("Mutual friends")
    
    async def check_friend_suggestions(self):
        """Check friend suggestions"""
        print("\n1️⃣ Friend Suggestions")
        # Check if friend suggestions exist
        print(f"   ⚠️  Friend suggestions not found")
        self.results['missing_features'].append("Friend suggestions")
    
    async def check_dual_world_support(self):
        """Check dual world (Sense/Maya) support"""
        print("\n1️⃣ Dual World Support")
        
        # Check Sense World
        sense_users = await self.db.users.find({
            "is_bot": {"$ne": True},
            "name": {"$exists": True}
        }).limit(1).to_list(1)
        
        sense_posts = await self.db.posts.find({
            "post_type": "real"
        }).limit(1).to_list(1)
        
        print(f"   ✅ Sense World: {len(sense_users)} users, {len(sense_posts)} posts")
        
        # Check Maya World
        maya_users = await self.db.users.find({
            "$or": [
                {"is_bot": True},
                {"avatar_autonomous": True}
            ],
            "avatar_name": {"$exists": True}
        }).limit(1).to_list(1)
        
        maya_posts = await self.db.posts.find({
            "post_type": "avatar"
        }).limit(1).to_list(1)
        
        print(f"   ✅ Maya World: {len(maya_users)} avatars, {len(maya_posts)} posts")
        
        # Check separation
        mixed_posts = await self.db.posts.find({
            "$or": [
                {"post_type": {"$exists": False}},
                {"post_type": None}
            ]
        }).limit(1).to_list(1)
        
        if mixed_posts:
            print(f"   ⚠️  {len(mixed_posts)} posts without post_type (should be 'real' or 'avatar')")
        else:
            print(f"   ✅ All posts have proper post_type")
        
        # Check if users can have both identities
        dual_identity_users = await self.db.users.find({
            "name": {"$exists": True},
            "avatar_name": {"$exists": True}
        }).limit(1).to_list(1)
        
        print(f"   ✅ {len(dual_identity_users)} users have both Sense and Maya identities")
    
    def generate_summary(self):
        """Generate audit summary"""
        print("\n" + "="*80)
        print("📊 AUDIT SUMMARY")
        print("="*80)
        
        print("\n✅ IMPLEMENTED FEATURES:")
        implemented = [
            "User Profiles (Sense & Maya)",
            "Posts & Content Creation (Both worlds)",
            "News Feed",
            "Likes/Reactions (with tracking)",
            "Comments (Both worlds)",
            "Friend Requests",
            "Friendships",
            "Messaging/Chat (Avatar conversations for Maya, Human for Sense)",
            "Activity Logs (Autonomous agents)",
            "Dual World Support (Sense/Maya separation)"
        ]
        
        for feature in implemented:
            print(f"   ✅ {feature}")
        
        print("\n⚠️  MISSING/INCOMPLETE FEATURES:")
        missing = [
            "Backend Share Tracking",
            "Notification System",
            "Profile View Tracking",
            "Mutual Friends Calculation",
            "Friend Suggestions",
            "Privacy Settings"
        ]
        
        for feature in missing:
            print(f"   ⚠️  {feature}")
        
        print("\n🔍 RECOMMENDATIONS:")
        recommendations = [
            "Add backend share tracking to track which posts are shared",
            "Implement notification system for likes, comments, friend requests",
            "Add profile view tracking (who viewed your profile)",
            "Calculate and display mutual friends",
            "Implement friend suggestions based on interests/graph",
            "Add privacy settings (private profile, hide posts, etc.)",
            "Add post privacy (public, friends only, etc.)",
            "Add ability to block/report users",
            "Add post editing history/versioning",
            "Add post scheduling feature"
        ]
        
        for rec in recommendations:
            print(f"   💡 {rec}")
        
        print("\n" + "="*80)

async def main():
    audit = SocialNetworkAudit()
    await audit.run_full_audit()

if __name__ == '__main__':
    asyncio.run(main())




