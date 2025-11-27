import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

async def migrate_dates():
    # Load environment variables
    env_path = os.path.join(backend_dir, '.env')
    load_dotenv(dotenv_path=env_path)
    
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["neurallinks_local"]
    
    print("Migrating posts to standard ISO string format...")
    
    count = 0
    updated = 0
    
    async for post in db.posts.find({}):
        count += 1
        updates = {}
        
        # Process created_at
        created_at = post.get('created_at')
        if isinstance(created_at, datetime):
            # Convert BSON Date to ISO string
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            updates['created_at'] = created_at.isoformat()
        
        # Process timestamp
        timestamp = post.get('timestamp')
        if isinstance(timestamp, datetime):
            # Convert BSON Date to ISO string
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            updates['timestamp'] = timestamp.isoformat()
            
        if updates:
            await db.posts.update_one({"_id": post["_id"]}, {"$set": updates})
            updated += 1
            if updated % 10 == 0:
                print(f"Updated {updated} posts...", end="\r")
    
    print(f"\nMigration complete!")
    print(f"Processed: {count}")
    print(f"Updated: {updated}")

    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_dates())

