#!/usr/bin/env python3
"""
Verify State-Aware Agent Architecture for B11, Seven, _bLikker
Checks all 8 layers: State Machine, Internal State, External State, Character Profile,
Decision Engine, Memory System, Activity Diversity, Activity Levels
"""
import asyncio
import os
import sys
import json
import boto3
from datetime import datetime, timezone

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


def check_status(condition, label):
    """Print status with emoji"""
    if condition:
        print(f"      ✅ {label}")
        return True
    else:
        print(f"      ❌ {label}")
        return False


async def verify_agent_layers(db, user, user_name, avatar_name):
    """Verify all 8 layers of state-aware agent architecture"""
    
    print(f"\n{'='*70}")
    print(f"🤖 State-Aware Agent Verification: {user_name} ({avatar_name})")
    print(f"{'='*70}")
    
    user_id = user.get('id')
    issues = []
    layer_scores = {}
    
    # ========================================================================
    # LAYER 1: State Machine (Top-level states)
    # ========================================================================
    print(f"\n📊 Layer 1: State Machine")
    current_state = user.get('avatar_current_state')
    valid_states = ['ACTIVE', 'SOCIAL', 'CREATIVE', 'EXPLORING', 'PASSIVE', 'RESTING']
    
    has_state = check_status(current_state is not None, "Has current state")
    valid_state = check_status(current_state in valid_states if current_state else False, 
                                f"Valid state: {current_state}")
    
    if not has_state:
        issues.append("Missing avatar_current_state")
    if current_state and not valid_state:
        issues.append(f"Invalid state: {current_state}")
    
    layer_scores['state_machine'] = int(has_state and valid_state)
    
    # ========================================================================
    # LAYER 2: Internal State (Psychological model)
    # ========================================================================
    print(f"\n🧠 Layer 2: Internal State")
    internal_state = user.get('avatar_internal_state', {})
    
    has_energy = check_status('energy_level' in internal_state, "Energy level")
    has_social = check_status('social_desire' in internal_state, "Social desire")
    has_creative = check_status('creative_urge' in internal_state, "Creative urge")
    has_mood = check_status('mood' in internal_state, "Mood")
    has_last_update = check_status('last_updated' in internal_state, "Last updated timestamp")
    
    if not internal_state:
        issues.append("Missing avatar_internal_state")
    else:
        missing = []
        for field in ['energy_level', 'social_desire', 'creative_urge', 'mood', 'last_updated']:
            if field not in internal_state:
                missing.append(field)
        if missing:
            issues.append(f"Internal state missing: {', '.join(missing)}")
    
    layer_scores['internal_state'] = sum([has_energy, has_social, has_creative, has_mood, has_last_update]) / 5
    
    # ========================================================================
    # LAYER 3: External State (Environmental perception)
    # ========================================================================
    print(f"\n🌍 Layer 3: External State")
    external_state = user.get('avatar_external_state', {})
    
    # Check friend activity
    friends_count = await db.friendships.count_documents({
        "$or": [
            {"user_id": user_id, "status": "accepted"},
            {"friend_id": user_id, "status": "accepted"}
        ]
    })
    has_friends = check_status(friends_count > 0, f"Has friends: {friends_count}")
    
    # Check recent posts in feed
    posts_count = await db.posts.count_documents({})
    has_posts = check_status(posts_count > 0, f"Posts available: {posts_count}")
    
    # Check external state tracking
    has_friend_activity = check_status('recent_friend_activity' in external_state, 
                                       "Tracks friend activity")
    has_unread_msgs = check_status('unread_messages' in external_state, 
                                    "Tracks unread messages")
    
    if not external_state:
        issues.append("Missing avatar_external_state")
    
    layer_scores['external_state'] = sum([has_friends, has_posts, has_friend_activity, has_unread_msgs]) / 4
    
    # ========================================================================
    # LAYER 4: Character Profile (Personality)
    # ========================================================================
    print(f"\n👤 Layer 4: Character Profile")
    character = user.get('avatar_character_profile', {})
    
    has_archetype = check_status('archetype' in character, f"Archetype: {character.get('archetype', 'N/A')}")
    has_traits = check_status(len(character.get('personality_traits', [])) > 0, 
                              f"Traits: {len(character.get('personality_traits', []))}")
    has_interests = check_status(len(character.get('interests', [])) > 0, 
                                 f"Interests: {len(character.get('interests', []))}")
    has_action_prefs = check_status('action_preferences' in character, "Action preferences")
    
    if not character:
        issues.append("Missing avatar_character_profile")
    else:
        if 'archetype' not in character:
            issues.append("No archetype set")
        if not character.get('personality_traits'):
            issues.append("No personality traits")
        if not character.get('interests'):
            issues.append("No interests")
    
    layer_scores['character_profile'] = sum([has_archetype, has_traits, has_interests, has_action_prefs]) / 4
    
    # ========================================================================
    # LAYER 5: Decision Engine (Action selection config)
    # ========================================================================
    print(f"\n🎯 Layer 5: Decision Engine")
    
    # Check if actions are enabled
    actions_enabled = user.get('avatar_actions_enabled', {})
    enabled_count = sum(1 for v in actions_enabled.values() if v)
    has_actions = check_status(enabled_count > 0, f"Actions enabled: {enabled_count}")
    
    # Check action preferences (part of character profile)
    has_prefs = check_status('action_preferences' in character, "Has action preferences")
    
    # Check if autonomous
    is_autonomous = check_status(user.get('avatar_autonomous', False), "Autonomous enabled")
    
    # Check activity level
    activity_level = user.get('avatar_activity_level')
    has_activity = check_status(activity_level is not None, f"Activity level: {activity_level}")
    
    if not user.get('avatar_autonomous'):
        issues.append("Autonomy not enabled")
    if enabled_count == 0:
        issues.append("No actions enabled")
    
    layer_scores['decision_engine'] = sum([has_actions, has_prefs, is_autonomous, has_activity]) / 4
    
    # ========================================================================
    # LAYER 6: Memory System (Learning and adaptation)
    # ========================================================================
    print(f"\n💭 Layer 6: Memory System")
    
    # Check for memories collection
    semantic_memories = await db.semantic_memory.count_documents({"user_id": user_id})
    episodic_memories = await db.episodic_memory.count_documents({"user_id": user_id})
    procedural_memories = await db.procedural_memory.count_documents({"user_id": user_id})
    
    has_semantic = check_status(semantic_memories > 0, f"Semantic memories: {semantic_memories}")
    has_episodic = check_status(episodic_memories > 0, f"Episodic memories: {episodic_memories}")
    has_procedural = check_status(procedural_memories > 0, f"Procedural memories: {procedural_memories}")
    
    # Check memory configuration
    memory_config = user.get('avatar_memory_config', {})
    has_config = check_status(len(memory_config) > 0, "Memory config exists")
    
    if semantic_memories == 0 and episodic_memories == 0 and procedural_memories == 0:
        issues.append("No memories stored")
    
    layer_scores['memory_system'] = sum([has_semantic, has_episodic, has_procedural, has_config]) / 4
    
    # ========================================================================
    # LAYER 7: Activity Diversity System (Prevents repetition)
    # ========================================================================
    print(f"\n🎲 Layer 7: Activity Diversity System")
    
    # Check recent activities for diversity
    recent_activities = await db.autonomous_activities.find({
        "bot_id": user_id
    }).sort([("timestamp", -1)]).limit(20).to_list(20)
    
    has_activities = check_status(len(recent_activities) > 0, f"Recent activities: {len(recent_activities)}")
    
    if recent_activities:
        action_types = [a.get('action_type') for a in recent_activities]
        unique_actions = len(set(action_types))
        diversity_score = unique_actions / len(action_types) if action_types else 0
        is_diverse = check_status(diversity_score > 0.3, f"Diversity score: {diversity_score:.2f}")
        
        # Show action distribution
        from collections import Counter
        action_counts = Counter(action_types)
        print(f"\n      Action distribution:")
        for action, count in action_counts.most_common(5):
            print(f"         {action}: {count}")
    else:
        is_diverse = False
        diversity_score = 0
        print(f"      ⚠️  No activities to analyze")
    
    # Check diversity config
    diversity_config = user.get('avatar_diversity_config', {})
    has_diversity_config = check_status(len(diversity_config) > 0, "Diversity config exists")
    
    if len(recent_activities) == 0:
        issues.append("No activities recorded (agent may not be running)")
    
    layer_scores['activity_diversity'] = (int(has_activities) + int(is_diverse) + int(has_diversity_config)) / 3
    
    # ========================================================================
    # LAYER 8: Activity Levels (Frequency control)
    # ========================================================================
    print(f"\n⚡ Layer 8: Activity Levels")
    
    activity_level = user.get('avatar_activity_level')
    valid_levels = ['hypo', 'low', 'medium', 'high']
    
    has_level = check_status(activity_level is not None, f"Activity level set: {activity_level}")
    valid_level = check_status(activity_level in valid_levels if activity_level else False, 
                               "Valid level")
    
    # Check if autonomous agent respects level
    if recent_activities:
        # Check activity frequency
        timestamps = [a.get('timestamp') for a in recent_activities if a.get('timestamp')]
        if len(timestamps) >= 2:
            # Simple frequency check
            print(f"      ℹ️  Recent activity pattern detected")
    
    if not activity_level:
        issues.append("No activity level set")
    
    layer_scores['activity_levels'] = int(has_level and valid_level)
    
    # ========================================================================
    # OVERALL SCORE
    # ========================================================================
    print(f"\n{'='*70}")
    print(f"📈 OVERALL STATE-AWARE AGENT SCORE")
    print(f"{'='*70}")
    
    overall_score = sum(layer_scores.values()) / len(layer_scores) * 100
    
    print(f"\n   Overall: {overall_score:.1f}%")
    print(f"\n   Layer Breakdown:")
    for layer, score in layer_scores.items():
        bar_length = int(score * 20)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        print(f"      {layer:20s} {bar} {score*100:5.1f}%")
    
    print(f"\n   Status: ", end="")
    if overall_score >= 80:
        print("✅ EXCELLENT - Fully operational")
    elif overall_score >= 60:
        print("⚠️  GOOD - Minor improvements needed")
    elif overall_score >= 40:
        print("⚠️  FAIR - Several components missing")
    else:
        print("❌ POOR - Major configuration needed")
    
    if issues:
        print(f"\n   🔧 Issues to fix ({len(issues)}):")
        for issue in issues:
            print(f"      • {issue}")
    
    return overall_score, issues


