import asyncio
import random
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Realistic Western names for Real World
real_first_names = [
    'Emma', 'Liam', 'Olivia', 'Noah', 'Ava', 'Ethan', 'Sophia', 'Mason', 'Isabella', 'Lucas',
    'Mia', 'James', 'Charlotte', 'Benjamin', 'Amelia', 'Alexander', 'Harper', 'Michael', 'Evelyn', 'Daniel',
    'Abigail', 'Matthew', 'Emily', 'Jackson', 'Elizabeth', 'Sebastian', 'Sofia', 'Jack', 'Avery', 'Aiden',
    'Ella', 'Samuel', 'Scarlett', 'David', 'Grace', 'Joseph', 'Chloe', 'Carter', 'Victoria', 'Owen',
    'Riley', 'Wyatt', 'Aria', 'John', 'Lily', 'Dylan', 'Aubrey', 'Luke', 'Zoey', 'Gabriel'
]

real_last_names = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
    'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
    'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson'
]

# Anime-style names for Avatar World
anime_first_names = [
    'Sakura', 'Yuki', 'Hana', 'Kaito', 'Ryu', 'Akira', 'Haruki', 'Sora', 'Mei', 'Ren',
    'Aiko', 'Daiki', 'Emi', 'Hinata', 'Ichigo', 'Jun', 'Kira', 'Luna', 'Miku', 'Nao',
    'Rei', 'Shinji', 'Taro', 'Yui', 'Zen', 'Asuna', 'Kirito', 'Mikasa', 'Eren', 'Levi',
    'Naruto', 'Sasuke', 'Goku', 'Vegeta', 'Luffy', 'Zoro', 'Ichigo', 'Rukia', 'Edward', 'Alphonse',
    'Light', 'L', 'Spike', 'Faye', 'Inuyasha', 'Kagome', 'Sailor', 'Tuxedo', 'Ash', 'Misty'
]

interests = [
    'anime', 'manga', 'cosplay', 'gaming', 'art', 'music', 'cooking', 'travel',
    'photography', 'fitness', 'reading', 'movies', 'technology', 'fashion', 'dance',
    'singing', 'drawing', 'writing', 'sports', 'yoga', 'meditation', 'coding'
]

jobs = [
    'Graphic Designer', 'Software Engineer', 'Artist', 'Content Creator', 'Streamer',
    'Photographer', 'Writer', 'Musician', 'Teacher', 'Chef', 'Student',
    'Game Developer', 'Animator', 'Voice Actor', 'Cosplayer', 'Influencer'
]

cities = [
    'Tokyo, Japan', 'Osaka, Japan', 'Kyoto, Japan', 'Seoul, South Korea',
    'San Francisco, CA', 'New York, NY', 'Los Angeles, CA', 'Seattle, WA',
    'London, UK', 'Paris, France', 'Berlin, Germany', 'Toronto, Canada'
]

posts_templates = [
    "Just finished watching the latest episode of {anime}! Who else is watching? 😍",
    "Working on some new artwork today! {interest} has been so much fun lately 🎨",
    "Can't believe it's already {day}! Time flies when you're having fun ⏰",
    "Does anyone else love {interest}? Looking for recommendations! 💭",
    "Had an amazing day at the {event}! Met so many cool people 🎉",
    "Just got back from {city}! The food was incredible 🍜",
    "Streaming {game} tonight at 8PM! Come hang out! 🎮",
    "New cosplay project in the works... can you guess who? 👀",
    "Coffee and {interest} - the perfect combination ☕",
    "Life update: Started learning {skill}! Wish me luck! 📚"
]

animes = ['One Piece', 'Naruto', 'Attack on Titan', 'Demon Slayer', 'My Hero Academia', 'Jujutsu Kaisen']
events = ['anime convention', 'cosplay meetup', 'art gallery', 'gaming tournament', 'concert']
games = ['Valorant', 'Genshin Impact', 'League of Legends', 'Overwatch', 'Minecraft']
skills = ['Japanese', 'digital art', 'guitar', 'photography', 'cooking']

conversation_starters = [
    "Hey! I noticed we both love {interest}. What got you into it?",
    "Your profile is really cool! Have you been to any {event} lately?",
    "I saw you're into {anime}! That's one of my favorites too! What do you think of the latest arc?",
    "Hi! I'm always looking to connect with fellow {interest} fans. What are your favorites?",
    "Hello! Your {skill} work looks amazing! How long have you been doing it?"
]

conversation_responses = [
    "Thanks for reaching out! I've been into {interest} for about {years} years now. It's such a passion of mine!",
    "That's awesome! I love meeting people who share similar interests. Have you checked out {recommendation}?",
    "I know right?! The latest episode was incredible. I can't wait to see what happens next!",
    "Absolutely! {event} events are always so much fun. I try to go whenever I can!",
    "Thank you so much! I've been practicing for a while now. It's been an amazing journey!"
]

