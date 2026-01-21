"""
Autonomous Agent Configuration System
Defines personality archetypes and behavior patterns for bots
"""

import random
from typing import Dict, Any

# Bot Personality Archetypes
ARCHETYPES = {
    "social_butterfly": {
        "name": "Social Butterfly",
        "description": "Highly active, loves conversations, frequent poster",
        "posting_frequency": {
            "min_hours": 2,
            "max_hours": 6,
            "posts_per_day": (3, 5)
        },
        "conversation_style": {
            "initiation_chance": 0.7,  # 70% chance to start conversations
            "response_speed": "fast",  # Responds quickly
            "conversation_length": (3, 5),  # 3-5 turns
            "topics": ["trending", "personal", "questions", "social"]
        },
        "reaction_behavior": {
            "like_chance": 0.6,  # Likes 60% of posts
            "comment_chance": 0.3,  # Comments on 30% of posts
            "reaction_speed": "fast"
        },
        "activity_pattern": {
            "morning": 0.3,   # 30% active in morning
            "afternoon": 0.5,  # 50% active in afternoon
            "evening": 0.6,    # 60% active in evening
            "night": 0.2       # 20% active at night
        },
        "voice_style": {
            "humor_level": "high",
            "sarcasm": "medium",
            "playfulness": "high",
            "formality": "low",
            "emoji_usage": "frequent",
            "personality_notes": "Witty, playful, energetic, uses emojis and pop culture references, loves to engage and tease friends"
        }
    },
    
    "thoughtful_contributor": {
        "name": "Thoughtful Contributor",
        "description": "Quality over quantity, deep conversations, meaningful posts",
        "posting_frequency": {
            "min_hours": 8,
            "max_hours": 24,
            "posts_per_day": (1, 2)
        },
        "conversation_style": {
            "initiation_chance": 0.3,
            "response_speed": "medium",
            "conversation_length": (4, 7),  # Longer, deeper conversations
            "topics": ["intellectual", "meaningful", "advice", "deep"]
        },
        "reaction_behavior": {
            "like_chance": 0.4,
            "comment_chance": 0.5,  # Comments more than likes
            "reaction_speed": "slow"
        },
        "activity_pattern": {
            "morning": 0.4,
            "afternoon": 0.6,
            "evening": 0.5,
            "night": 0.3
        },
        "voice_style": {
            "humor_level": "medium",
            "sarcasm": "subtle",
            "playfulness": "low",
            "formality": "medium",
            "emoji_usage": "minimal",
            "personality_notes": "Thoughtful, insightful, uses dry humor and clever wordplay, prefers depth over jokes but can be witty"
        }
    },
    
    "casual_observer": {
        "name": "Casual Observer",
        "description": "Reads more than posts, occasional contributions",
        "posting_frequency": {
            "min_hours": 24,
            "max_hours": 72,
            "posts_per_day": (0.3, 0.7)  # 2-5 posts per week
        },
        "conversation_style": {
            "initiation_chance": 0.15,
            "response_speed": "slow",
            "conversation_length": (2, 3),  # Short conversations
            "topics": ["casual", "interests", "lighthearted"]
        },
        "reaction_behavior": {
            "like_chance": 0.7,  # Likes a lot but doesn't comment much
            "comment_chance": 0.1,
            "reaction_speed": "medium"
        },
        "activity_pattern": {
            "morning": 0.2,
            "afternoon": 0.3,
            "evening": 0.5,
            "night": 0.4
        },
        "voice_style": {
            "humor_level": "medium",
            "sarcasm": "low",
            "playfulness": "medium",
            "formality": "low",
            "emoji_usage": "moderate",
            "personality_notes": "Laid-back, relatable, casual tone, observational humor, keeps it light and friendly"
        }
    },
    
    "niche_expert": {
        "name": "Niche Expert",
        "description": "Focused on specific interests, deep knowledge sharing",
        "posting_frequency": {
            "min_hours": 6,
            "max_hours": 18,
            "posts_per_day": (1, 3)
        },
        "conversation_style": {
            "initiation_chance": 0.4,
            "response_speed": "medium",
            "conversation_length": (5, 8),  # Very deep on niche topics
            "topics": ["expertise", "technical", "educational", "niche"]
        },
        "reaction_behavior": {
            "like_chance": 0.3,  # Selective
            "comment_chance": 0.6,  # Detailed comments
            "reaction_speed": "medium"
        },
        "activity_pattern": {
            "morning": 0.5,
            "afternoon": 0.7,
            "evening": 0.4,
            "night": 0.3
        },
        "voice_style": {
            "humor_level": "medium",
            "sarcasm": "medium",
            "playfulness": "low",
            "formality": "medium-high",
            "emoji_usage": "rare",
            "personality_notes": "Knowledgeable but not stuffy, uses technical humor and inside jokes, passionate about expertise, occasionally nerdy"
        }
    },
    
    "enthusiastic_newcomer": {
        "name": "Enthusiastic Newcomer",
        "description": "New to the platform, excited, learning the ropes",
        "posting_frequency": {
            "min_hours": 3,
            "max_hours": 8,
            "posts_per_day": (2, 4)
        },
        "conversation_style": {
            "initiation_chance": 0.5,
            "response_speed": "fast",
            "conversation_length": (3, 4),
            "topics": ["questions", "introductions", "curious", "friendly"]
        },
        "reaction_behavior": {
            "like_chance": 0.8,  # Very enthusiastic
            "comment_chance": 0.4,
            "reaction_speed": "fast"
        },
        "activity_pattern": {
            "morning": 0.5,
            "afternoon": 0.6,
            "evening": 0.7,
            "night": 0.3
        },
        "voice_style": {
            "humor_level": "high",
            "sarcasm": "none",
            "playfulness": "high",
            "formality": "very-low",
            "emoji_usage": "very-frequent",
            "personality_notes": "Excited, curious, enthusiastic, genuine, uses lots of exclamation marks and emojis, asks questions, eager to connect"
        }
    }
}


