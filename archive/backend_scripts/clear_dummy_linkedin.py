#!/usr/bin/env python3
"""
Clear dummy/placeholder LinkedIn connections that don't have OAuth access tokens
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "neuralinks")

async def clear_dummy_linkedin():
    """Remove LinkedIn integrations that don't have access_token (dummy connections)"""
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Find all LinkedIn integrations
    linkedin_integrations = await db.user_integrations.find({
        "platform_name": "linkedin"
    }).to_list(length=100)
    
    print(f"Found {len(linkedin_integrations)} LinkedIn integration(s)")
    
    deleted_count = 0
    for integration in linkedin_integrations:
        # Check if it has an access_token (real OAuth connection)
        has_access_token = bool(integration.get("access_token"))
        is_connected = integration.get("connected", False)
        
        # Delete if:
        # 1. No access_token (dummy/placeholder)
        # 2. OR connected=False (OAuth not completed)
        if not has_access_token or not is_connected:
            await db.user_integrations.delete_one({"_id": integration["_id"]})
            deleted_count += 1
            print(f"  Deleted dummy connection for user {integration.get('user_id', 'unknown')}")
        else:
            print(f"  Keeping real connection for user {integration.get('user_id', 'unknown')} (has access_token)")
    
    print(f"\nDeleted {deleted_count} dummy LinkedIn connection(s)")
    print("You can now connect LinkedIn fresh via OAuth.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(clear_dummy_linkedin())



