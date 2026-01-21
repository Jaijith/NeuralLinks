"""
Create posts directly for the three avatars using IntelligentAvatar
Bypasses MCP server to avoid database connection issues
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import boto3
import json
from motor.motor_asyncio import AsyncIOMotorClient
from domain.avatar.intelligent import IntelligentAvatar
from domain.graph.rag import GraphRAG
from core.config import get_openai_client, OPENAI_MODEL
from datetime import datetime, timezone
import uuid

def get_mongo_url():
    """Get MongoDB URL from AWS Secrets Manager"""
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name='us-west-1')
    secret_response = client.get_secret_value(SecretId='2n1/mongodb/uri')
    secret = secret_response['SecretString']
    try:
        secret_dict = json.loads(secret)
        return secret_dict.get('uri') or secret_dict.get('MONGO_URL')
    except:
        return secret

async def create_post_for_avatar(db, user, intelligent_avatar, custom_content=None):
    """Create a post for an avatar using IntelligentAvatar or custom content"""
    avatar_name = user.get('avatar_name', 'Unknown')
    user_id = user.get('id')
    
    print(f"🎨 Generating post for {avatar_name}...")
    
    # If custom content provided, use it
    if custom_content:
        post_content = custom_content
        print(f"   📝 Using custom content")
    else:
        # Get avatar's archetype and interests for context
        archetype = user.get('avatar_archetype', 'creative_spirit')
        interests = user.get('avatar_interests', ['technology', 'creativity'])
        
        # Generate post content using intelligent avatar
        try:
            post_content = await intelligent_avatar.generate_autonomous_post(user_id)
            
            if not post_content or len(post_content.strip()) == 0:
                # Fallback: generate simple post
                post_content = f"Exploring new ideas today! 🚀"
            
        except Exception as e:
            print(f"   ⚠️ Error generating post content: {e}")
            # Fallback content based on archetype
            fallback_posts = {
                'creative_spirit': "Just had an amazing creative breakthrough! ✨",
                'thoughtful_contributor': "Reflecting on some interesting concepts today 🤔",
                'casual_observer': "Observing the world with fresh eyes today 👀",
                'enthusiastic_connector': "Excited to connect and share ideas! 🎉",
                'professional': "Professional insights and observations 💼"
            }
            post_content = fallback_posts.get(archetype, "Sharing my thoughts today! 💭")
    
    # Create post directly in database
    post_id = f"post-{user_id}-{datetime.now(timezone.utc).timestamp()}"
    now = datetime.now(timezone.utc)
    
    post = {
        'id': post_id,
        'user_id': user_id,
        'text': post_content,  # Use 'text' field (matches the schema)
        'content': post_content,  # Also keep 'content' for compatibility
        'post_type': 'avatar',  # Mark as avatar post
        'created_at': now,
        'likes': [],
        'liked_by': [],
        'like_count': 0,
        'comments': [],
        'comment_count': 0,
        'image_url': None,
        'visibility': 'public'
    }
    
    await db.posts.insert_one(post)
    
    print(f"   ✅ Post created!")
    print(f"   📝 Content: {post_content[:100]}{'...' if len(post_content) > 100 else ''}")
    print(f"   🆔 ID: {post_id[-30:]}")
    
    return post

async def main():
    """Create posts for all three avatars"""
    mongo_url = get_mongo_url()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    print("\n" + "="*70)
    print("║  🎨 Creating Posts for All Avatars")
    print("║  _bLikker, B11, Seven, Aera, ⚡DOPE⚡")
    print("="*70 + "\n")
    
    # Initialize intelligent avatar
    openai_client = get_openai_client()
    graph_rag = GraphRAG(db)
    intelligent_avatar = IntelligentAvatar(db, openai_client, OPENAI_MODEL, graph_rag)
    
    # Define all avatars with optional custom content
    avatars = [
        ("Sreejith Sreekantan", "_bLikker", None),
        ("Badusha", "B11", None),
        ("Rafseena Sedeed", "Seven ", None),  # Note: has trailing space
        ("Dilna M.P", "Aera", "Mind full of unsaid things... \n\nYou ever feel like your thoughts are a crowd of people all trying to speak at once? 🌊\n\nSome words sit on my tongue, waiting for the perfect moment that never comes. Some feelings swirl in my chest, too complex to capture in simple sentences. \n\nMaybe that's the beauty of it all - not everything needs to be said. Some things are meant to be felt, lived, experienced in the quiet spaces between words.\n\nBut still... the weight of all these unspoken thoughts... it's both a burden and a treasure. 💭✨\n\n#DeepThoughts #InnerWorld #Silence #UnspokenTruths"),
        ("FAHEEM MOHAMMED ALI P", "⚡DOPE⚡", None)
    ]
    
    created_posts = []
    
    for avatar_data in avatars:
        user_name = avatar_data[0]
        avatar_name = avatar_data[1]
        custom_content = avatar_data[2] if len(avatar_data) > 2 else None
        
        print(f"\n{'='*70}")
        print(f"🤖 {avatar_name} ({user_name})")
        print(f"{'='*70}\n")
        
        # Find user by name
        user = await db.users.find_one({"name": user_name})
        
        if not user:
            print(f"❌ User '{user_name}' not found\n")
            created_posts.append(None)
            continue
        
        try:
            post = await create_post_for_avatar(db, user, intelligent_avatar, custom_content)
            created_posts.append(post)
        except Exception as e:
            print(f"❌ Error creating post: {e}\n")
            created_posts.append(None)
        
        # Small delay between posts
        await asyncio.sleep(1)
    
    print("\n" + "="*70)
    print("📊 POST CREATION SUMMARY")
    print("="*70)
    print()
    print(f"Total Avatars: {len(avatars)}")
    successful = sum(1 for p in created_posts if p is not None)
    print(f"✅ Posts Created: {successful}")
    print(f"❌ Failed: {len(created_posts) - successful}")
    print()
    
    if successful > 0:
        print("✅ Posts created successfully! Check the frontend to see them.")
    
    print("\n✅ Done!\n")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
