import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

async def analyze_dates():
    # Load environment variables
    env_path = os.path.join(backend_dir, '.env')
    load_dotenv(dotenv_path=env_path)
    
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["neurallinks_local"]
    
    print("Analyzing 'created_at' formats in 'posts' collection...")
    
    total_posts = await db.posts.count_documents({})
    print(f"Total posts: {total_posts}")
    
    formats = {}
    
    async for post in db.posts.find({}, {"created_at": 1}):
        created_at = post.get('created_at')
        type_name = type(created_at).__name__
        
        if type_name == 'str':
            # Try to guess format
            if 'T' in created_at:
                fmt = "ISO String"
            else:
                fmt = "Non-ISO String"
        else:
            fmt = type_name
            
        if fmt not in formats:
            formats[fmt] = 0
        formats[fmt] += 1
        
        if formats[fmt] < 3:
            print(f"Sample {fmt}: {created_at}")

    print("\nDistribution:")
    for fmt, count in formats.items():
        print(f"  {fmt}: {count}")

    client.close()

if __name__ == "__main__":
    asyncio.run(analyze_dates())

