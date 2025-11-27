import asyncio
import random
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Realistic data for Sense World
first_names_male = [
    'James', 'Michael', 'David', 'Christopher', 'Matthew', 'Daniel', 'Andrew', 
    'Joshua', 'Ryan', 'Alexander'
]

first_names_female = [
    'Emma', 'Olivia', 'Sophia', 'Isabella', 'Ava', 'Mia', 'Charlotte', 
    'Amelia', 'Harper', 'Emily'
]

last_names = [
    'Anderson', 'Martinez', 'Thompson', 'Garcia', 'Rodriguez', 'Wilson', 
    'Moore', 'Taylor', 'Jackson', 'White', 'Harris', 'Clark', 'Lewis', 
    'Robinson', 'Walker', 'Hall', 'Allen', 'Young', 'King', 'Wright'
]

# Anime names for Maya World
anime_names_male = [
    'Kaito', 'Haruto', 'Riku', 'Yuto', 'Sota', 'Ren', 'Hayato', 'Takumi', 
    'Akira', 'Kenji'
]

anime_names_female = [
    'Sakura', 'Yuki', 'Hana', 'Akari', 'Mei', 'Rin', 'Aiko', 'Natsumi', 
    'Yui', 'Kaede'
]

jobs = [
    'Software Engineer', 'Product Designer', 'Data Scientist', 'Marketing Manager', 
    'Teacher', 'Photographer', 'Entrepreneur', 'Architect', 'Writer', 'Doctor',
    'Lawyer', 'Chef', 'Artist', 'Musician', 'Consultant', 'Financial Analyst',
    'Nurse', 'Social Worker', 'Engineer', 'Therapist'
]

cities = [
    'San Francisco, CA', 'New York, NY', 'Los Angeles, CA', 'Seattle, WA', 
    'Austin, TX', 'Boston, MA', 'Chicago, IL', 'Denver, CO', 'Portland, OR',
    'Miami, FL', 'Atlanta, GA', 'San Diego, CA', 'Phoenix, AZ', 'Dallas, TX',
    'Philadelphia, PA', 'Nashville, TN', 'Charlotte, NC', 'Minneapolis, MN',
    'Detroit, MI', 'San Jose, CA'
]

interests_pool = [
    'hiking', 'photography', 'travel', 'cooking', 'reading', 'yoga', 'music', 
    'art', 'technology', 'fitness', 'coffee', 'movies', 'gaming', 'meditation',
    'running', 'cycling', 'swimming', 'dancing', 'painting', 'writing', 'guitar',
    'singing', 'volunteering', 'astronomy', 'gardening', 'fashion', 'design',
    'anime', 'manga', 'rock climbing', 'surfing', 'skiing', 'tennis', 'basketball'
]

personality_traits = [
    'adventurous', 'creative', 'analytical', 'empathetic', 'ambitious', 
    'spontaneous', 'organized', 'introverted', 'extroverted', 'optimistic',
    'humorous', 'curious', 'thoughtful', 'confident', 'caring', 'passionate'
]

values = [
    'honesty', 'loyalty', 'family', 'career', 'adventure', 'creativity',
    'independence', 'community', 'growth', 'health', 'authenticity', 'balance',
    'integrity', 'compassion', 'ambition', 'freedom'
]

post_templates_real = [
    "Just finished an amazing {activity}! Feeling grateful 🙏",
    "Beautiful day for {activity}. Life is good! ☀️",
    "Weekend vibes: {activity} and good company 💫",
    "Nothing beats a good session of {activity} 💪",
    "Found my new favorite spot for {activity}! 📍",
    "Today's mood: {activity} and chill 😌",
    "Loving this weather perfect for {activity}! 🌤️",
    "Pro tip: {activity} is the best stress relief 🧘",
    "Can't get enough of {activity} these days! ❤️",
    "Life update: Still obsessed with {activity} 🎯"
]

post_templates_avatar = [
    "✨ Exploring new dimensions through {activity}! The journey continues...",
    "🌟 In the Maya realm, {activity} takes on a whole new meaning",
    "🎭 My avatar self loves {activity} even more than I expected",
    "💫 Virtual adventures in {activity} hitting different today",
    "🌸 Maya world vibes: {activity} with endless possibilities",
    "⚡ Channeling pure energy through {activity} in this realm",
    "🎨 Creating magic with {activity} in the avatar world",
    "🌙 Midnight sessions of {activity} in Maya are unmatched",
    "🦋 Transformed by {activity} - avatar life is extraordinary",
    "🔮 Discovering hidden depths through {activity} here"
]

async def get_current_user():
    """Get the current logged-in user (non-bot user)"""
    user = await db.users.find_one({"is_bot": {"$ne": True}})
    return user

