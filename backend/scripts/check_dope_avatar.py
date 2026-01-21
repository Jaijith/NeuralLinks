#!/usr/bin/env python3
"""
Check if DOPE avatar is properly set up and running
Verifies: State-aware agent, Event cycle, Activity system
"""
import asyncio
import os
import sys
import json
import boto3
from datetime import datetime, timezone, timedelta

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from motor.motor_asyncio import AsyncIOMotorClient


def get_production_mongo_url():
    """Get MongoDB URL from AWS Secrets Manager"""
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name='us-west-1'
        )
        
        secret_response = client.get_secret_value(SecretId='2n1/mongodb/uri')
        
        if 'SecretString' in secret_response:
            secret = secret_response['SecretString']
            try:
                secret_dict = json.loads(secret)
                return secret_dict.get('uri') or secret_dict.get('MONGO_URL')
            except json.JSONDecodeError:
                return secret
        else:
            raise Exception("Secret not found in expected format")
            
    except Exception as e:
        print(f"❌ Error retrieving secret: {e}")
        sys.exit(1)


async def check_avatar():
    """Comprehensive check for DOPE avatar"""
    
    print("=" * 80)
    print("║     🤖 DOPE AVATAR - COMPREHENSIVE CHECK                                 ║")
    print("=" * 80)
    
    # Get production MongoDB URL
    mongo_url = get_production_mongo_url()
    
    # Connect to MongoDB
    print(f"\n🔌 Connecting to PRODUCTION MongoDB...")
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    try:
        await db.command("ping")
        print("✅ Connected\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)
    
    # Find user with avatar name "DOPE"
    user = await db.users.find_one({
        "avatar_name": {"$regex": "DOPE", "$options": "i"}
    })
    
    if not user:
        print("❌ Avatar 'DOPE' not found in database")
        print("\n💡 Searching for similar avatars...")
        users = await db.users.find({"avatar_name": {"$exists": True}}).to_list(100)
        for u in users:
            print(f"   • {u.get('name')} - Avatar: {u.get('avatar_name')}")
        client.close()
        sys.exit(1)
    
    user_id = user.get('id')
    print(f"✅ Avatar FOUND!")
    print(f"\n📋 Basic Info:")
    print(f"   User ID: {user_id}")
    print(f"   User Name: {user.get('name')}")
    print(f"   Email: {user.get('email')}")
    print(f"   Avatar Name: {user.get('avatar_name')}")
    
    # ============================================================================
    # 1. AVATAR CONFIGURATION CHECK
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"1️⃣  AVATAR CONFIGURATION")
    print(f"{'='*80}")
    
    avatar_name = user.get('avatar_name')
    is_autonomous = user.get('avatar_autonomous', False)
    activity_level = user.get('avatar_activity_level')
    
    print(f"\n   Avatar Name: {avatar_name or '❌ NOT SET'}")
    print(f"   Autonomous: {'✅ Enabled' if is_autonomous else '❌ Disabled'}")
    print(f"   Activity Level: {activity_level or '❌ NOT SET'}")
    
    # Actions enabled
    actions_enabled = user.get('avatar_actions_enabled', {})
    enabled_actions = [k for k, v in actions_enabled.items() if v]
    
    print(f"\n   📋 Enabled Actions ({len(enabled_actions)}):")
    if enabled_actions:
        for action in enabled_actions:
            print(f"      ✅ {action}")
    else:
        print(f"      ❌ No actions enabled")
    
    config_score = 0
    if avatar_name: config_score += 25
    if is_autonomous: config_score += 25
    if activity_level: config_score += 25
    if len(enabled_actions) >= 3: config_score += 25
    
    print(f"\n   Configuration Score: {config_score}%")
    
    # ============================================================================
    # 2. STATE-AWARE AGENT CHECK
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"2️⃣  STATE-AWARE AGENT")
    print(f"{'='*80}")
    
    # Current state
    current_state = user.get('avatar_current_state')
    print(f"\n   Current State: {current_state or '❌ NOT SET'}")
    
    # Internal state
    internal_state = user.get('avatar_internal_state', {})
    print(f"\n   🧠 Internal State:")
    if internal_state:
        print(f"      Energy: {internal_state.get('energy_level', 'N/A')}")
        print(f"      Social Desire: {internal_state.get('social_desire', 'N/A')}")
        print(f"      Creative Urge: {internal_state.get('creative_urge', 'N/A')}")
        print(f"      Mood: {internal_state.get('mood', 'N/A')}")
        last_updated = internal_state.get('last_updated')
        if last_updated:
            print(f"      Last Updated: {last_updated}")
    else:
        print(f"      ❌ NOT INITIALIZED")
    
    # External state
    external_state = user.get('avatar_external_state', {})
    print(f"\n   🌍 External State:")
    if external_state:
        print(f"      Friend Activity: {'✅' if 'recent_friend_activity' in external_state else '❌'}")
        print(f"      Unread Messages: {'✅' if 'unread_messages' in external_state else '❌'}")
    else:
        print(f"      ❌ NOT INITIALIZED")
    
    # Character profile
    character = user.get('avatar_character_profile', {})
    print(f"\n   👤 Character Profile:")
    if character:
        print(f"      Archetype: {character.get('archetype', 'N/A')}")
        traits = character.get('personality_traits', [])
        if traits:
            print(f"      Traits: {', '.join(traits[:5])}")
        interests = character.get('interests', [])
        if interests:
            print(f"      Interests: {', '.join(interests[:5])}")
    else:
        print(f"      ❌ NOT INITIALIZED")
    
    state_score = 0
    if current_state: state_score += 20
    if internal_state: state_score += 30
    if external_state: state_score += 20
    if character: state_score += 30
    
    print(f"\n   State-Aware Agent Score: {state_score}%")
    
    # ============================================================================
    # 3. MEMORY SYSTEM CHECK
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"3️⃣  MEMORY SYSTEM")
    print(f"{'='*80}")
    
    semantic_count = await db.semantic_memory.count_documents({"user_id": user_id})
    episodic_count = await db.episodic_memory.count_documents({"user_id": user_id})
    procedural_count = await db.procedural_memory.count_documents({"user_id": user_id})
    
    print(f"\n   Semantic Memories: {semantic_count}")
    print(f"   Episodic Memories: {episodic_count}")
    print(f"   Procedural Memories: {procedural_count}")
    
    total_memories = semantic_count + episodic_count + procedural_count
    memory_score = min(100, (total_memories / 10) * 100)  # 10 memories = 100%
    print(f"\n   Memory System Score: {memory_score:.0f}%")
    
    # ============================================================================
    # 4. EVENT CYCLE / AUTONOMOUS ACTIVITIES CHECK
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"4️⃣  EVENT CYCLE & AUTONOMOUS ACTIVITIES")
    print(f"{'='*80}")
    
    # Check recent activities
    recent_activities = await db.autonomous_activities.find({
        "bot_id": user_id
    }).sort([("timestamp", -1)]).limit(20).to_list(20)
    
    print(f"\n   Total Activities Recorded: {len(recent_activities)}")
    
    if recent_activities:
        # Latest activity
        latest = recent_activities[0]
        print(f"\n   🕐 Latest Activity:")
        print(f"      Action: {latest.get('action_type')}")
        print(f"      Timestamp: {latest.get('timestamp')}")
        print(f"      Success: {'✅' if latest.get('success') else '❌'}")
        
        # Check if activities are recent (within last 24 hours)
        now = datetime.now(timezone.utc)
        recent_24h = []
        for a in recent_activities:
            ts = a.get('timestamp')
            if ts:
                # Handle both datetime and string timestamps
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    except:
                        continue
                if (now - ts).total_seconds() < 86400:
                    recent_24h.append(a)
        
        print(f"\n   Activities in last 24h: {len(recent_24h)}")
        
        # Action diversity
        from collections import Counter
        action_types = [a.get('action_type') for a in recent_activities]
        action_counts = Counter(action_types)
        
        print(f"\n   🎲 Action Diversity:")
        for action, count in action_counts.most_common(5):
            print(f"      {action}: {count}")
        
        diversity = len(set(action_types)) / len(action_types)
        print(f"\n   Diversity Score: {diversity:.2%}")
        
        # Check if cycle is actively running
        if len(recent_24h) > 0:
            print(f"\n   ✅ Event cycle appears to be ACTIVE")
        else:
            print(f"\n   ⚠️  No recent activities - cycle may be INACTIVE")
    else:
        print(f"\n   ❌ NO ACTIVITIES RECORDED")
        print(f"   This means the autonomous agent has never run for this user")
    
    activity_score = 0
    if len(recent_activities) > 0: activity_score += 40
    if recent_activities and len(recent_24h) > 0: activity_score += 30
    if recent_activities and diversity > 0.3: activity_score += 30
    
    print(f"\n   Activity System Score: {activity_score}%")
    
    # ============================================================================
    # 5. POSTS & ENGAGEMENT CHECK
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"5️⃣  POSTS & ENGAGEMENT")
    print(f"{'='*80}")
    
    # Avatar posts
    avatar_posts = await db.posts.find({
        "user_id": user_id,
        "post_type": "avatar"
    }).sort([("created_at", -1)]).limit(5).to_list(5)
    
    print(f"\n   Avatar Posts Created: {len(avatar_posts)}")
    
    if avatar_posts:
        print(f"\n   📝 Recent Posts:")
        for i, post in enumerate(avatar_posts[:3], 1):
            text = post.get('text', '')[:60]
            created = post.get('created_at')
            likes = post.get('like_count', 0)
            comments = post.get('comment_count', 0)
            print(f"      {i}. {text}...")
            print(f"         Likes: {likes}, Comments: {comments}, Created: {created}")
    
    # Friends
    friends_count = await db.friendships.count_documents({
        "$or": [
            {"user_id": user_id, "status": "accepted"},
            {"friend_id": user_id, "status": "accepted"}
        ]
    })
    
    print(f"\n   Friends: {friends_count}")
    
    engagement_score = 0
    if len(avatar_posts) > 0: engagement_score += 50
    if friends_count > 0: engagement_score += 50
    
    print(f"\n   Engagement Score: {engagement_score}%")
    
    # ============================================================================
    # 6. OVERALL SYSTEM STATUS
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"📊 OVERALL SYSTEM STATUS")
    print(f"{'='*80}")
    
    overall_score = (config_score + state_score + memory_score + activity_score + engagement_score) / 5
    
    print(f"\n   Configuration: {config_score}%")
    print(f"   State-Aware Agent: {state_score}%")
    print(f"   Memory System: {memory_score:.0f}%")
    print(f"   Event Cycle/Activities: {activity_score}%")
    print(f"   Engagement: {engagement_score}%")
    print(f"\n   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   OVERALL SCORE: {overall_score:.1f}%")
    
    if overall_score >= 80:
        print(f"   Status: ✅ EXCELLENT - Fully operational and active")
    elif overall_score >= 60:
        print(f"   Status: ✅ GOOD - Mostly configured, some improvements needed")
    elif overall_score >= 40:
        print(f"   Status: ⚠️  FAIR - Partially configured, needs setup")
    else:
        print(f"   Status: ❌ POOR - Major configuration needed")
    
    # ============================================================================
    # 7. RECOMMENDATIONS
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"💡 RECOMMENDATIONS")
    print(f"{'='*80}\n")
    
    issues = []
    
    if not avatar_name:
        issues.append("Set avatar name in Edit Maya profile")
    if not is_autonomous:
        issues.append("Enable autonomy in Edit Maya profile")
    if not activity_level:
        issues.append("Set activity level (hypo/low/medium/high)")
    if len(enabled_actions) < 3:
        issues.append("Enable more actions for avatar")
    if not character:
        issues.append("Initialize character profile")
    if not internal_state:
        issues.append("Initialize internal state")
    if len(recent_activities) == 0:
        issues.append("Autonomous agent has never run - needs to be triggered")
    elif len(recent_24h) == 0:
        issues.append("No recent activities - autonomous agent may not be running")
    if len(avatar_posts) == 0:
        issues.append("Avatar hasn't created any posts yet")
    
    if issues:
        print(f"   🔧 Issues to address ({len(issues)}):")
        for issue in issues:
            print(f"      • {issue}")
    else:
        print(f"   ✅ No issues found! Avatar is fully operational.")
    
    print(f"\n   📚 Next Steps:")
    if overall_score < 60:
        print(f"      1. Complete avatar configuration in Edit Maya profile")
        print(f"      2. Run initialization script if needed")
        print(f"      3. Ensure autonomous agent EventBridge rule is active")
        print(f"      4. Monitor first few activities")
    else:
        print(f"      ✅ Avatar is well-configured!")
        print(f"      • Ensure EventBridge rule is running")
        print(f"      • Monitor activity patterns")
        print(f"      • Check engagement with other users")
    
    client.close()
    print(f"\n✅ Check Complete!")


if __name__ == "__main__":
    try:
        asyncio.run(check_avatar())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
