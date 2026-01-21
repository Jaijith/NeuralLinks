#!/usr/bin/env python3
"""
Test Diverse Post Generation
Creates posts with new types: friend_interaction, joke, current_events, pleasantries, etc.
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
from datetime import datetime, timezone
from core.config import get_openai_client
from domain.graph.rag import GraphRAG
from domain.avatar.intelligent import IntelligentAvatar

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

async def test_diverse_posts():
    """Test the new diverse post generation"""
    mongo_url = get_mongo_url()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']
    
    print("\n" + "="*70)
    print("║  🎨 Testing Diverse Post Generation")
    print("="*70 + "\n")
    
    # Get an avatar to test with
    user = await db.users.find_one({"avatar_name": "DigitalHunter"})
    
    if not user:
        print("❌ No avatar found")
        client.close()
        return
    
    user_id = user.get('id')
    avatar_name = user.get('avatar_name')
    
    print(f"✅ Testing with avatar: {avatar_name}")
    print(f"   User ID: {user_id}\n")
    
    # Initialize intelligent avatar
    openai_client = get_openai_client()
    graph_rag = GraphRAG(db, openai_client, "gpt-4o-mini")
    intelligent_avatar = IntelligentAvatar(db, openai_client, "gpt-4o-mini", graph_rag)
    
    # Test different post types
    post_types = [
        ("friend_interaction", "Comment on friend's activity"),
        ("joke", "Share a funny observation"),
        ("current_events", "React to news/trends"),
        ("pleasantry", "Casual greeting/check-in"),
        ("friendly_banter", "Playful teasing")
    ]
    
    for post_type, description in post_types:
        print(f"\n{'='*70}")
        print(f"Testing: {post_type.upper()} - {description}")
        print("="*70)
        
        try:
            result = await intelligent_avatar.generate_diverse_post(
                user_id=user_id,
                post_type=post_type
            )
            
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
            else:
                post_content = result.get('content', '')
                print(f"✅ Generated post:")
                print(f"\n{post_content}\n")
                print(f"Length: {len(post_content)} characters")
        
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        # Small delay between requests
        await asyncio.sleep(2)
    
    # Test auto-selection
    print(f"\n{'='*70}")
    print("Testing: AUTO - Let AI choose post type")
    print("="*70)
    
    try:
        result = await intelligent_avatar.generate_diverse_post(
            user_id=user_id,
            post_type="auto"
        )
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            post_content = result.get('content', '')
            selected_type = result.get('type', 'unknown')
            print(f"✅ AI selected type: {selected_type}")
            print(f"\n{post_content}\n")
    
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    client.close()
    print("\n✅ Testing complete!\n")

if __name__ == "__main__":
    asyncio.run(test_diverse_posts())