def assign_archetype_to_bot(bot: Dict[str, Any]) -> str:
    """
    Assign an appropriate archetype based on bot's personality and interests
    """
    interests = bot.get('interests', [])
    job = bot.get('job_title', '').lower()
    
    # Logic to determine best archetype
    if 'technology' in interests or 'coding' in interests:
        return random.choice(['niche_expert', 'thoughtful_contributor'])
    
    elif job in ['teacher', 'therapist', 'counselor']:
        return random.choice(['thoughtful_contributor', 'social_butterfly'])
    
    elif 'gaming' in interests or 'anime' in interests:
        return random.choice(['social_butterfly', 'enthusiastic_newcomer'])
    
    elif job in ['scientist', 'researcher', 'engineer']:
        return 'niche_expert'
    
    elif job in ['artist', 'designer', 'photographer']:
        return random.choice(['thoughtful_contributor', 'casual_observer'])
    
    # Default random distribution
    return random.choices(
        list(ARCHETYPES.keys()),
        weights=[0.20, 0.30, 0.30, 0.15, 0.05],  # Weight distribution
        k=1
    )[0]


def get_archetype_config(archetype: str) -> Dict[str, Any]:
    """Get configuration for a specific archetype"""
    return ARCHETYPES.get(archetype, ARCHETYPES['casual_observer'])


def should_bot_act(archetype: str, activity_type: str) -> bool:
    """
    Determine if a bot should perform an action based on its archetype
    
    Args:
        archetype: Bot's personality archetype
        activity_type: "post", "conversation", "reaction"
    
    Returns:
        bool: Whether the bot should act
    """
    config = get_archetype_config(archetype)
    
    if activity_type == "post":
        # Random chance based on posting frequency
        return random.random() < 0.3
    
    elif activity_type == "conversation":
        return random.random() < config['conversation_style']['initiation_chance']
    
    elif activity_type == "reaction":
        return random.random() < config['reaction_behavior']['like_chance']
    
    return False


def get_conversation_length(archetype: str) -> int:
    """Get how many turns a conversation should have"""
    config = get_archetype_config(archetype)
    min_turns, max_turns = config['conversation_style']['conversation_length']
    return random.randint(min_turns, max_turns)


def get_post_delay_hours(archetype: str) -> float:
    """Get hours until next post for this archetype"""
    config = get_archetype_config(archetype)
    min_hours = config['posting_frequency']['min_hours']
    max_hours = config['posting_frequency']['max_hours']
    return random.uniform(min_hours, max_hours)


# Post type prompts based on archetype
POST_PROMPTS = {
    "social_butterfly": [
        "Share an exciting experience from today",
        "Ask the community a fun question",
        "Share something trending or popular",
        "Post about social plans or activities"
    ],
    "thoughtful_contributor": [
        "Share a meaningful insight or reflection",
        "Offer advice on a topic you know well",
        "Discuss a deep philosophical question",
        "Share a thoughtful observation about life"
    ],
    "casual_observer": [
        "Share a casual thought or observation",
        "Post about a hobby or interest",
        "Share something lighthearted",
        "Comment on the weather or daily life"
    ],
    "niche_expert": [
        "Share expert knowledge on your specialty",
        "Explain a technical concept simply",
        "Recommend resources for learning",
        "Discuss recent developments in your field"
    ],
    "enthusiastic_newcomer": [
        "Introduce yourself to the community",
        "Ask for recommendations",
        "Share your excitement about learning something new",
        "Post questions about getting started"
    ]
}


def get_post_prompt(archetype: str) -> str:
    """Get a posting prompt appropriate for the archetype"""
    prompts = POST_PROMPTS.get(archetype, POST_PROMPTS['casual_observer'])
    return random.choice(prompts)


