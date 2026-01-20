"""
Authentication Routes
"""

import os
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from core.auth import require_auth
from core.database import get_database
from core.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
from api.models import User, UserSession
from datetime import datetime, timezone, timedelta
import uuid
import random
import logging
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

db = get_database()
router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# Google OAuth scopes
GOOGLE_SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']


async def create_or_get_user(email: str, name: str, picture: str = None) -> str:
    """Helper function to create or get user, returns user_id"""
    # Check if user exists
    existing_user = await db.users.find_one({"email": email})
    
    if not existing_user:
        # Check if signup request is approved
        signup_request = await db.signup_requests.find_one(
            {"email": email},
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
        new_user_id = str(uuid.uuid4())
        
        # Generate avatar nickname with user ID for uniqueness
        avatar_prefixes = ['Cyber', 'Neon', 'Digital', 'Quantum', 'Stellar', 'Phoenix', 'Dragon', 'Storm', 
                           'Shadow', 'Crystal', 'Mystic', 'Thunder', 'Void', 'Nova', 'Cosmic', 'Plasma']
        avatar_suffixes = ['Walker', 'Rider', 'Hunter', 'Seeker', 'Warrior', 'Spirit', 'Dream', 'Star',
                           'Knight', 'Phantom', 'Blade', 'Soul', 'Wing', 'Raven', 'Wolf', 'Falcon']
        
        avatar_nickname = f"{random.choice(avatar_prefixes)}{random.choice(avatar_suffixes)}{random.randint(10, 99)}"
        avatar_picture = f"https://api.dicebear.com/7.x/adventurer/svg?seed={new_user_id}"
        
        user = User(
            id=new_user_id,
            email=email,
            name=name,
            picture=picture,
            avatar_name=avatar_nickname,
            avatar_picture=avatar_picture,
            avatar_bio="Digital warrior in the virtual realm",
            avatar_job_title="Virtual Explorer",
            avatar_location="Cyberspace",
            avatar_interests=[],
        )
        user_dict = user.model_dump()
        user_dict['created_at'] = user_dict['created_at'].isoformat()
        user_dict['profile_completed'] = True  # Mark profile as completed so user appears in search
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
        
        # Initialize state-aware agent (8 layers of autonomous behavior)
        try:
            from domain.avatar.initialization import initialize_state_aware_agent
            success = await initialize_state_aware_agent(db, user_id, name, email)
            if success:
                logger.info(f"✅ State-aware agent initialized for new user: {email}")
            else:
                logger.warning(f"⚠️  State-aware agent initialization failed for: {email}")
        except Exception as e:
            logger.error(f"State-aware agent initialization error: {str(e)}")
    else:
        user_id = existing_user['id']
        # Only update user picture if:
        # 1. User doesn't have a custom uploaded picture (local uploads contain /uploads/)
        # 2. The Google picture is different from current picture
        current_picture = existing_user.get('picture', '')
        # Check if it's a custom uploaded picture (either relative path /uploads/ or full URL containing /uploads/)
        has_custom_picture = current_picture and '/uploads/' in current_picture
        
        if picture and not has_custom_picture and current_picture != picture:
            # Only update if user doesn't have a custom uploaded picture
            await db.users.update_one(
                {"id": user_id},
                {"$set": {"picture": picture}}
            )
            logger.info(f"Updated user picture from Google for user {user_id}")
        elif has_custom_picture:
            logger.info(f"Preserving custom uploaded picture for user {user_id}: {current_picture}")
    
    return user_id


@router.get("/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth login"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    # Get redirect URL from query params or use default
    redirect_url = request.query_params.get('redirect', GOOGLE_REDIRECT_URI)
    
    # Create OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        },
        scopes=GOOGLE_SCOPES
    )
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    
    # Generate authorization URL with explicit application name
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='select_account',  # Changed from 'consent' to 'select_account' to avoid YouTube branding
        hd=None  # Don't restrict to specific domain
    )
    
    # Store state in session (you might want to use Redis or database for production)
    # For now, we'll include it in the redirect URL
    return RedirectResponse(url=authorization_url)


@router.get("/google/callback")
async def google_callback(request: Request, response: Response):
    """Handle Google OAuth callback"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    code = request.query_params.get('code')
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    try:
        # Create OAuth flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI]
                }
            },
            scopes=GOOGLE_SCOPES
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        
        # Fetch token
        flow.fetch_token(code=code)
        
        # Get user info from ID token
        credentials = flow.credentials
        idinfo = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        email = idinfo.get('email')
        name = idinfo.get('name', email.split('@')[0])
        picture = idinfo.get('picture')
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        # Create or get user
        user_id = await create_or_get_user(email, name, picture)
        
        # Generate session token
        session_token = str(uuid.uuid4())
        
        # Create session
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        session_dict = session.model_dump()
        session_dict['expires_at'] = session_dict['expires_at'].isoformat()
        session_dict['created_at'] = session_dict['created_at'].isoformat()
        await db.user_sessions.insert_one(session_dict)
        
        # Get redirect URL from query params or use default
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        redirect_url = request.query_params.get('redirect', f'{frontend_url}/home')
        
        # Determine if we're in production (HTTPS)
        is_production = frontend_url.startswith('https')
        
        # Set cookie and redirect
        response = RedirectResponse(url=redirect_url)
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,
            secure=is_production,
            samesite='lax' if is_production else 'lax',
            path='/',
            domain='.2ness.com' if is_production else None  # Allow subdomain access in production
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Google OAuth callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.get("/me")
async def get_me(request: Request):
    """Get current user with full profile data"""
    user = await require_auth(request)
    
    # Fetch full user document from database (includes autonomy fields)
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_doc


# Old Emergent session-data endpoint removed - now using Google OAuth directly


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user - doesn't require auth, just clears the cookie"""
    # Determine if we're in production
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    is_production = frontend_url.startswith('https')
    
    # Try to get session token and invalidate it in DB
    session_token = request.cookies.get("session_token")
    if session_token:
        try:
            await db.user_sessions.delete_one({"session_token": session_token})
        except Exception as e:
            logger.warning(f"Failed to delete session from DB: {e}")
    
    # Clear session token with matching cookie settings
    response.delete_cookie(
        key="session_token",
        path='/',
        domain='.2ness.com' if is_production else None
    )
    
    # Also try clearing without domain for backwards compatibility
    response.delete_cookie(key="session_token", path='/')
    
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

