"""
Force DigitalHunter to create a post immediately
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncAzureOpenAI
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from graph_rag import GraphRAG
from intelligent_avatar import IntelligentAvatar

load_dotenv()

async def force_post():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['neurallinks_local']
    
    your_id = 'dedc30ef-dca9-467d-84b1-5e643941e6fd'
    
    print('🚀 FORCING DIGITALHUNTER TO POST')
    print('='*80)
    print()
    
    # Setup LLM
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if endpoint and not endpoint.startswith('https://'):
        endpoint = f"https://{endpoint}.openai.azure.com"
    
    llm = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2025-02-01-preview"
    )
    
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    graph_rag = GraphRAG(db)
    avatar = IntelligentAvatar(db, llm, deployment, graph_rag)
    
    print('1️⃣ Generating post content...')
    result = await avatar.generate_avatar_post(your_id, "general")
    
    if 'error' in result:
        print(f'❌ Error: {result["error"]}')
        return
    
    post_content = result.get('content', '')
    print(f'✅ Generated: "{post_content[:80]}..."')
    print()
    
    print('2️⃣ Creating post in database...')
    
    # Choose world randomly
    import random
    world_mode = random.choice(['real', 'avatar'])
    
    post = {
        "id": f"post-{your_id}-{datetime.now(timezone.utc).timestamp()}",
        "user_id": your_id,
        "text": post_content,
        "content": post_content,
        "post_type": world_mode,
        "likes": 0,
        "comments": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Add to posts collection
    await db.posts.insert_one(post)
    print(f'✅ Added to posts collection')
    
    # Add to user document
    post_clean = {k: v for k, v in post.items() if k != '_id'}
    field_name = 'avatar_posts' if world_mode == 'avatar' else 'posts'
    await db.users.update_one(
        {"id": your_id},
        {"$push": {field_name: post_clean}}
    )
    print(f'✅ Added to user document ({world_mode} world)')
    print()
    
    # Log activity
    await db.activity_logs.insert_one({
        "user_id": your_id,
        "action_type": "post_created",
        "description": f"Created post in {world_mode} world",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "post_id": post["id"],
            "world_mode": world_mode
        }
    })
    print(f'✅ Logged activity')
    print()
    
    print('='*80)
    print('🎉 POST CREATED SUCCESSFULLY!')
    print('='*80)
    print(f'World: {world_mode}')
    print(f'Content: "{post_content[:100]}..."')
    print()
    print('Refresh your browser to see it!')
    
    client.close()

if __name__ == '__main__':
    asyncio.run(force_post())




