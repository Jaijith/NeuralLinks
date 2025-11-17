"""
Authentication utilities
Handles user authentication and session management
"""

from fastapi import HTTPException, Request
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from core.database import get_database

db = get_database()


# User model imported from api.models
# In later phases, we'll move it to api/models/user.py


async def get_current_user(request: Request):
    """Get current authenticated user from session token
    Returns User model from api.models
    """
    # Import here to avoid circular dependency
    from api.models import User
    
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.replace("Bearer ", "")
    
    if not session_token:
        return None
    
    # Find session
    session = await db.user_sessions.find_one({"session_token": session_token})
    if not session:
        return None
    
    # Handle datetime comparison
    expires_at = session['expires_at']
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    elif not expires_at.tzinfo:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        return None
    
    # Find user
    user_doc = await db.users.find_one({"id": session['user_id']})
    if not user_doc:
        return None
    
    return User(**user_doc)


async def require_auth(request: Request):
    """Require authentication - raises HTTPException if not authenticated"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