async def main():
    """Verify state-aware agents for all three avatars"""
    
    print("=" * 70)
    print("║     🤖 STATE-AWARE AGENT VERIFICATION                              ║")
    print("║     B11, Seven, _bLikker                                           ║")
    print("=" * 70)
    
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
    
    # Check all three avatars
    target_users = [
        ("Sreejith Sreekantan", "_bLikker"),
        ("Badusha", "B11"),
        ("Rafseena Sedeed", "Seven")
    ]
    
    all_scores = []
    all_issues = []
    
    for user_name, avatar_name in target_users:
        # Find user
        user = await db.users.find_one({
            "name": {"$regex": user_name, "$options": "i"}
        })
        
        if not user:
            print(f"\n❌ User '{user_name}' not found")
            continue
        
        score, issues = await verify_agent_layers(db, user, user_name, avatar_name)
        all_scores.append((avatar_name, score))
        all_issues.extend([(avatar_name, issue) for issue in issues])
    
    # Final Summary
    print(f"\n\n{'='*70}")
    print(f"📊 FINAL SUMMARY - All Agents")
    print(f"{'='*70}\n")
    
    if all_scores:
        avg_score = sum(s for _, s in all_scores) / len(all_scores)
        print(f"Average Score: {avg_score:.1f}%\n")
        
        print("Individual Scores:")
        for avatar, score in all_scores:
            status = "✅" if score >= 70 else "⚠️" if score >= 50 else "❌"
            print(f"   {status} {avatar:12s}: {score:.1f}%")
    
    if all_issues:
        print(f"\n\n🔧 ALL ISSUES FOUND ({len(all_issues)}):")
        for avatar, issue in all_issues:
            print(f"   {avatar}: {issue}")
    
    print(f"\n💡 Next Steps:")
    if avg_score < 70:
        print("   1. Initialize missing state-aware components")
        print("   2. Set character profiles for all avatars")
        print("   3. Enable all actions")
        print("   4. Start autonomous agent system")
    else:
        print("   ✅ Agents are well-configured!")
        print("   • Ensure autonomous agent is running")
        print("   • Monitor activity patterns")
    
    client.close()
    print("\n✅ Verification Complete!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