async def clear_existing_bots():
    """Clear existing bot data"""
    await db.users.delete_many({"is_bot": True})
    await db.agent_conversations.delete_many({})
    await db.graph_nodes.delete_many({})
    await db.user_integrations.delete_many({})
    await db.friendships.delete_many({})
    print("✅ Cleared existing bot data")

async def generate_anime_bot():
    """Generate a single bot with dual personalities (Real + Avatar)"""
    # Real World identity
    real_first = random.choice(real_first_names)
    real_last = random.choice(real_last_names)
    real_name = f"{real_first} {real_last}"
    
    # Avatar World identity
    avatar_name = random.choice(anime_first_names)
    
    user_id = f'bot-{uuid.uuid4()}'
    age = random.randint(18, 35)
    gender = random.choice(['Male', 'Female', 'Non-binary'])
    location = random.choice(cities)
    job = random.choice(jobs)
    user_interests = random.sample(interests, random.randint(4, 7))
    
    # Real World: Use AI-generated realistic human face
    # Using thispersondoesnotexist-like API or random seed-based realistic avatars
    real_picture = f'https://i.pravatar.cc/400?img={random.randint(1, 70)}'
    
    # Avatar World: Use anime-style avatar
    avatar_seed = avatar_name + str(random.randint(1, 1000))
    avatar_picture = f'https://api.dicebear.com/7.x/adventurer/svg?seed={avatar_seed}'
    
    bio = f"{age} | {job} | {' & '.join(user_interests[:3])} enthusiast"
    avatar_bio = f"{age} | {job} | {' & '.join(user_interests[:3])} enthusiast 🌸"
    
    user = {
        'id': user_id,
        'email': f'{real_first.lower()}.{real_last.lower()}.{random.randint(100, 999)}@social.app',
        # Real World Data
        'name': real_name,
        'picture': real_picture,
        'bio': bio,
        # Avatar World Data
        'avatar_name': avatar_name,
        'avatar_picture': avatar_picture,
        'avatar_bio': avatar_bio,
        # Common Data
        'age': age,
        'gender': gender,
        'location': location,
        'job_title': job,
        'interests': user_interests,
        'profile_completed': True,
        'onboarding_stage': 'complete',
        'is_bot': True,
        'created_at': datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365))
    }
    
    await db.users.insert_one(user)
    
    # Create graph nodes
    for interest in user_interests:
        await db.graph_nodes.insert_one({
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'node_type': 'interest',
            'label': interest,
            'properties': {'importance': random.randint(7, 10)},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        })
    
    # Create platform integrations
    platforms = [
        ('Instagram', 'social_media'),
        ('Twitter', 'social_media'),
        ('TikTok', 'social_media'),
        ('Discord', 'messaging'),
        ('Twitch', 'social_media')
    ]
    
    for platform_name, platform_type in random.sample(platforms, random.randint(2, 4)):
        await db.user_integrations.insert_one({
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'platform_name': platform_name,
            'platform_type': platform_type,
            'connected': True,
            'connected_at': datetime.now(timezone.utc).isoformat(),
            'last_sync': datetime.now(timezone.utc).isoformat(),
            'data_collected': random.randint(50, 500)
        })
    
    # Generate posts
    num_posts = random.randint(3, 8)
    posts = []
    for i in range(num_posts):
        template = random.choice(posts_templates)
        post_text = template.format(
            anime=random.choice(animes),
            interest=random.choice(user_interests),
            day=random.choice(['Monday', 'Friday', 'weekend']),
            event=random.choice(events),
            city=random.choice(cities),
            game=random.choice(games),
            skill=random.choice(skills)
        )
        posts.append({
            'id': str(uuid.uuid4()),
            'text': post_text,
            'created_at': (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))).isoformat(),
            'likes': random.randint(5, 150),
            'comments': random.randint(0, 25)
        })
    
    # Store posts
    await db.users.update_one(
        {'id': user_id},
        {'$set': {'posts': posts}}
    )
    
    return user_id, real_name, avatar_name, user_interests

