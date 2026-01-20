#!/usr/bin/env python3
"""List all real users in the database"""
import asyncio
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client['neurallinks_local']
    
    users = await db.users.find({}).to_list(1000)
    real_users = [u for u in users if not u.get('is_bot', False)]
    
    print(f'Total real users (non-bots): {len(real_users)}\n')
    print('User list:')
    for i, user in enumerate(real_users, 1):
        name = user.get('name', 'N/A')
        username = user.get('username', 'N/A')
        email = user.get('email', 'N/A')
        avatar_name = user.get('avatar_name', 'NOT SET')
        avatar_auto = user.get('avatar_autonomous', False)
        
        print(f'{i}. Name: {name}')
        print(f'   Username: {username}')
        print(f'   Email: {email[:30]}...' if len(email) > 30 else f'   Email: {email}')
        print(f'   Avatar Name: {avatar_name}')
        print(f'   Avatar Active: {avatar_auto}')
        print()
    
    client.close()

if __name__ == '__main__':
    asyncio.run(main())
