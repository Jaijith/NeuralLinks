"""
Profile Routes
"""

from fastapi import APIRouter, Request, HTTPException, Query, UploadFile, File, Form
from typing import Dict, Any, Optional
from core.auth import require_auth
from services.user_service import UserService
from services.friend_service import FriendService
from core.database import get_database
from utils.file_storage import save_file, get_file_url
import logging

db = get_database()
logger = logging.getLogger(__name__)
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
    
    # Check privacy settings - only if not viewing own profile
    if user.id != user_id:
        profile_privacy = target_user.get('profile_privacy', 'everyone')
        
        if profile_privacy == 'private':
            # Profile is completely private
            raise HTTPException(status_code=403, detail="Profile is in private mode")
        elif profile_privacy == 'friends':
            # Only friends can view
            if friendship_status != 'accepted':
                raise HTTPException(status_code=403, detail="Profile is in friends-only mode")
    
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


@router.post("/profile/upload-picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    world_mode: str = Form("real"),
    request: Request = None
):
    """Upload profile picture for Sense (real) or Maya (avatar) world"""
    user = await require_auth(request)
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file content
    file_content = await file.read()
    
    # Save file
    try:
        file_path = await save_file(file_content, file.filename, 'profile_pictures')
        image_url = get_file_url(file_path)
        logger.info(f"Profile picture saved: {file_path}, URL: {image_url}")
    except Exception as e:
        logger.error(f"Error saving profile picture: {e}")
        raise HTTPException(status_code=500, detail="Failed to save profile picture")
    
    # Update user profile
    user_service = get_user_service()
    if world_mode == 'avatar':
        # Update avatar picture
        await db.users.update_one(
            {"id": user.id},
            {"$set": {"avatar_picture": image_url}}
        )
    else:
        # Update real profile picture
        await db.users.update_one(
            {"id": user.id},
            {"$set": {"picture": image_url}}
        )
    
    return {
        "success": True,
        "image_url": image_url,
        "world_mode": world_mode
    }


@router.post("/profile/upload-cover")
async def upload_cover_photo(
    file: UploadFile = File(...),
    world_mode: str = Form("real"),
    request: Request = None
):
    """Upload cover photo for Sense (real) or Maya (avatar) world"""
    user = await require_auth(request)
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file content
    file_content = await file.read()
    
    # Save file
    try:
        file_path = await save_file(file_content, file.filename, 'cover_photos')
        image_url = get_file_url(file_path)
        logger.info(f"Cover photo saved: {file_path}, URL: {image_url}")
    except Exception as e:
        logger.error(f"Error saving cover photo: {e}")
        raise HTTPException(status_code=500, detail="Failed to save cover photo")
    
    # Update user profile
    field_name = "avatar_cover_photo" if world_mode == 'avatar' else "cover_photo"
    await db.users.update_one(
        {"id": user.id},
        {"$set": {field_name: image_url}}
    )
    
    return {
        "success": True,
        "image_url": image_url,
        "world_mode": world_mode
    }

