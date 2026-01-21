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
import asyncio

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
        
        # Rebuild/update knowledge graph from updated profile in background
        if self.graph_builder:
            asyncio.create_task(self._update_profile_graph_background(user_id))
        
        return {"message": "Profile updated"}
    
    async def _update_profile_graph_background(self, user_id: str):
        """Background task to update knowledge graph from profile"""
        try:
            user_doc = await self.db.users.find_one({"id": user_id})
            if user_doc:
                await self.graph_builder.build_graph_from_profile(user_doc)
                logger.info(f"Background graph update completed for user {user_id}")
        except Exception as e:
            logger.error(f"Background graph update error for user {user_id}: {str(e)}")
    
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
    
    async def delete_account(self, user_id: str) -> Dict[str, Any]:
        """Delete user account and all related data"""
        try:
            # Delete all user's posts
            posts_deleted = await self.db.posts.delete_many({"user_id": user_id})
            logger.info(f"Deleted {posts_deleted.deleted_count} posts for user {user_id}")
            
            # Delete all friendships (both directions)
            friendships_deleted = await self.db.friendships.delete_many({
                "$or": [
                    {"user_id": user_id},
                    {"friend_id": user_id}
                ]
            })
            logger.info(f"Deleted {friendships_deleted.deleted_count} friendships for user {user_id}")
            
            # Delete all user sessions
            sessions_deleted = await self.db.user_sessions.delete_many({"user_id": user_id})
            logger.info(f"Deleted {sessions_deleted.deleted_count} sessions for user {user_id}")
            
            # Delete comments made by user on other posts
            await self.db.posts.update_many(
                {},
                {"$pull": {"comments": {"user_id": user_id}}}
            )
            
            # Delete likes on user's posts and likes made by user
            await self.db.posts.update_many(
                {},
                {"$pull": {"liked_by": user_id}}
            )
            
            # Delete user integrations
            integrations_deleted = await self.db.user_integrations.delete_many({"user_id": user_id})
            logger.info(f"Deleted {integrations_deleted.deleted_count} integrations for user {user_id}")
            
            # Delete avatar conversations
            avatar_conversations_deleted = await self.db.avatar_conversations.delete_many({
                "$or": [
                    {"agent1_user_id": user_id},
                    {"agent2_user_id": user_id}
                ]
            })
            logger.info(f"Deleted {avatar_conversations_deleted.deleted_count} avatar conversations for user {user_id}")
            
            # Delete matches
            matches_deleted = await self.db.matches.delete_many({
                "$or": [
                    {"user_id": user_id},
                    {"matched_user_id": user_id}
                ]
            })
            logger.info(f"Deleted {matches_deleted.deleted_count} matches for user {user_id}")
            
            # Delete human conversations (get match IDs first)
            match_ids = [m['id'] for m in await self.db.matches.find({
                "$or": [
                    {"user_id": user_id},
                    {"matched_user_id": user_id}
                ]
            }, {"id": 1}).to_list(1000)]
            if match_ids:
                conversations_deleted = await self.db.human_conversations.delete_many({"match_id": {"$in": match_ids}})
                logger.info(f"Deleted {conversations_deleted.deleted_count} conversations for user {user_id}")
            
            # Delete autonomous activities
            activities_deleted = await self.db.autonomous_activities.delete_many({"user_id": user_id})
            logger.info(f"Deleted {activities_deleted.deleted_count} activities for user {user_id}")
            
            # Delete graph nodes and edges
            graph_nodes = await self.db.graph_nodes.find({"user_id": user_id}, {"id": 1}).to_list(1000)
            node_ids = [n['id'] for n in graph_nodes]
            
            if node_ids:
                graph_nodes_deleted = await self.db.graph_nodes.delete_many({"user_id": user_id})
                logger.info(f"Deleted {graph_nodes_deleted.deleted_count} graph nodes for user {user_id}")
                
                # Delete graph edges (both directions)
                graph_edges_deleted = await self.db.graph_edges.delete_many({
                    "$or": [
                        {"from_node_id": {"$in": node_ids}},
                        {"to_node_id": {"$in": node_ids}}
                    ]
                })
                logger.info(f"Deleted {graph_edges_deleted.deleted_count} graph edges for user {user_id}")
            
            # Delete AI agents
            agents_deleted = await self.db.ai_agents.delete_many({"user_id": user_id})
            logger.info(f"Deleted {agents_deleted.deleted_count} AI agents for user {user_id}")
            
            # Delete signup request if exists (by email - we'll need to get user email first)
            user_doc = await self.db.users.find_one({"id": user_id}, {"email": 1})
            if user_doc and user_doc.get("email"):
                await self.db.signup_requests.delete_many({"email": user_doc["email"]})
            
            # Finally, delete the user document
            user_deleted = await self.db.users.delete_one({"id": user_id})
            
            if user_deleted.deleted_count > 0:
                logger.info(f"Successfully deleted account for user {user_id}")
                return {
                    "success": True,
                    "message": "Account deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "User not found"
                }
        except Exception as e:
            logger.error(f"Error deleting account for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

