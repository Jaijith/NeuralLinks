"""
Search Routes - User search and discovery
"""

from fastapi import APIRouter, Request, HTTPException, Query
from core.auth import require_auth
from core.database import get_database

db = get_database()
router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search/users")
async def search_users(
    q: str = Query(..., min_length=1),
    world_mode: str = Query("real", description="World mode: 'real' or 'avatar'"),
    request: Request = ...
):
    """Search for users by name, bio, interests, location (supports both Sense and Maya worlds)"""
    user = await require_auth(request)
    
    if len(q) < 1:
        return []
    
    # Build search query based on world mode
    if world_mode == "avatar":
        # Search in avatar fields for Maya world
        # Match users with avatar fields that match query, or bots (which typically have avatar fields)
        search_query = {
            "$and": [
                {"id": {"$ne": user.id}},
                {"profile_completed": True},
                {
                    "$or": [
                        {"avatar_name": {"$regex": q, "$options": "i"}},
                        {"avatar_bio": {"$regex": q, "$options": "i"}},
                        {"avatar_location": {"$regex": q, "$options": "i"}},
                        {"avatar_interests": {"$regex": q, "$options": "i"}},
                        {"avatar_job_title": {"$regex": q, "$options": "i"}},
                        {
                            "$and": [
                                {"is_bot": True},
                                {
                                    "$or": [
                                        {"name": {"$regex": q, "$options": "i"}},
                                        {"bio": {"$regex": q, "$options": "i"}}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    else:
        # Search in real profile fields for Sense world
        search_query = {
            "$and": [
                {"id": {"$ne": user.id}},
                {"profile_completed": True},
                {"$or": [
                    {"name": {"$regex": q, "$options": "i"}},
                    {"bio": {"$regex": q, "$options": "i"}},
                    {"location": {"$regex": q, "$options": "i"}},
                    {"interests": {"$regex": q, "$options": "i"}},
                    {"job_title": {"$regex": q, "$options": "i"}}
                ]}
            ]
        }
    
    users = await db.users.find(search_query, {"_id": 0}).limit(20).to_list(20)
    
    # Check friendship status
    for u in users:
        friendship = await db.friendships.find_one({
            "$or": [
                {"user_id": user.id, "friend_id": u['id']},
                {"user_id": u['id'], "friend_id": user.id}
            ]
        })
        u['friendship_status'] = friendship['status'] if friendship else 'none'
        u['is_friend'] = friendship['status'] == 'accepted' if friendship else False
    
    return users

