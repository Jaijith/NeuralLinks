"""
Database connection and utilities
Centralized database access for the application
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection settings
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'neurallinks_local')

# Global database client (initialized on first access)
_client: Optional[AsyncIOMotorClient] = None
_db = None


def get_mongo_client() -> AsyncIOMotorClient:
    """Get or create MongoDB client"""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URL)
    return _client


def get_database():
    """Get database instance"""
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client[DB_NAME]
    return _db


async def close_database():
    """Close database connection"""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None


# Initialize database on import (for backward compatibility)
db = get_database()

