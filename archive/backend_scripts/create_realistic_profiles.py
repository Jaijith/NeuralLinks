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

# Realistic data
first_names = [
    'James', 'John', 'Robert', 'Michael', 'William', 'David', 'Richard', 'Joseph', 'Thomas', 'Christopher',
    'Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth', 'Barbara', 'Susan', 'Jessica', 'Sarah', 'Karen',
    'Daniel', 'Matthew', 'Anthony', 'Mark', 'Donald', 'Steven', 'Andrew', 'Paul', 'Joshua', 'Kenneth',
    'Emma', 'Olivia', 'Ava', 'Isabella', 'Sophia', 'Mia', 'Charlotte', 'Amelia', 'Harper', 'Evelyn'
]

last_names = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
    'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
    'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson'
]

jobs = [
    'Software Engineer', 'Product Manager', 'Data Scientist', 'Marketing Manager', 'Sales Director',
    'Teacher', 'Nurse', 'Doctor', 'Lawyer', 'Accountant', 'Architect', 'Designer', 'Consultant',
    'Entrepreneur', 'Financial Analyst', 'Project Manager', 'HR Manager', 'Operations Manager'
]

cities = [
    'New York, NY', 'Los Angeles, CA', 'Chicago, IL', 'Houston, TX', 'Phoenix, AZ',
    'Philadelphia, PA', 'San Antonio, TX', 'San Diego, CA', 'Dallas, TX', 'San Jose, CA',
    'Austin, TX', 'Jacksonville, FL', 'Fort Worth, TX', 'Columbus, OH', 'San Francisco, CA',
    'Charlotte, NC', 'Indianapolis, IN', 'Seattle, WA', 'Denver, CO', 'Boston, MA'
]

interests = [
    'travel', 'photography', 'cooking', 'fitness', 'reading', 'movies', 'music', 'hiking',
    'yoga', 'running', 'cycling', 'swimming', 'art', 'wine', 'food', 'technology', 'sports'
]

async def create_realistic_profiles():
    print("🌍 Creating 50 Realistic Profiles for Real World...\n")
    
    # Clear existing real world bots
    await db.users.delete_many({"is_bot": True, "bot_type": "realistic"})
    
    for i in range(50):
        gender = random.choice(['Male', 'Female'])
        first = random.choice(first_names)
        last = random.choice(last_names)
        full_name = f"{first} {last}"
        
        user_id = f'real-bot-{uuid.uuid4()}'
        age = random.randint(25, 45)
        location = random.choice(cities)
        job = random.choice(jobs)
        user_interests = random.sample(interests, random.randint(3, 6))
        
        # Use realistic photos (UI Avatars)
        picture = f"https://ui-avatars.com/api/?name={first}+{last}&background=random&size=200&bold=true"
        
        bio = f"{job} | {', '.join(user_interests[:3])} enthusiast"
        
        user = {
            'id': user_id,
            'email': f'{first.lower()}.{last.lower()}@professional.com',
            'name': full_name,
            'picture': picture,
            'age': age,
            'gender': gender,
            'location': location,
            'bio': bio,
            'job_title': job,
            'interests': user_interests,
            'profile_completed': True,
            'onboarding_stage': 'complete',
            'is_bot': True,
            'bot_type': 'realistic',
            'created_at': datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365))
        }
        
        await db.users.insert_one(user)
        
        # Add graph nodes
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
        
        print(f"✅ {i+1}/50: {full_name} ({job})")
    
    print(f"\n🎉 Created 50 realistic profiles!")

asyncio.run(create_realistic_profiles())
