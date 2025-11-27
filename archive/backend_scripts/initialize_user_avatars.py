import asyncio
import random
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Avatar nickname suggestions
avatar_prefixes = [
    'Cyber', 'Neon', 'Digital', 'Quantum', 'Stellar', 'Cosmic', 'Shadow', 
    'Phoenix', 'Dragon', 'Storm', 'Thunder', 'Lightning', 'Frost', 'Flame',
    'Crystal', 'Mystic', 'Lunar', 'Solar', 'Nova', 'Eclipse', 'Nebula',
    'Void', 'Astral', 'Ethereal', 'Spectral', 'Phantom'
]

avatar_suffixes = [
    'Walker', 'Rider', 'Hunter', 'Seeker', 'Warrior', 'Sage', 'Blade',
    'Knight', 'Rogue', 'Mage', 'Ghost', 'Spirit', 'Soul', 'Heart',
    'Mind', 'Dream', 'Star', 'Moon', 'Sun', 'Wave', 'Wind'
]

async def initialize_avatar_profiles():
    """Initialize avatar profiles for all existing real users"""
    print("🤖 Initializing Avatar Profiles for Existing Users...\n")
    
    # Get all real users (not bots) without avatar profiles
    users = await db.users.find({
        "is_bot": {"$ne": True},
        "$or": [
            {"avatar_name": {"$exists": False}},
            {"avatar_name": None},
            {"avatar_name": ""}
        ]
    }, {"_id": 0}).to_list(1000)
    
    print(f"Found {len(users)} users without avatar profiles\n")
    
    for user in users:
        # Generate avatar nickname
        prefix = random.choice(avatar_prefixes)
        suffix = random.choice(avatar_suffixes)
        avatar_nickname = f"{prefix}{suffix}"
        
        # Generate avatar image (anime style)
        avatar_seed = f"{user['name']}{random.randint(100, 999)}"
        avatar_picture = f"https://api.dicebear.com/7.x/adventurer/svg?seed={avatar_seed}"
        
        # Create avatar bio
        real_interests = user.get('interests', [])
        avatar_bio = f"Digital warrior in the virtual realm | {' • '.join(real_interests[:3]) if real_interests else 'Explorer'}"
        
        # Avatar job titles (virtual themed)
        avatar_jobs = [
            'Digital Architect', 'Cyber Guardian', 'Virtual Explorer',
            'Data Nomad', 'Code Warrior', 'Dream Weaver',
            'Reality Hacker', 'Quantum Traveler', 'Neural Artist'
        ]
        avatar_job = random.choice(avatar_jobs)
        
        # Avatar locations (virtual themed)
        avatar_locations = [
            'Cyberspace', 'Virtual Realm', 'Digital Haven',
            'Neon City', 'Quantum Zone', 'Neural Network',
            'Data Stream', 'Cloud Nine', 'Matrix Core'
        ]
        avatar_location = random.choice(avatar_locations)
        
        # Update user with avatar profile
        await db.users.update_one(
            {"id": user['id']},
            {"$set": {
                "avatar_name": avatar_nickname,
                "avatar_picture": avatar_picture,
                "avatar_bio": avatar_bio,
                "avatar_job_title": avatar_job,
                "avatar_location": avatar_location,
                "avatar_interests": real_interests,  # Start with same interests
                "avatar_posts": []  # Initialize empty avatar posts
            }}
        )
        
        print(f"✅ {user['name']} -> Avatar: {avatar_nickname}")
    
    print(f"\n🎉 Complete! Initialized {len(users)} avatar profiles")
    print("All users now have both Real and Avatar identities!")

if __name__ == '__main__':
    asyncio.run(initialize_avatar_profiles())
