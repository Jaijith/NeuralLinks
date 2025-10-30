import asyncio
import random
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Sample data for bot generation
first_names_male = ['Alex', 'James', 'Michael', 'David', 'Chris', 'Daniel', 'Matthew', 'Ryan', 'Andrew', 'Josh', 'Kevin', 'Brian', 'Jason', 'Tyler', 'Justin']
first_names_female = ['Sarah', 'Emma', 'Emily', 'Jessica', 'Ashley', 'Sophia', 'Olivia', 'Isabella', 'Mia', 'Charlotte', 'Amelia', 'Harper', 'Evelyn', 'Abigail', 'Madison']
last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Wilson', 'Anderson', 'Taylor', 'Thomas', 'Moore']

cities = [
    'San Francisco, CA', 'New York, NY', 'Los Angeles, CA', 'Chicago, IL', 'Austin, TX',
    'Seattle, WA', 'Boston, MA', 'Denver, CO', 'Portland, OR', 'Miami, FL',
    'Atlanta, GA', 'Phoenix, AZ', 'San Diego, CA', 'Dallas, TX', 'Philadelphia, PA'
]

interests_pool = [
    'hiking', 'photography', 'travel', 'cooking', 'reading', 'yoga', 'music', 'art',
    'technology', 'fitness', 'coffee', 'wine', 'movies', 'gaming', 'startups',
    'meditation', 'running', 'cycling', 'swimming', 'dancing', 'painting', 'writing',
    'guitar', 'piano', 'singing', 'theater', 'volunteering', 'astronomy', 'gardening',
    'photography', 'fashion', 'design', 'architecture', 'history', 'science', 'sports'
]

job_titles = [
    'Software Engineer', 'Product Manager', 'UX Designer', 'Data Scientist', 'Marketing Manager',
    'Creative Director', 'Teacher', 'Nurse', 'Architect', 'Photographer', 'Writer',
    'Chef', 'Entrepreneur', 'Consultant', 'Financial Analyst', 'Doctor', 'Lawyer',
    'Artist', 'Musician', 'Therapist', 'Social Worker', 'Engineer', 'Researcher'
]

bio_templates = [
    '{job} who loves {i1}, {i2}, and {i3}. Always looking for new adventures!',
    'Passionate about {i1} and {i2}. {job} by day, {i3} enthusiast by night.',
    '{job} with a love for {i1}, {i2}, and {i3}. Life is too short not to enjoy it!',
    'Adventure seeker who enjoys {i1}, {i2}, and {i3}. {job} living life to the fullest.',
    '{job} | {i1} lover | {i2} enthusiast | Always exploring {i3}',
]

personality_traits = [
    'adventurous', 'creative', 'analytical', 'empathetic', 'ambitious', 'laid-back',
    'spontaneous', 'organized', 'introverted', 'extroverted', 'optimistic', 'thoughtful',
    'humorous', 'serious', 'curious', 'practical', 'idealistic', 'open-minded'
]

values = [
    'honesty', 'loyalty', 'family', 'career', 'adventure', 'stability', 'creativity',
    'independence', 'community', 'growth', 'health', 'authenticity', 'balance', 'passion'
]

social_platforms = ['Facebook', 'Instagram', 'Twitter', 'LinkedIn', 'TikTok', 'Snapchat']
ecommerce_platforms = ['Amazon', 'Etsy', 'eBay', 'Shopify']
mail_platforms = ['Gmail', 'Outlook', 'Yahoo Mail', 'ProtonMail']
messaging_platforms = ['WhatsApp', 'Telegram', 'Signal', 'Messenger']
dating_platforms = ['Tinder', 'Bumble', 'Hinge', 'OKCupid']

