"""
Authentication Routes
"""

from fastapi import APIRouter, Request, Response, HTTPException
from core.auth import require_auth
from core.database import get_database
from api.models import User, UserSession
from datetime import datetime, timezone, timedelta
import uuid
import random
import httpx
import logging

db = get_database()
router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.get("/me")
async def get_me(request: Request):
    """Get current user with full profile data"""
    user = await require_auth(request)
    
    # Fetch full user document from database (includes autonomy fields)
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_doc


@router.get("/session-data")
async def get_session_data(request: Request):
    """Get session data from Emergent session_id"""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid session")
            
            data = response.json()
            
            # Check if user exists
            existing_user = await db.users.find_one({"email": data['email']})
            
            if not existing_user:
                # Check if signup request is approved
                signup_request = await db.signup_requests.find_one(
                    {"email": data['email']},
                    sort=[("requested_at", -1)]
                )
                
                if not signup_request:
                    raise HTTPException(
                        status_code=403,
                        detail="Please submit a signup request first. Your request will be reviewed before you can create an account."
                    )
                
                if signup_request.get("status") != "approved":
                    if signup_request.get("status") == "pending":
                        raise HTTPException(
                            status_code=403,
                            detail="Your signup request is pending approval. You will receive an email once it's reviewed."
                        )
                    elif signup_request.get("status") == "rejected":
                        raise HTTPException(
                            status_code=403,
                            detail="Your signup request was not approved. Please contact support for more information."
                        )
                    else:
                        raise HTTPException(
                            status_code=403,
                            detail="Your signup request is not approved. Please contact support."
                        )
                # Create new user with BOTH real and avatar profiles
                # Generate unique user ID first
                new_user_id = str(uuid.uuid4())
                
                # Generate avatar nickname with user ID for uniqueness
                avatar_prefixes = ['Cyber', 'Neon', 'Digital', 'Quantum', 'Stellar', 'Phoenix', 'Dragon', 'Storm', 
                                   'Shadow', 'Crystal', 'Mystic', 'Thunder', 'Void', 'Nova', 'Cosmic', 'Plasma']
                avatar_suffixes = ['Walker', 'Rider', 'Hunter', 'Seeker', 'Warrior', 'Spirit', 'Dream', 'Star',
                                   'Knight', 'Phantom', 'Blade', 'Soul', 'Wing', 'Raven', 'Wolf', 'Falcon']
                
                # Add number suffix for uniqueness
                avatar_nickname = f"{random.choice(avatar_prefixes)}{random.choice(avatar_suffixes)}{random.randint(10, 99)}"
                
                # Generate unique avatar image based on user ID
                avatar_picture = f"https://api.dicebear.com/7.x/adventurer/svg?seed={new_user_id}"
                
                user = User(
                    id=new_user_id,
                    email=data['email'],
                    name=data['name'],
                    picture=data.get('picture'),
                    # Avatar profile (auto-created with unique identity)
                    avatar_name=avatar_nickname,
                    avatar_picture=avatar_picture,
                    avatar_bio="Digital warrior in the virtual realm",
                    avatar_job_title="Virtual Explorer",
                    avatar_location="Cyberspace",
                    avatar_interests=[],
                )
                user_dict = user.model_dump()
                user_dict['created_at'] = user_dict['created_at'].isoformat()
                await db.users.insert_one(user_dict)
                user_id = user.id
                
                # Build initial knowledge graph for new user
                try:
                    from app.globals import graph_builder
                    user_doc = await db.users.find_one({"id": user_id})
                    if user_doc:
                        await graph_builder.build_graph_from_profile(user_doc)
                except Exception as e:
                    logger.error(f"Initial graph build error: {str(e)}")
            else:
                user_id = existing_user['id']
            
            # Create session
            session = UserSession(
                user_id=user_id,
                session_token=data['session_token'],
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )
            session_dict = session.model_dump()
            session_dict['expires_at'] = session_dict['expires_at'].isoformat()
            session_dict['created_at'] = session_dict['created_at'].isoformat()
            await db.user_sessions.insert_one(session_dict)
            
            return {
                "user_id": user_id,
                "email": data['email'],
                "name": data['name'],
                "picture": data.get('picture'),
                "session_token": data['session_token']
            }
    except Exception as e:
        logger.error(f"Session data error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    user = await require_auth(request)
    
    # Clear session token
    response.delete_cookie("session_token")
    return {"message": "Logged out"}


@router.delete("/account")
async def delete_account(request: Request, response: Response):
    """Delete user account and all related data"""
    user = await require_auth(request)
    
    from services.user_service import UserService
    from core.database import get_database
    from app.globals import graph_builder
    
    db = get_database()
    user_service = UserService(db, graph_builder)
    
    result = await user_service.delete_account(user.id)
    
    if result.get("success"):
        # Clear session token
        response.delete_cookie("session_token")
        logger.info(f"Account deleted for user {user.id}")
        return {"message": "Account deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to delete account"))

