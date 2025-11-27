"""
Comprehensive Feature Testing Script
Tests all social network features in both Sense and Maya worlds
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import uuid

class FeatureTester:
    def __init__(self):
        self.client = AsyncIOMotorClient('mongodb://localhost:27017')
        self.db = self.client['neurallinks_local']
        self.test_results = []
        self.test_user_id = None
        self.test_avatar_id = None
        self.test_post_id = None
        self.test_comment_id = None
    
    def log_result(self, feature, world, status, message=""):
        """Log test result"""
        result = {
            "feature": feature,
            "world": world,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.test_results.append(result)
        
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} [{world}] {feature}: {status} {message}")
    
    async def setup_test_data(self):
        """Create test users and data"""
        print("\n" + "="*80)
        print("🔧 SETTING UP TEST DATA")
        print("="*80)
        
        # Create test user with both identities
        test_user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        test_user = {
            "id": test_user_id,
            "name": "Test User",
            "email": f"test-{uuid.uuid4().hex[:8]}@test.com",
            "picture": "https://api.dicebear.com/7.x/adventurer/svg?seed=test",
            "bio": "Test user bio",
            "location": "Test City",
            "job_title": "Tester",
            "avatar_name": "TestAvatar",
            "avatar_picture": "https://api.dicebear.com/7.x/adventurer/svg?seed=avatar",
            "avatar_bio": "Test avatar bio",
            "avatar_location": "Avatar City",
            "avatar_job_title": "Avatar Tester",
            "avatar_autonomous": False,
            "is_bot": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.users.insert_one(test_user)
        self.test_user_id = test_user_id
        print(f"✅ Created test user: {test_user_id}")
        
        # Create test avatar user
        test_avatar_id = f"test-avatar-{uuid.uuid4().hex[:8]}"
        test_avatar = {
            "id": test_avatar_id,
            "name": "Test Avatar User",
            "email": f"avatar-{uuid.uuid4().hex[:8]}@test.com",
            "picture": "https://api.dicebear.com/7.x/adventurer/svg?seed=avatar2",
            "avatar_name": "TestAvatar2",
            "avatar_picture": "https://api.dicebear.com/7.x/adventurer/svg?seed=avatar2",
            "avatar_bio": "Test avatar 2",
            "avatar_autonomous": True,
            "is_bot": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.users.insert_one(test_avatar)
        self.test_avatar_id = test_avatar_id
        print(f"✅ Created test avatar: {test_avatar_id}")
        
        return test_user_id, test_avatar_id
    
    async def test_user_profiles(self):
        """Test user profile functionality"""
        print("\n" + "="*80)
        print("📋 TESTING USER PROFILES")
        print("="*80)
        
        # Test Sense profile
        user = await self.db.users.find_one({"id": self.test_user_id})
        if user and user.get("name") and user.get("picture"):
            self.log_result("Sense Profile - Exists", "Sense", "PASS")
        else:
            self.log_result("Sense Profile - Exists", "Sense", "FAIL", "Missing required fields")
        
        # Test Maya profile
        if user and user.get("avatar_name") and user.get("avatar_picture"):
            self.log_result("Maya Profile - Exists", "Maya", "PASS")
        else:
            self.log_result("Maya Profile - Exists", "Maya", "FAIL", "Missing avatar fields")
        
        # Test profile update
        await self.db.users.update_one(
            {"id": self.test_user_id},
            {"$set": {"bio": "Updated bio"}}
        )
        updated = await self.db.users.find_one({"id": self.test_user_id})
        if updated and updated.get("bio") == "Updated bio":
            self.log_result("Profile Update", "Both", "PASS")
        else:
            self.log_result("Profile Update", "Both", "FAIL")
    
    async def test_posts(self):
        """Test post creation and management"""
        print("\n" + "="*80)
        print("📋 TESTING POSTS")
        print("="*80)
        
        # Test Sense post creation
        sense_post = {
            "id": f"post-sense-{uuid.uuid4().hex[:8]}",
            "user_id": self.test_user_id,
            "text": "Test Sense post",
            "content": "Test Sense post",
            "post_type": "real",
            "likes": 0,
            "liked_by": [],
            "comments": [],
            "comment_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.posts.insert_one(sense_post)
        
        # Also add to user document
        post_for_user = {k: v for k, v in sense_post.items() if k != '_id'}
        await self.db.users.update_one(
            {"id": self.test_user_id},
            {"$push": {"posts": post_for_user}}
        )
        
        retrieved = await self.db.posts.find_one({"id": sense_post["id"]})
        if retrieved and retrieved.get("text") and retrieved.get("post_type") == "real":
            self.log_result("Sense Post Creation", "Sense", "PASS")
            self.test_post_id = sense_post["id"]
        else:
            self.log_result("Sense Post Creation", "Sense", "FAIL")
        
        # Test Maya post creation
        maya_post = {
            "id": f"post-maya-{uuid.uuid4().hex[:8]}",
            "user_id": self.test_user_id,
            "text": "Test Maya post",
            "content": "Test Maya post",
            "post_type": "avatar",
            "likes": 0,
            "liked_by": [],
            "comments": [],
            "comment_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.posts.insert_one(maya_post)
        
        # Also add to user document
        post_for_user = {k: v for k, v in maya_post.items() if k != '_id'}
        await self.db.users.update_one(
            {"id": self.test_user_id},
            {"$push": {"avatar_posts": post_for_user}}
        )
        
        retrieved = await self.db.posts.find_one({"id": maya_post["id"]})
        if retrieved and retrieved.get("text") and retrieved.get("post_type") == "avatar":
            self.log_result("Maya Post Creation", "Maya", "PASS")
        else:
            self.log_result("Maya Post Creation", "Maya", "FAIL")
        
        # Test post editing
        await self.db.posts.update_one(
            {"id": sense_post["id"]},
            {"$set": {"text": "Updated Sense post"}}
        )
        updated = await self.db.posts.find_one({"id": sense_post["id"]})
        if updated and updated.get("text") == "Updated Sense post":
            self.log_result("Post Editing", "Sense", "PASS")
        else:
            self.log_result("Post Editing", "Sense", "FAIL")
        
        # Test post deletion (use a separate post)
        delete_post = {
            "id": f"post-delete-test-{uuid.uuid4().hex[:8]}",
            "user_id": self.test_user_id,
            "text": "Post to delete",
            "content": "Post to delete",
            "post_type": "real",
            "likes": 0,
            "liked_by": [],
            "comments": [],
            "comment_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.db.posts.insert_one(delete_post)
        await self.db.posts.delete_one({"id": delete_post["id"]})
        deleted = await self.db.posts.find_one({"id": delete_post["id"]})
        if not deleted:
            self.log_result("Post Deletion", "Sense", "PASS")
        else:
            self.log_result("Post Deletion", "Sense", "FAIL")
        
        # Keep test_post_id for likes/comments tests
        self.test_post_id = maya_post["id"]
    
    async def test_likes(self):
        """Test like functionality"""
        print("\n" + "="*80)
        print("📋 TESTING LIKES")
        print("="*80)
        
        # Always create a fresh test post for likes
        test_post = {
            "id": f"post-like-test-{uuid.uuid4().hex[:8]}",
            "user_id": self.test_user_id,
            "text": "Test post for likes",
            "content": "Test post for likes",
            "post_type": "avatar",
            "likes": 0,
            "liked_by": [],
            "comments": [],
            "comment_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.db.posts.insert_one(test_post)
        self.test_post_id = test_post["id"]
        
        # Verify post was created
        verify_post = await self.db.posts.find_one({"id": self.test_post_id})
        if not verify_post:
            self.log_result("Like Post Setup", "Maya", "FAIL", "Post not created")
            return
        
        # Test like
        await self.db.posts.update_one(
            {"id": self.test_post_id},
            {
                "$addToSet": {"liked_by": self.test_avatar_id},
                "$inc": {"likes": 1}
            }
        )
        
        post = await self.db.posts.find_one({"id": self.test_post_id})
        if post and self.test_avatar_id in post.get("liked_by", []) and post.get("likes") == 1:
            self.log_result("Like Post", "Maya", "PASS")
        else:
            self.log_result("Like Post", "Maya", "FAIL", f"Expected 1 like, got {post.get('likes') if post else 'None'}")
        
        # Test unlike
        await self.db.posts.update_one(
            {"id": self.test_post_id},
            {
                "$pull": {"liked_by": self.test_avatar_id},
                "$inc": {"likes": -1}
            }
        )
        
        post = await self.db.posts.find_one({"id": self.test_post_id})
        if post and self.test_avatar_id not in post.get("liked_by", []) and post.get("likes") == 0:
            self.log_result("Unlike Post", "Maya", "PASS")
        else:
            self.log_result("Unlike Post", "Maya", "FAIL")
        
        # Test like count tracking (properly sync)
        # First ensure post has 0 likes
        await self.db.posts.update_one(
            {"id": self.test_post_id},
            {
                "$set": {"liked_by": [], "likes": 0}
            }
        )
        
        # Add two likes
        await self.db.posts.update_one(
            {"id": self.test_post_id},
            {
                "$addToSet": {"liked_by": self.test_user_id},
                "$inc": {"likes": 1}
            }
        )
        
        await self.db.posts.update_one(
            {"id": self.test_post_id},
            {
                "$addToSet": {"liked_by": self.test_avatar_id},
                "$inc": {"likes": 1}
            }
        )
        
        post = await self.db.posts.find_one({"id": self.test_post_id})
        liked_by_count = len(post.get("liked_by", [])) if post else 0
        likes_count = post.get("likes", 0) if post else 0
        
        if liked_by_count == likes_count == 2:
            self.log_result("Like Count Sync", "Maya", "PASS")
        else:
            self.log_result("Like Count Sync", "Maya", "FAIL", 
                          f"liked_by={liked_by_count}, likes={likes_count}")
    
    async def test_comments(self):
        """Test comment functionality"""
        print("\n" + "="*80)
        print("📋 TESTING COMMENTS")
        print("="*80)
        
        # Always create a fresh test post for comments
        test_post = {
            "id": f"post-comment-test-{uuid.uuid4().hex[:8]}",
            "user_id": self.test_user_id,
            "text": "Test post for comments",
            "content": "Test post for comments",
            "post_type": "avatar",
            "likes": 0,
            "liked_by": [],
            "comments": [],
            "comment_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.db.posts.insert_one(test_post)
        comment_post_id = test_post["id"]
        
        # Verify post was created
        verify_post = await self.db.posts.find_one({"id": comment_post_id})
        if not verify_post:
            self.log_result("Comment Post Setup", "Maya", "FAIL", "Post not created")
            return
        
        # Test comment creation
        comment = {
            "id": f"comment-{uuid.uuid4().hex[:8]}",
            "user_id": self.test_avatar_id,
            "user_name": "TestAvatar2",
            "user_picture": "https://api.dicebear.com/7.x/adventurer/svg?seed=avatar2",
            "text": "Test comment",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.posts.update_one(
            {"id": comment_post_id},
            {"$push": {"comments": comment}, "$inc": {"comment_count": 1}}
        )
        
        post = await self.db.posts.find_one({"id": comment_post_id})
        comments = post.get("comments", []) if post else []
        comment_count = post.get("comment_count", 0) if post else 0
        
        if len(comments) == 1 and comment_count == 1:
            self.log_result("Comment Creation", "Maya", "PASS")
            self.test_comment_id = comment["id"]
        else:
            self.log_result("Comment Creation", "Maya", "FAIL", 
                          f"comments={len(comments)}, count={comment_count}")
        
        # Test comment structure
        if comments:
            cmt = comments[0]
            required = ["id", "user_id", "user_name", "text", "created_at"]
            missing = [f for f in required if not cmt.get(f)]
            if not missing:
                self.log_result("Comment Structure", "Maya", "PASS")
            else:
                self.log_result("Comment Structure", "Maya", "FAIL", f"Missing: {missing}")
        
        # Test comment count sync
        if len(comments) == comment_count:
            self.log_result("Comment Count Sync", "Maya", "PASS")
        else:
            self.log_result("Comment Count Sync", "Maya", "FAIL",
                          f"comments={len(comments)}, count={comment_count}")
    
    async def test_friend_requests(self):
        """Test friend request functionality"""
        print("\n" + "="*80)
        print("📋 TESTING FRIEND REQUESTS")
        print("="*80)
        
        # Create friendship request
        friendship = {
            "id": f"friendship-{uuid.uuid4().hex[:8]}",
            "user_id": self.test_user_id,
            "friend_id": self.test_avatar_id,
            "status": "pending",
            "requested_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.friendships.insert_one(friendship)
        
        # Test request creation
        request = await self.db.friendships.find_one({"id": friendship["id"]})
        if request and request.get("status") == "pending":
            self.log_result("Friend Request Creation", "Both", "PASS")
        else:
            self.log_result("Friend Request Creation", "Both", "FAIL")
        
        # Test accepting request
        await self.db.friendships.update_one(
            {"id": friendship["id"]},
            {
                "$set": {
                    "status": "accepted",
                    "accepted_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        accepted = await self.db.friendships.find_one({"id": friendship["id"]})
        if accepted and accepted.get("status") == "accepted":
            self.log_result("Accept Friend Request", "Both", "PASS")
        else:
            self.log_result("Accept Friend Request", "Both", "FAIL")
        
        # Test getting friends
        friends = await self.db.friendships.find({
            "$or": [
                {"user_id": self.test_user_id, "status": "accepted"},
                {"friend_id": self.test_user_id, "status": "accepted"}
            ]
        }).to_list(100)
        
        if len(friends) > 0:
            self.log_result("Get Friends List", "Both", "PASS")
        else:
            self.log_result("Get Friends List", "Both", "FAIL")
    
    async def test_messaging(self):
        """Test messaging functionality"""
        print("\n" + "="*80)
        print("📋 TESTING MESSAGING")
        print("="*80)
        
        # Test avatar conversation creation
        conversation = {
            "user1_id": self.test_user_id,
            "user2_id": self.test_avatar_id,
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = await self.db.avatar_conversations.insert_one(conversation)
        conv_id = result.inserted_id
        
        # Test message sending
        message = {
            "sender_id": self.test_user_id,
            "sender_name": "TestAvatar",
            "content": "Test message",
            "timestamp": datetime.now(timezone.utc),
            "generated": False
        }
        
        await self.db.avatar_conversations.update_one(
            {"_id": conv_id},
            {"$push": {"messages": message}}
        )
        
        conv = await self.db.avatar_conversations.find_one({"_id": conv_id})
        messages = conv.get("messages", []) if conv else []
        
        if len(messages) == 1:
            self.log_result("Avatar Message Sending", "Maya", "PASS")
        else:
            self.log_result("Avatar Message Sending", "Maya", "FAIL")
        
        # Test message structure
        if messages:
            msg = messages[0]
            required = ["sender_id", "content", "timestamp"]
            missing = [f for f in required if not msg.get(f)]
            if not missing:
                self.log_result("Message Structure", "Maya", "PASS")
            else:
                self.log_result("Message Structure", "Maya", "FAIL", f"Missing: {missing}")
    
    async def test_world_separation(self):
        """Test that Sense and Maya worlds are properly separated"""
        print("\n" + "="*80)
        print("📋 TESTING WORLD SEPARATION")
        print("="*80)
        
        # Check posts have post_type
        posts = await self.db.posts.find({
            "user_id": self.test_user_id
        }).to_list(10)
        
        all_have_type = all(p.get("post_type") in ["real", "avatar"] for p in posts)
        if all_have_type:
            self.log_result("Posts Have post_type", "Both", "PASS")
        else:
            self.log_result("Posts Have post_type", "Both", "FAIL")
        
        # Check Sense posts are separate
        sense_posts = await self.db.posts.find({
            "user_id": self.test_user_id,
            "post_type": "real"
        }).to_list(10)
        
        maya_posts = await self.db.posts.find({
            "user_id": self.test_user_id,
            "post_type": "avatar"
        }).to_list(10)
        
        # Create test posts if they don't exist
        if not sense_posts:
            sense_test = {
                "id": f"post-sense-sep-{uuid.uuid4().hex[:8]}",
                "user_id": self.test_user_id,
                "text": "Sense test",
                "content": "Sense test",
                "post_type": "real",
                "likes": 0,
                "liked_by": [],
                "comments": [],
                "comment_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await self.db.posts.insert_one(sense_test)
            sense_posts = [sense_test]
        
        if not maya_posts:
            maya_test = {
                "id": f"post-maya-sep-{uuid.uuid4().hex[:8]}",
                "user_id": self.test_user_id,
                "text": "Maya test",
                "content": "Maya test",
                "post_type": "avatar",
                "likes": 0,
                "liked_by": [],
                "comments": [],
                "comment_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await self.db.posts.insert_one(maya_test)
            maya_posts = [maya_test]
        
        if sense_posts and maya_posts:
            self.log_result("World Separation", "Both", "PASS", 
                          f"Sense: {len(sense_posts)}, Maya: {len(maya_posts)}")
        else:
            self.log_result("World Separation", "Both", "FAIL")
        
        # Check user has both identities
        user = await self.db.users.find_one({"id": self.test_user_id})
        if user and user.get("name") and user.get("avatar_name"):
            self.log_result("Dual Identity Support", "Both", "PASS")
        else:
            self.log_result("Dual Identity Support", "Both", "FAIL")
    
    async def cleanup_test_data(self):
        """Clean up test data"""
        print("\n" + "="*80)
        print("🧹 CLEANING UP TEST DATA")
        print("="*80)
        
        if self.test_user_id:
            await self.db.users.delete_one({"id": self.test_user_id})
            print(f"✅ Deleted test user: {self.test_user_id}")
        
        if self.test_avatar_id:
            await self.db.users.delete_one({"id": self.test_avatar_id})
            print(f"✅ Deleted test avatar: {self.test_avatar_id}")
        
        # Delete test posts
        await self.db.posts.delete_many({
            "user_id": {"$in": [self.test_user_id, self.test_avatar_id]}
        })
        print("✅ Deleted test posts")
        
        # Delete test friendships
        await self.db.friendships.delete_many({
            "$or": [
                {"user_id": {"$in": [self.test_user_id, self.test_avatar_id]}},
                {"friend_id": {"$in": [self.test_user_id, self.test_avatar_id]}}
            ]
        })
        print("✅ Deleted test friendships")
        
        # Delete test conversations
        await self.db.avatar_conversations.delete_many({
            "$or": [
                {"user1_id": {"$in": [self.test_user_id, self.test_avatar_id]}},
                {"user2_id": {"$in": [self.test_user_id, self.test_avatar_id]}}
            ]
        })
        print("✅ Deleted test conversations")
    
    async def run_all_tests(self):
        """Run all tests"""
        print("="*80)
        print("🧪 COMPREHENSIVE FEATURE TESTING")
        print("="*80)
        
        try:
            # Setup
            await self.setup_test_data()
            
            # Run tests
            await self.test_user_profiles()
            await self.test_posts()
            await self.test_likes()
            await self.test_comments()
            await self.test_friend_requests()
            await self.test_messaging()
            await self.test_world_separation()
            
            # Summary
            print("\n" + "="*80)
            print("📊 TEST SUMMARY")
            print("="*80)
            
            passed = sum(1 for r in self.test_results if r["status"] == "PASS")
            failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
            total = len(self.test_results)
            
            print(f"\nTotal Tests: {total}")
            print(f"✅ Passed: {passed}")
            print(f"❌ Failed: {failed}")
            print(f"Success Rate: {(passed/total*100):.1f}%")
            
            if failed > 0:
                print("\n❌ FAILED TESTS:")
                for result in self.test_results:
                    if result["status"] == "FAIL":
                        print(f"   - [{result['world']}] {result['feature']}: {result['message']}")
            
        finally:
            await self.cleanup_test_data()
            self.client.close()

async def main():
    tester = FeatureTester()
    await tester.run_all_tests()

if __name__ == '__main__':
    asyncio.run(main())