async def create_dual_world_bot(bot_num, current_user_id=None):
    """Create a bot with both Sense and Maya profiles"""
    
    gender = random.choice(['Male', 'Female'])
    
    # Sense World Identity
    first_name = random.choice(first_names_male if gender == 'Male' else first_names_female)
    last_name = random.choice(last_names)
    sense_name = f"{first_name} {last_name}"
    
    # Maya World Identity (Anime name)
    maya_first = random.choice(anime_names_male if gender == 'Male' else anime_names_female)
    maya_last = random.choice(['Nightshade', 'Starlight', 'Moonbeam', 'Shadowfire', 
                                'Crystalheart', 'Stormwind', 'Silverwing', 'Dreamweaver',
                                'Frostborn', 'Sunblade'])
    maya_name = f"{maya_first} {maya_last}"
    
    user_id = f'bot-{uuid.uuid4()}'
    age = random.randint(24, 38)
    location = random.choice(cities)
    job = random.choice(jobs)
    user_interests = random.sample(interests_pool, random.randint(5, 8))
    
    # Real photo for Sense (using diverse photo service)
    sense_picture = f"https://randomuser.me/api/portraits/{'men' if gender == 'Male' else 'women'}/{bot_num}.jpg"
    
    # Anime avatar for Maya (using anime avatar API)
    maya_picture = f"https://api.dicebear.com/7.x/big-smile/svg?seed={maya_name.replace(' ', '')}&backgroundColor=b6e3f4,c0aede,d1d4f9"
    
    sense_bio = f"{job} in {location} | Love {', '.join(user_interests[:3])} | Always exploring new adventures 🌟"
    maya_bio = f"✨ {maya_first} in the realm of dreams | {', '.join(user_interests[:3])} enthusiast | Living my best avatar life 🎭"
    
    # Maya nickname
    maya_nickname = maya_name
    
    # User document
    user = {
        'id': user_id,
        'email': f'{first_name.lower()}.{last_name.lower()}.bot@neurallinks.ai',
        'name': sense_name,
        'picture': sense_picture,
        'age': age,
        'gender': gender,
        'location': location,
        'bio': sense_bio,
        'job_title': job,
        'interests': user_interests,
        'profile_completed': True,
        'onboarding_stage': 'complete',
        'is_bot': True,
        'bot_type': 'dual_world',
        'created_at': datetime.now(timezone.utc) - timedelta(days=random.randint(30, 180)),
        
        # Maya World profile (using avatar_ prefix to match backend expectations)
        'avatar_name': maya_nickname,
        'avatar_picture': maya_picture,
        'avatar_bio': maya_bio,
        'avatar_interests': user_interests,  # Same interests in both worlds
        'avatar_job_title': job,  # Same job title in both worlds
        'avatar_location': location,  # Same location in both worlds
        
        # Keep maya_ fields for backward compatibility
        'maya_nickname': maya_nickname,
        'maya_picture': maya_picture,
        'maya_bio': maya_bio,
        'maya_interests': user_interests,
        'maya_personality': ', '.join(random.sample(personality_traits, 3))
    }
    
    await db.users.insert_one(user)
    
    # Create AI agent
    agent = {
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'personality_summary': f"Dual identity: {sense_name} (Sense) / {maya_name} (Maya) - {', '.join(random.sample(personality_traits, 3))}",
        'conversation_style': random.choice(['friendly', 'witty', 'thoughtful', 'enthusiastic', 'playful']),
        'knowledge_graph_version': 1,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    await db.ai_agents.insert_one(agent)
    
    # Create graph nodes for interests
    for interest in user_interests:
        node = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'node_type': 'interest',
            'label': interest,
            'properties': {'category': 'hobby', 'importance': random.randint(7, 10)},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.graph_nodes.insert_one(node)
    
    # Create graph nodes for personality traits
    user_traits = random.sample(personality_traits, random.randint(4, 6))
    for trait in user_traits:
        node = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'node_type': 'trait',
            'label': trait,
            'properties': {'strength': random.randint(7, 10)},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.graph_nodes.insert_one(node)
    
    # Create graph nodes for values
    user_values = random.sample(values, random.randint(4, 6))
    for value in user_values:
        node = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'node_type': 'value',
            'label': value,
            'properties': {'priority': random.randint(7, 10)},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.graph_nodes.insert_one(node)
    
    # Create posts (2-4 real posts, 2-4 avatar posts)
    num_real_posts = random.randint(2, 4)
    num_avatar_posts = random.randint(2, 4)
    
    # Real world posts
    for i in range(num_real_posts):
        activity = random.choice(user_interests)
        content = random.choice(post_templates_real).format(activity=activity)
        
        post = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'content': content,
            'post_type': 'real',
            'likes': random.randint(5, 50),
            'comments': [],
            'created_at': datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60)),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.posts.insert_one(post)
    
    # Avatar world posts
    for i in range(num_avatar_posts):
        activity = random.choice(user_interests)
        content = random.choice(post_templates_avatar).format(activity=activity)
        
        post = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'content': content,
            'post_type': 'avatar',
            'likes': random.randint(5, 50),
            'comments': [],
            'created_at': datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60)),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.posts.insert_one(post)
    
    # Randomly add as friend to current user (40% chance)
    if current_user_id and random.random() < 0.4:
        # Create friendship
        friendship = {
            'id': str(uuid.uuid4()),
            'user_id': current_user_id,
            'friend_id': user_id,
            'status': 'accepted',
            'created_at': datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90))
        }
        await db.friendships.insert_one(friendship)
        
        # Reciprocal friendship
        friendship_reciprocal = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'friend_id': current_user_id,
            'status': 'accepted',
            'created_at': datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90))
        }
        await db.friendships.insert_one(friendship_reciprocal)
        
        return user_id, sense_name, maya_name, True
    
    return user_id, sense_name, maya_name, False

