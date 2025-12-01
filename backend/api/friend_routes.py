"""
Friend Routes
"""

from fastapi import APIRouter, Request, HTTPException, Query
from typing import Optional
from core.auth import require_auth
from services.friend_service import FriendService

router = APIRouter(prefix="/api/friends", tags=["friends"])


def get_friend_service() -> FriendService:
    """Get friend service instance"""
    from app.globals import friend_service
    return friend_service


@router.post("/request/{friend_id}")
async def send_friend_request(friend_id: str, request: Request):
    """Send a friend request"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        user = await require_auth(request)
        logger.info(f"Friend request endpoint called: user_id={user.id}, friend_id={friend_id}")
        
        if not friend_id:
            raise HTTPException(status_code=400, detail="Friend ID is required")
        
        friend_service = get_friend_service()
        result = await friend_service.send_friend_request(user.id, friend_id)
        
        if not result.get("success"):
            error_msg = result.get("error", "Failed to send friend request")
            logger.warning(f"Friend request failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"Friend request sent successfully: user_id={user.id}, friend_id={friend_id}")
        friendship_data = result.get("friendship", {})
        return {"message": "Friend request sent", "friendship": friendship_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in send_friend_request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/accept/{friendship_id}")
async def accept_friend_request(friendship_id: str, request: Request):
    """Accept a friend request"""
    user = await require_auth(request)
    friend_service = get_friend_service()
    result = await friend_service.accept_friend_request(friendship_id, user.id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Friend request not found"))
    return {"message": "Friend request accepted"}


@router.post("/decline/{friendship_id}")
async def decline_friend_request(friendship_id: str, request: Request):
    """Decline a friend request"""
    user = await require_auth(request)
    friend_service = get_friend_service()
    result = await friend_service.decline_friend_request(friendship_id, user.id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Friend request not found"))
    return {"message": "Friend request declined"}


@router.delete("/{friend_id}")
async def remove_friend(friend_id: str, request: Request):
    """Remove a friend"""
    user = await require_auth(request)
    friend_service = get_friend_service()
    result = await friend_service.remove_friend(user.id, friend_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Friendship not found"))
    return {"message": "Friend removed"}


@router.get("/requests")
async def get_friend_requests(request: Request):
    """Get pending friend requests for current user"""
    user = await require_auth(request)
    friend_service = get_friend_service()
    return await friend_service.get_friend_requests(user.id)


@router.get("")
async def get_friends(
    user_id: Optional[str] = Query(None, description="User ID (defaults to current user)"),
    request: Request = None
):
    """Get user's friends list"""
    current_user = await require_auth(request)
    target_user_id = user_id if user_id else current_user.id
    friend_service = get_friend_service()
    return await friend_service.get_friends(target_user_id)


@router.get("/suggestions")
async def get_suggestions(
    limit: int = Query(5, ge=1, le=20),
    world_mode: str = Query("real", description="World mode: 'real' or 'avatar'"),
    request: Request = None
):
    """Get suggested users (users who are not friends and not pending)"""
    from core.database import get_database
    from datetime import datetime, timezone
    
    user = await require_auth(request)
    db = get_database()
    
    # Get current user's friends and pending requests
    friendships = await db.friendships.find({
        "$or": [
            {"user_id": user.id},
            {"friend_id": user.id}
        ]
    }).to_list(1000)
    
    # Get IDs of users we're already connected with
    connected_user_ids = {user.id}  # Include self
    for friendship in friendships:
        if friendship['user_id'] == user.id:
            connected_user_ids.add(friendship['friend_id'])
        else:
            connected_user_ids.add(friendship['user_id'])
    
    # Build query based on world mode
    if world_mode == 'avatar':
        # For Maya world, prefer users with avatar profiles or bots
        query = {
            "id": {"$nin": list(connected_user_ids)},
            "$or": [
                {"avatar_name": {"$exists": True, "$ne": ""}},
                {"is_bot": True}
            ]
        }
    else:
        # For Sense world, get users with completed profiles
        query = {
            "id": {"$nin": list(connected_user_ids)},
            "profile_completed": True
        }
    
    # Get suggested users
    suggested_users = await db.users.find(
        query,
        {"_id": 0, "id": 1, "name": 1, "avatar_name": 1, "picture": 1, "avatar_picture": 1, "bio": 1, "avatar_bio": 1, "is_bot": 1}
    ).limit(limit * 2).to_list(limit * 2)  # Get more to filter
    
    # Calculate mutual connections and format
    suggestions = []
    for suggested_user in suggested_users:
        # Get mutual friends count
        suggested_friends = await db.friendships.find({
            "$or": [
                {"user_id": suggested_user['id'], "status": "accepted"},
                {"friend_id": suggested_user['id'], "status": "accepted"}
            ]
        }).to_list(100)
        
        suggested_friend_ids = set()
        for f in suggested_friends:
            if f['user_id'] == suggested_user['id']:
                suggested_friend_ids.add(f['friend_id'])
            else:
                suggested_friend_ids.add(f['user_id'])
        
        # Get current user's friends
        my_friends = await db.friendships.find({
            "$or": [
                {"user_id": user.id, "status": "accepted"},
                {"friend_id": user.id, "status": "accepted"}
            ]
        }).to_list(100)
        
        my_friend_ids = set()
        for f in my_friends:
            if f['user_id'] == user.id:
                my_friend_ids.add(f['friend_id'])
            else:
                my_friend_ids.add(f['user_id'])
        
        mutual_count = len(suggested_friend_ids & my_friend_ids)
        
        # Determine display name and picture based on world mode
        if world_mode == 'avatar':
            display_name = suggested_user.get('avatar_name') or suggested_user.get('name') or 'Unknown'
            display_picture = suggested_user.get('avatar_picture') or suggested_user.get('picture') or ''
        else:
            display_name = suggested_user.get('name') or 'Unknown'
            display_picture = suggested_user.get('picture') or ''
        
        suggestions.append({
            "id": suggested_user['id'],
            "name": display_name,
            "picture": display_picture,
            "mutual_connections": mutual_count,
            "is_bot": suggested_user.get('is_bot', False)
        })
    
    # Sort by mutual connections (descending) and limit
    suggestions.sort(key=lambda x: x['mutual_connections'], reverse=True)
    return suggestions[:limit]

