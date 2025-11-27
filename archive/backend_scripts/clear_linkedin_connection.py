#!/usr/bin/env python3
"""Script to clear LinkedIn connection status"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def clear_linkedin_connections():
    """Clear all LinkedIn integration records"""
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    if not mongo_url or not db_name:
        print("Error: MONGO_URL and DB_NAME must be set in environment")
        sys.exit(1)
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Find all LinkedIn integrations
    linkedin_integrations = await db.user_integrations.find(
        {"platform_name": "linkedin"}
    ).to_list(100)
    
    if not linkedin_integrations:
        print("No LinkedIn connections found to clear.")
        return
    
    print(f"Found {len(linkedin_integrations)} LinkedIn connection(s) to clear:")
    for integration in linkedin_integrations:
        user_id = integration.get("user_id", "unknown")
        connected = integration.get("connected", False)
        print(f"  - User ID: {user_id}, Connected: {connected}")
    
    # Delete all LinkedIn integrations
    result = await db.user_integrations.delete_many({"platform_name": "linkedin"})
    
    print(f"\n✅ Cleared {result.deleted_count} LinkedIn connection(s).")
    print("You can now connect LinkedIn fresh via OAuth.")

if __name__ == "__main__":
    asyncio.run(clear_linkedin_connections())