async def generate_all_dual_world_bots():
    print("🌍✨ Generating 20 Dual-World Bot Profiles")
    print("=" * 60)
    print("Creating profiles with:")
    print("  ✓ Sense World (Real) identities with photos")
    print("  ✓ Maya World (Avatar) identities with anime avatars")
    print("  ✓ Complete profile details")
    print("  ✓ Posts in both worlds")
    print("  ✓ Friend connections")
    print("  ✓ Knowledge graphs")
    print("=" * 60)
    print()
    
    # Get current user for friend connections
    current_user = await get_current_user()
    current_user_id = current_user['id'] if current_user else None
    
    if current_user_id:
        print(f"📌 Will add some bots as friends to: {current_user.get('name', 'Current User')}\n")
    
    friends_added = 0
    bot_profiles = []
    
    for i in range(1, 21):
        user_id, sense_name, maya_name, is_friend = await create_dual_world_bot(i, current_user_id)
        
        if is_friend:
            friends_added += 1
            friend_marker = "👥 [FRIEND]"
        else:
            friend_marker = ""
        
        print(f"✅ Bot {i}/20: {sense_name} ↔️ {maya_name} {friend_marker}")
        
        # Fetch full profile for summary
        user = await db.users.find_one({'id': user_id})
        post_count_real = await db.posts.count_documents({'user_id': user_id, 'post_type': 'real'})
        post_count_avatar = await db.posts.count_documents({'user_id': user_id, 'post_type': 'avatar'})
        
        bot_profiles.append({
            'sense_name': sense_name,
            'maya_name': maya_name,
            'age': user['age'],
            'gender': user['gender'],
            'location': user['location'],
            'job': user['job_title'],
            'interests': user['interests'],
            'posts_real': post_count_real,
            'posts_avatar': post_count_avatar,
            'is_friend': is_friend
        })
        
        await asyncio.sleep(0.05)
    
    print("\n" + "=" * 60)
    print("🎉 Successfully generated 20 dual-world bot profiles!")
    print("=" * 60)
    
    # Print statistics
    user_count = await db.users.count_documents({'is_bot': True, 'bot_type': 'dual_world'})
    agent_count = await db.ai_agents.count_documents({})
    node_count = await db.graph_nodes.count_documents({})
    post_count_real = await db.posts.count_documents({'post_type': 'real', 'user_id': {'$regex': '^bot-'}})
    post_count_avatar = await db.posts.count_documents({'post_type': 'avatar', 'user_id': {'$regex': '^bot-'}})
    
    print(f"\n📊 Statistics:")
    print(f"   Total dual-world bots: {user_count}")
    print(f"   Friends added to your account: {friends_added}")
    print(f"   AI agents created: {agent_count}")
    print(f"   Graph nodes: {node_count}")
    print(f"   Real world posts: {post_count_real}")
    print(f"   Avatar world posts: {post_count_avatar}")
    
    print(f"\n📋 Profile Summary:")
    print("=" * 60)
    for i, profile in enumerate(bot_profiles, 1):
        print(f"\n{i}. {profile['sense_name']} / {profile['maya_name']}")
        print(f"   Age: {profile['age']} | Gender: {profile['gender']} | {profile['location']}")
        print(f"   Job: {profile['job']}")
        print(f"   Interests: {', '.join(profile['interests'][:5])}")
        print(f"   Posts: {profile['posts_real']} real, {profile['posts_avatar']} avatar")
        if profile['is_friend']:
            print(f"   ✓ Added as friend")

if __name__ == '__main__':
    asyncio.run(generate_all_dual_world_bots())