async def create_avatar_conversations(bot_ids, bot_data):
    """Create conversations between avatars"""
    print("\n🤖 Creating avatar conversations...")
    
    # Create conversations between random pairs
    num_conversations = min(30, len(bot_ids) * 2)
    
    for i in range(num_conversations):
        # Pick two random bots
        bot1_id = random.choice(bot_ids)
        bot2_id = random.choice([b for b in bot_ids if b != bot1_id])
        
        # Check if conversation exists
        existing = await db.agent_conversations.find_one({
            "$or": [
                {"agent1_user_id": bot1_id, "agent2_user_id": bot2_id},
                {"agent1_user_id": bot2_id, "agent2_user_id": bot1_id}
            ]
        })
        
        if existing:
            continue
        
        bot1 = bot_data[bot1_id]
        bot2 = bot_data[bot2_id]
        
        # Find shared interests
        shared = list(set(bot1['interests']) & set(bot2['interests']))
        
        # Generate conversation
        messages = []
        
        # Bot 1 starts
        starter = random.choice(conversation_starters).format(
            interest=random.choice(shared) if shared else random.choice(bot1['interests']),
            event=random.choice(events),
            anime=random.choice(animes),
            skill=random.choice(skills)
        )
        messages.append({
            "sender": bot1_id,
            "message": starter,
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72))).isoformat()
        })
        
        # Bot 2 responds
        response = random.choice(conversation_responses).format(
            interest=random.choice(shared) if shared else random.choice(bot2['interests']),
            years=random.randint(2, 10),
            recommendation=random.choice(animes),
            event=random.choice(events)
        )
        messages.append({
            "sender": bot2_id,
            "message": response,
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 71))).isoformat()
        })
        
        # Calculate compatibility
        compatibility = min(len(shared) * 15 + random.randint(10, 30), 95)
        
        conversation = {
            'id': str(uuid.uuid4()),
            'agent1_user_id': bot1_id,
            'agent2_user_id': bot2_id,
            'messages': messages,
            'compatibility_score': compatibility,
            'conversation_summary': f"Discussed {', '.join(shared[:3])}" if shared else "Getting to know each other",
            'status': 'active',
            'created_at': (datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72))).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        await db.agent_conversations.insert_one(conversation)
        print(f"  💬 {bot1['name']} ↔ {bot2['name']} ({compatibility}% compatible)")

async def auto_friend_bots_to_users():
    """Auto-friend some bots to real users"""
    print("\n👥 Adding bot friends to real users...")
    
    # Get all real users
    real_users = await db.users.find({"is_bot": {"$ne": True}}, {"_id": 0}).to_list(100)
    
    # Get all bots
    bots = await db.users.find({"is_bot": True}, {"_id": 0}).to_list(100)
    
    for real_user in real_users:
        # Add 10-15 random bots as friends
        num_friends = min(random.randint(10, 15), len(bots))
        friend_bots = random.sample(bots, num_friends)
        
        for bot in friend_bots:
            # Check if already friends
            existing = await db.friendships.find_one({
                "$or": [
                    {"user_id": real_user['id'], "friend_id": bot['id']},
                    {"user_id": bot['id'], "friend_id": real_user['id']}
                ]
            })
            
            if not existing:
                await db.friendships.insert_one({
                    'id': str(uuid.uuid4()),
                    'user_id': real_user['id'],
                    'friend_id': bot['id'],
                    'status': 'accepted',
                    'requested_at': (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))).isoformat(),
                    'accepted_at': (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 29))).isoformat()
                })
        
        print(f"  ✅ Added {num_friends} bot friends to {real_user['name']}")

async def main():
    print("🎌 Creating Dual-World Bot Profiles (Real + Avatar)...\n")
    
    # Clear existing
    await clear_existing_bots()
    
    # Generate 50 bots
    bot_ids = []
    bot_data = {}
    
    for i in range(50):
        user_id, real_name, avatar_name, interests = await generate_anime_bot()
        bot_ids.append(user_id)
        bot_data[user_id] = {
            'real_name': real_name, 
            'avatar_name': avatar_name, 
            'interests': interests
        }
        print(f"✅ Bot {i+1}/50: {real_name} / {avatar_name}")
        await asyncio.sleep(0.05)
    
    # Create avatar conversations
    await create_avatar_conversations(bot_ids, bot_data)
    
    # Auto-friend to real users
    await auto_friend_bots_to_users()
    
    # Stats
    print("\n📊 Final Statistics:")
    user_count = await db.users.count_documents({'is_bot': True})
    conv_count = await db.agent_conversations.count_documents({})
    friend_count = await db.friendships.count_documents({})
    node_count = await db.graph_nodes.count_documents({})
    
    print(f"  Dual-World Bots: {user_count}")
    print(f"  Avatar Conversations: {conv_count}")
    print(f"  Friendships: {friend_count}")
    print(f"  Graph Nodes: {node_count}")
    print("\n🎉 Complete! Your social media is now populated with dual-world bots!")
    print("   - Real World: Realistic names & photos")
    print("   - Avatar World: Anime-style avatars")

if __name__ == '__main__':
    asyncio.run(main())
