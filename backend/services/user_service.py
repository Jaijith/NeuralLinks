"""
User Service
Handles user and profile business logic
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.database import get_database
from domain.graph.builder import GraphBuilder
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Service for user and profile operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase, graph_builder: Optional[GraphBuilder] = None):
        self.db = db
        self.graph_builder = graph_builder
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0})
        return user
    
    async def get_user_profile(self, user_id: str, world_mode: str = "real") -> Optional[Dict[str, Any]]:
        """Get user profile with world mode support"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        # Apply world mode transformations for bots
        if user.get('is_bot') and world_mode == 'avatar':
            # Use avatar identity
            if 'avatar_name' in user:
                user['display_name'] = user['avatar_name']
                user['display_picture'] = user.get('avatar_picture', user.get('picture'))
                user['display_bio'] = user.get('avatar_bio', user.get('bio'))
            else:
                user['display_name'] = user['name']
                user['display_picture'] = user.get('picture')
                user['display_bio'] = user.get('bio')
        else:
            # Use real identity
            user['display_name'] = user['name']
            user['display_picture'] = user.get('picture')
            user['display_bio'] = user.get('bio')
        
        return user
    
    async def update_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user's real profile"""
        # Only update real profile fields (not avatar fields)
        real_fields = {}
        for key, value in profile_data.items():
            if not key.startswith('avatar_'):
                real_fields[key] = value
        
        # Update user
        await self.db.users.update_one(
            {"id": user_id},
            {"$set": real_fields}
        )
        
        # Rebuild/update knowledge graph from updated profile
        if self.graph_builder:
            try:
                user_doc = await self.db.users.find_one({"id": user_id})
                if user_doc:
                    await self.graph_builder.build_graph_from_profile(user_doc)
            except Exception as e:
                logger.error(f"Graph update error: {str(e)}")
        
        return {"message": "Profile updated"}
    
    async def update_avatar_profile(self, user_id: str, avatar_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user's avatar profile"""
        # Fields that should NOT get the avatar_ prefix (used by autonomous system)
        no_prefix_fields = {'archetype', 'avatar_autonomous', 'avatar_activity_level', 'avatar_actions_enabled'}
        
        # Prefix avatar fields (except autonomy fields)
        avatar_update = {}
        for key, value in avatar_data.items():
            if key in no_prefix_fields or key.startswith('avatar_'):
                # Don't add prefix for autonomy fields or already-prefixed fields
                avatar_update[key] = value
            else:
                # Add avatar_ prefix for display fields (name, bio, etc.)
                avatar_update[f'avatar_{key}'] = value
        
        logger.info(f"🔧 Updating avatar profile for user {user_id}")
        logger.info(f"📝 Received data: {avatar_data}")
        logger.info(f"💾 Saving to DB: {avatar_update}")
        
        # Update user's avatar data
        await self.db.users.update_one(
            {"id": user_id},
            {"$set": avatar_update}
        )
        
        # Verify what was saved
        updated_user = await self.db.users.find_one(
            {"id": user_id}, 
            {"_id": 0, "avatar_autonomous": 1, "avatar_activity_level": 1, "archetype": 1, "avatar_actions_enabled": 1}
        )
        logger.info(f"✅ Verified saved autonomy settings: {updated_user}")
        
        return {"message": "Avatar profile updated", "saved_autonomy": updated_user}
    
    async def get_avatar_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user's avatar profile"""
        user_doc = await self.db.users.find_one({"id": user_id}, {"_id": 0})
        
        if not user_doc:
            return {}
        
        # Extract avatar-specific fields
        avatar_profile = {
            "avatar_name": user_doc.get("avatar_name", ""),
            "avatar_bio": user_doc.get("avatar_bio", ""),
            "avatar_picture": user_doc.get("avatar_picture", ""),
            "avatar_interests": user_doc.get("avatar_interests", []),
            "avatar_job_title": user_doc.get("avatar_job_title", ""),
            "avatar_location": user_doc.get("avatar_location", "")
        }
        
        return avatar_profile

