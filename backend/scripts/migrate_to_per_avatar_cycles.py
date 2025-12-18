"""
Migration script to create EventBridge rules for existing active avatars.

This script should be run once after deploying the per-avatar cycle system
to create EventBridge rules for all avatars that currently have autonomy enabled.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from domain.avatar.cycle_manager import AvatarCycleManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_avatars():
    """Create EventBridge rules for all active avatars"""
    # Get MongoDB URI
    mongodb_uri = os.environ.get('MONGODB_URI')
    if not mongodb_uri:
        # Try to get from secrets (for local testing)
        mongodb_uri = "mongodb+srv://2n1user:bSe4As5QIZGGRndR@avatarcluster0.pfih8m3.mongodb.net/?appName=AvatarCluster0"
        logger.warning("Using hardcoded MongoDB URI - set MONGODB_URI env var in production")
    
    client = AsyncIOMotorClient(mongodb_uri)
    db = client.neurallinks_local
    
    # Initialize cycle manager
    cycle_manager = AvatarCycleManager()
    
    try:
        # Find all users with autonomy enabled
        users = await db.users.find(
            {
                "avatar_autonomous": True,
                "avatar_name": {"$exists": True, "$ne": None},
                "avatar_picture": {"$exists": True, "$ne": None}
            },
            {"id": 1, "avatar_name": 1, "avatar_activity_level": 1}
        ).to_list(100)
        
        logger.info(f"📊 Found {len(users)} active avatars to migrate")
        
        created = 0
        skipped = 0
        errors = 0
        
        for user in users:
            user_id = user.get('id')
            avatar_name = user.get('avatar_name', 'Unknown')
            activity_level = user.get('avatar_activity_level', 'medium')
            
            # Check if rule already exists
            rule_exists = await cycle_manager.rule_exists(user_id)
            if rule_exists:
                logger.info(f"⏭️  Rule already exists for {avatar_name} ({user_id[:8]}), skipping")
                skipped += 1
                continue
            
            # Create rule
            logger.info(f"📅 Creating rule for {avatar_name} ({user_id[:8]}) - activity: {activity_level}")
            success = await cycle_manager.create_rule(user_id, activity_level)
            
            if success:
                created += 1
                logger.info(f"✅ Created rule for {avatar_name}")
            else:
                errors += 1
                logger.error(f"❌ Failed to create rule for {avatar_name}")
        
        logger.info(f"\n📈 Migration Summary:")
        logger.info(f"   ✅ Created: {created}")
        logger.info(f"   ⏭️  Skipped (already exists): {skipped}")
        logger.info(f"   ❌ Errors: {errors}")
        logger.info(f"   📊 Total: {len(users)}")
        
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(migrate_avatars())

