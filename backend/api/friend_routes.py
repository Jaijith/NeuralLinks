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
    user = await require_auth(request)
    friend_service = get_friend_service()
    result = await friend_service.send_friend_request(user.id, friend_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send friend request"))
    return {"message": "Friend request sent", "friendship": result.get("friendship")}


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

