"""
Profile Routes
"""

from fastapi import APIRouter, Request, HTTPException, Query
from typing import Dict, Any, Optional
from core.auth import require_auth
from services.user_service import UserService
from services.friend_service import FriendService
from core.database import get_database

db = get_database()
# Services will be injected from main app
router = APIRouter(prefix="/api", tags=["profile"])


def get_user_service() -> UserService:
    """Get user service instance"""
    from app.globals import user_service
    return user_service


def get_friend_service() -> FriendService:
    """Get friend service instance"""
    from app.globals import friend_service
    return friend_service


@router.get("/users/{user_id}")
async def get_user_profile(
    user_id: str, 
    world_mode: str = Query("real", description="World mode: 'real' or 'avatar'"),
    request: Request = None
):
    """Get user profile by ID with world mode support"""
    user = await require_auth(request)
    
    user_service = get_user_service()
    friend_service = get_friend_service()
    
    target_user = await user_service.get_user_profile(user_id, world_mode)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check friendship status
    friendship_status = await friend_service.get_friendship_status(user.id, user_id)
    target_user['friendship_status'] = friendship_status
    target_user['is_friend'] = friendship_status == 'accepted'
    
    return target_user


@router.put("/profile")
async def update_profile(profile_data: Dict[str, Any], request: Request):
    """Update user's real profile"""
    user = await require_auth(request)
    user_service = get_user_service()
    return await user_service.update_profile(user.id, profile_data)


@router.put("/profile/avatar")
async def update_avatar_profile(avatar_data: Dict[str, Any], request: Request):
    """Update user's avatar profile"""
    user = await require_auth(request)
    user_service = get_user_service()
    return await user_service.update_avatar_profile(user.id, avatar_data)


@router.get("/profile/avatar")
async def get_avatar_profile(request: Request):
    """Get current user's avatar profile"""
    user = await require_auth(request)
    user_service = get_user_service()
    return await user_service.get_avatar_profile(user.id)