async def generate_bot_profile():
    """Generate a single realistic bot profile"""
    gender = random.choice(['Male', 'Female'])
    first_name = random.choice(first_names_male if gender == 'Male' else first_names_female)
    last_name = random.choice(last_names)
    full_name = f"{first_name} {last_name}"
    
    age = random.randint(22, 45)
    location = random.choice(cities)
    job = random.choice(job_titles)
    
    # Select 4-7 interests
    num_interests = random.randint(4, 7)
    interests = random.sample(interests_pool, num_interests)
    
    # Generate bio
    bio_template = random.choice(bio_templates)
    bio = bio_template.format(
        job=job,
        i1=interests[0],
        i2=interests[1] if len(interests) > 1 else 'life',
        i3=interests[2] if len(interests) > 2 else 'exploring'
    )
    
    user_id = f'bot-{uuid.uuid4()}'
    
    # Create user
    user = {
        'id': user_id,
        'email': f'{first_name.lower()}.{last_name.lower()}@example.com',
        'name': full_name,
        'picture': f'https://api.dicebear.com/7.x/avataaars/svg?seed={full_name}',
        'age': age,
        'gender': gender,
        'location': location,
        'bio': bio,
        'job_title': job,
        'interests': interests,
        'profile_completed': True,
        'onboarding_stage': 'complete',
        'is_bot': True,
        'created_at': datetime.now(timezone.utc)
    }
    
    await db.users.insert_one(user)
    
    # Create AI agent
    agent = {
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'personality_summary': f"{full_name}'s AI agent - {', '.join(random.sample(personality_traits, 3))}",
        'conversation_style': random.choice(['friendly', 'witty', 'thoughtful', 'enthusiastic', 'curious']),
        'knowledge_graph_version': 1,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    await db.ai_agents.insert_one(agent)
    
    # Create graph nodes for interests
    for interest in interests:
        node = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'node_type': 'interest',
            'label': interest,
            'properties': {'category': 'hobby', 'importance': random.randint(1, 10)},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.graph_nodes.insert_one(node)
    
    # Create graph nodes for personality traits
    user_traits = random.sample(personality_traits, random.randint(3, 5))
    for trait in user_traits:
        node = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'node_type': 'trait',
            'label': trait,
            'properties': {'strength': random.randint(1, 10)},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.graph_nodes.insert_one(node)
    
    # Create graph nodes for values
    user_values = random.sample(values, random.randint(3, 5))
    for value in user_values:
        node = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'node_type': 'value',
            'label': value,
            'properties': {'priority': random.randint(1, 10)},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        await db.graph_nodes.insert_one(node)
    
    # Create platform integrations
    connected_socials = random.sample(social_platforms, random.randint(2, 4))
    connected_ecommerce = random.sample(ecommerce_platforms, random.randint(1, 2))
    connected_mail = [random.choice(mail_platforms)]
    connected_messaging = random.sample(messaging_platforms, random.randint(1, 3))
    connected_dating = random.sample(dating_platforms, random.randint(1, 2))
    
    all_platforms = connected_socials + connected_ecommerce + connected_mail + connected_messaging + connected_dating
    
    for platform in all_platforms:
        integration = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'platform_name': platform,
            'platform_type': get_platform_type(platform),
            'connected': True,
            'connected_at': datetime.now(timezone.utc).isoformat(),
            'last_sync': datetime.now(timezone.utc).isoformat(),
            'data_collected': random.randint(10, 500)
        }
        await db.user_integrations.insert_one(integration)
    
    return user_id, full_name

def get_platform_type(platform):
    if platform in social_platforms:
        return 'social_media'
    elif platform in ecommerce_platforms:
        return 'ecommerce'
    elif platform in mail_platforms:
        return 'email'
    elif platform in messaging_platforms:
        return 'messaging'
    elif platform in dating_platforms:
        return 'dating'
    return 'other'

async def generate_all_bots():
    print("🤖 Generating 50 bot profiles with AI agents and graph data...\n")
    
    for i in range(50):
        user_id, name = await generate_bot_profile()
        print(f"✅ Bot {i+1}/50: {name} ({user_id})")
        await asyncio.sleep(0.1)  # Small delay to avoid overwhelming the DB
    
    print("\n🎉 Successfully generated 50 bot profiles!")
    
    # Print statistics
    user_count = await db.users.count_documents({'is_bot': True})
    agent_count = await db.ai_agents.count_documents({})
    node_count = await db.graph_nodes.count_documents({})
    integration_count = await db.user_integrations.count_documents({})
    
    print("\n📊 Statistics:")
    print(f"   Total bot users: {user_count}")
    print(f"   AI agents created: {agent_count}")
    print(f"   Graph nodes: {node_count}")
    print(f"   Platform integrations: {integration_count}")

if __name__ == '__main__':
    asyncio.run(generate_all_bots())
