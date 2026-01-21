"""
State-Aware Agent Initialization Module

Automatically initializes all 8 layers of state-aware agent architecture
when a new user joins the platform.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any
import random

logger = logging.getLogger(__name__)


def get_initial_voice_modulators(archetype: str) -> Dict[str, float]:
    """Get initial voice modulators based on archetype"""
    voice_profiles = {
        'the_creator': {
            'humor_intensity': 0.6, 'sarcasm_level': 0.3, 'playfulness': 0.7,
            'formality': 0.3, 'emoji_frequency': 0.6, 'excitement_expression': 0.6,
            'thoughtfulness': 0.7, 'friendliness': 0.7, 'teasing_tendency': 0.3,
            'self_focused': 0.6, 'world_awareness': 0.5, 'friend_focus': 0.5
        },
        'the_sage': {
            'humor_intensity': 0.5, 'sarcasm_level': 0.5, 'playfulness': 0.3,
            'formality': 0.6, 'emoji_frequency': 0.3, 'excitement_expression': 0.3,
            'thoughtfulness': 0.9, 'friendliness': 0.6, 'teasing_tendency': 0.2,
            'self_focused': 0.4, 'world_awareness': 0.8, 'friend_focus': 0.4
        },
        'the_explorer': {
            'humor_intensity': 0.6, 'sarcasm_level': 0.3, 'playfulness': 0.6,
            'formality': 0.3, 'emoji_frequency': 0.6, 'excitement_expression': 0.7,
            'thoughtfulness': 0.5, 'friendliness': 0.7, 'teasing_tendency': 0.4,
            'self_focused': 0.5, 'world_awareness': 0.7, 'friend_focus': 0.5
        },
        'the_rebel': {
            'humor_intensity': 0.7, 'sarcasm_level': 0.8, 'playfulness': 0.6,
            'formality': 0.2, 'emoji_frequency': 0.5, 'excitement_expression': 0.6,
            'thoughtfulness': 0.5, 'friendliness': 0.6, 'teasing_tendency': 0.7,
            'self_focused': 0.6, 'world_awareness': 0.7, 'friend_focus': 0.5
        },
        'the_hero': {
            'humor_intensity': 0.5, 'sarcasm_level': 0.2, 'playfulness': 0.4,
            'formality': 0.5, 'emoji_frequency': 0.4, 'excitement_expression': 0.7,
            'thoughtfulness': 0.5, 'friendliness': 0.8, 'teasing_tendency': 0.3,
            'self_focused': 0.4, 'world_awareness': 0.6, 'friend_focus': 0.7
        },
        'the_magician': {
            'humor_intensity': 0.6, 'sarcasm_level': 0.4, 'playfulness': 0.6,
            'formality': 0.5, 'emoji_frequency': 0.5, 'excitement_expression': 0.5,
            'thoughtfulness': 0.7, 'friendliness': 0.6, 'teasing_tendency': 0.4,
            'self_focused': 0.6, 'world_awareness': 0.7, 'friend_focus': 0.4
        },
        'the_companion': {
            'humor_intensity': 0.6, 'sarcasm_level': 0.2, 'playfulness': 0.7,
            'formality': 0.3, 'emoji_frequency': 0.7, 'excitement_expression': 0.7,
            'thoughtfulness': 0.5, 'friendliness': 0.9, 'teasing_tendency': 0.5,
            'self_focused': 0.3, 'world_awareness': 0.4, 'friend_focus': 0.9
        },
        'the_jester': {
            'humor_intensity': 0.9, 'sarcasm_level': 0.6, 'playfulness': 0.9,
            'formality': 0.2, 'emoji_frequency': 0.8, 'excitement_expression': 0.8,
            'thoughtfulness': 0.4, 'friendliness': 0.8, 'teasing_tendency': 0.8,
            'self_focused': 0.4, 'world_awareness': 0.5, 'friend_focus': 0.7
        }
    }
    
    return voice_profiles.get(archetype, voice_profiles['the_companion'])


async def initialize_state_aware_agent(db, user_id: str, user_name: str = None, user_email: str = None) -> bool:
    """
    Initialize all 8 layers of state-aware agent architecture for a new user
    
    Layers:
    1. State Machine - Set initial top-level state
    2. Internal State - Initialize psychological model
    3. External State - Set up environmental perception tracking
    4. Character Profile - Create personality and interests
    5. Decision Engine - Enable autonomous actions
    6. Memory System - Initialize memory collections
    7. Activity Diversity - Set up diversity config
    8. Activity Levels - Set initial activity frequency
    
    Args:
        db: MongoDB database instance
        user_id: User's unique ID
        user_name: User's name (optional, for logging)
        user_email: User's email (optional, for logging)
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    
    try:
        logger.info(f"🤖 Initializing state-aware agent for user: {user_name or user_id}")
        
        # Get existing user data
        user = await db.users.find_one({"id": user_id})
        if not user:
            logger.error(f"User {user_id} not found")
            return False
        
        # Prepare update document
        update_doc = {}
        
        # ====================================================================
        # LAYER 1: State Machine - Set initial state
        # ====================================================================
        update_doc['avatar_current_state'] = 'ACTIVE'
        update_doc['avatar_state_history'] = [{
            'state': 'ACTIVE',
            'entered_at': datetime.now(timezone.utc).isoformat(),
            'reason': 'Initial setup'
        }]
        
        # ====================================================================
        # LAYER 2: Internal State - Initialize psychological model
        # ====================================================================
        # Will set archetype soon, use default for now
        temp_archetype = 'the_companion'  # Default, will be overridden
        
        update_doc['avatar_internal_state'] = {
            'energy_level': 0.8,  # Start with high energy
            'social_desire': 0.7,  # Moderate social desire
            'creative_urge': 0.6,  # Some creative drive
            'mood': 'curious',  # Start with curiosity
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'last_activity': None,
            'cycles_since_rest': 0
        }
        
        # ====================================================================
        # LAYER 3: External State - Environmental perception
        # ====================================================================
        update_doc['avatar_external_state'] = {
            'recent_friend_activity': [],
            'recent_posts_seen': [],
            'unread_messages': 0,
            'relationship_map': {},
            'trending_topics': [],
            'last_checked': datetime.now(timezone.utc).isoformat()
        }
        
        # ====================================================================
        # LAYER 4: Character Profile - Personality
        # ====================================================================
        # Assign a random archetype
        archetypes = [
            'the_creator',  # Artistic, innovative
            'the_sage',  # Wise, knowledge-seeking
            'the_explorer',  # Adventurous, curious
            'the_rebel',  # Bold, rule-breaking
            'the_hero',  # Courageous, action-oriented
            'the_magician',  # Transformative, visionary
            'the_companion',  # Friendly, supportive
            'the_jester',  # Playful, entertaining
        ]
        
        # Generate personality traits based on archetype
        trait_sets = {
            'the_creator': ['innovative', 'artistic', 'expressive', 'imaginative'],
            'the_sage': ['thoughtful', 'analytical', 'knowledgeable', 'wise'],
            'the_explorer': ['curious', 'adventurous', 'open-minded', 'spontaneous'],
            'the_rebel': ['bold', 'independent', 'challenging', 'passionate'],
            'the_hero': ['courageous', 'determined', 'loyal', 'protective'],
            'the_magician': ['visionary', 'transformative', 'mysterious', 'charismatic'],
            'the_companion': ['friendly', 'empathetic', 'supportive', 'reliable'],
            'the_jester': ['playful', 'witty', 'entertaining', 'optimistic']
        }
        
        # Generate initial interests
        interest_categories = [
            ['technology', 'AI', 'coding', 'startups'],
            ['art', 'music', 'design', 'creativity'],
            ['science', 'philosophy', 'psychology', 'learning'],
            ['travel', 'culture', 'adventure', 'exploration'],
            ['fitness', 'wellness', 'mindfulness', 'nature'],
            ['gaming', 'esports', 'entertainment', 'pop culture'],
            ['business', 'entrepreneurship', 'innovation', 'leadership'],
            ['writing', 'literature', 'storytelling', 'poetry']
        ]
        
        archetype = random.choice(archetypes)
        traits = trait_sets[archetype]
        interests = random.sample([item for sublist in interest_categories for item in sublist], 6)
        
        update_doc['avatar_character_profile'] = {
            'archetype': archetype,
            'personality_traits': traits,
            'interests': interests,
            'communication_style': 'friendly' if archetype in ['the_companion', 'the_jester'] else 'thoughtful',
            'action_preferences': {
                'create_posts': 0.7 if archetype == 'the_creator' else 0.5,
                'like_post': 0.8,
                'comment_on_post': 0.6 if archetype in ['the_sage', 'the_companion'] else 0.4,
                'message_friend': 0.5 if archetype == 'the_companion' else 0.3,
                'discover_profiles': 0.8 if archetype == 'the_explorer' else 0.4
            },
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # NEW: Add voice modulators to internal state based on archetype
        voice_modulators = get_initial_voice_modulators(archetype)
        update_doc['avatar_internal_state']['voice_modulators'] = voice_modulators
        
        logger.info(f"   ✓ Voice modulators initialized for archetype: {archetype}")
        
        # ====================================================================
        # LAYER 5: Decision Engine - Enable autonomous behavior
        # ====================================================================
        update_doc['avatar_autonomous'] = True
        update_doc['avatar_activity_level'] = 'medium'  # Start with medium activity
        
        # Enable ALL actions by default (user can disable via Edit Maya Profile)
        # Use BOTH formats for compatibility
        update_doc['avatar_enabled_actions'] = [
            'create_posts',
            'like_posts',  # Fixed: was 'like_post' 
            'comment_posts',  # Fixed: was 'comment_on_post'
            'message_friends',  # Fixed: was 'message_friend'
            'discover_profiles',
            'profile_viewed',
            'read_messages',
            'send_friend_requests',
            'accept_friend_requests',
            'browse_feed',  # NEW: Browse feed tool
            'get_friend_activities',  # NEW: State-aware friend tracking
            'get_trending_topics'  # NEW: State-aware news/world awareness
        ]
        
        # CORRECT FORMAT: Object with boolean values (this is what the system actually reads)
        update_doc['avatar_actions_enabled'] = {
            'create_posts': True,
            'like_posts': True,
            'comment_posts': True,
            'message_friends': True,
            'discover_profiles': True,
            'profile_viewed': True,
            'read_messages': True,
            'send_friend_requests': True,
            'accept_friend_requests': True,
            'browse_feed': True,  # NEW: Browse feed
            'get_friend_activities': True,  # NEW: State-aware
            'get_trending_topics': True,  # NEW: State-aware
            'share_posts': False  # NEW: Not implemented yet
        }
        
        # Also set top-level archetype and interests for compatibility
        update_doc['avatar_archetype'] = archetype
        update_doc['avatar_interests'] = interests
        
        # ====================================================================
        # LAYER 6: Memory System - Initialize configs
        # ====================================================================
        update_doc['avatar_memory_config'] = {
            'semantic_memory_enabled': True,
            'episodic_memory_enabled': True,
            'procedural_memory_enabled': True,
            'max_semantic_memories': 1000,
            'max_episodic_memories': 500,
            'memory_consolidation_interval': 86400,  # 24 hours
            'last_consolidation': datetime.now(timezone.utc).isoformat()
        }
        
        # ====================================================================
        # LAYER 7: Activity Diversity - Prevent repetition
        # ====================================================================
        update_doc['avatar_diversity_config'] = {
            'enabled': True,
            'min_action_interval': 300,  # 5 minutes between same action
            'max_repetitions': 3,  # Max 3 times same action in window
            'diversity_window': 3600,  # 1 hour window
            'action_cooldowns': {}
        }
        
        # ====================================================================
        # LAYER 8: Activity Levels - Already set in Layer 5
        # ====================================================================
        # (Covered by avatar_activity_level above)
        
        # Update user document
        result = await db.users.update_one(
            {"id": user_id},
            {"$set": update_doc}
        )
        
        if result.modified_count > 0 or result.matched_count > 0:
            logger.info(f"✅ State-aware agent initialized successfully for {user_name or user_id}")
            logger.info(f"   Archetype: {archetype}")
            logger.info(f"   Initial State: ACTIVE")
            logger.info(f"   Autonomy: ENABLED")
            return True
        else:
            logger.warning(f"⚠️  No changes made for user {user_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error initializing state-aware agent for {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def initialize_existing_users(db, user_ids: list = None):
    """
    Initialize state-aware agents for existing users who don't have it
    
    Args:
        db: MongoDB database instance
        user_ids: Optional list of specific user IDs to initialize.
                 If None, initializes all users missing state-aware components.
    
    Returns:
        dict: Summary of initialization results
    """
    try:
        logger.info("🔄 Initializing state-aware agents for existing users...")
        
        # Find users missing state-aware components
        query = {
            "$or": [
                {"avatar_current_state": {"$exists": False}},
                {"avatar_internal_state": {"$exists": False}},
                {"avatar_character_profile": {"$exists": False}}
            ]
        }
        
        if user_ids:
            query["id"] = {"$in": user_ids}
        
        users = await db.users.find(query).to_list(1000)
        
        logger.info(f"Found {len(users)} users needing initialization")
        
        results = {
            'total': len(users),
            'success': 0,
            'failed': 0,
            'users': []
        }
        
        for user in users:
            user_id = user.get('id')
            user_name = user.get('name', 'Unknown')
            user_email = user.get('email')
            
            success = await initialize_state_aware_agent(db, user_id, user_name, user_email)
            
            if success:
                results['success'] += 1
                results['users'].append({
                    'id': user_id,
                    'name': user_name,
                    'status': 'success'
                })
            else:
                results['failed'] += 1
                results['users'].append({
                    'id': user_id,
                    'name': user_name,
                    'status': 'failed'
                })
        
        logger.info(f"✅ Initialization complete: {results['success']} successful, {results['failed']} failed")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in batch initialization: {e}")
        import traceback
        traceback.print_exc()
        return None
