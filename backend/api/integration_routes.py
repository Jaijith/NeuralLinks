"""
Integration Routes - Platform OAuth, data sync, and watch history processing
"""

from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import os
import logging
import uuid
import secrets
import json
import re
import httpx
from urllib.parse import urlencode, quote
from collections import Counter

from core.auth import require_auth
from core.database import get_database
from api.models import UserIntegration

db = get_database()
router = APIRouter(prefix="/api", tags=["integrations"])
logger = logging.getLogger(__name__)


def get_openai_client():
    """Get OpenAI client"""
    from app.globals import openai_client
    return openai_client

def get_azure_client():
    """Get OpenAI client (alias for backwards compatibility)"""
    return get_openai_client()


def get_openai_model():
    """Get OpenAI model name"""
    from app.globals import OPENAI_MODEL
    return OPENAI_MODEL  # Has default in config.py

def get_azure_deployment():
    """Get OpenAI model name (alias for backwards compatibility)"""
    return get_openai_model()


def is_responses_api_model(model: str) -> bool:
    """Check if model uses the new Responses API (gpt-5 models)"""
    return "gpt-5" in model.lower()


async def call_openai(client, model: str, prompt: str) -> str:
    """
    Call OpenAI with appropriate API based on model type.
    """
    if is_responses_api_model(model):
        # Use new responses API for gpt-5 models
        response = await client.responses.create(
            model=model,
            input=prompt
        )
        return response.output_text.strip() if response.output_text else ""
    else:
        # Use traditional Chat Completions API
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content.strip() if response.choices[0].message.content else ""


def get_graph_builder():
    """Get GraphBuilder instance"""
    from app.globals import graph_builder
    return graph_builder

@router.get("/integrations")
async def get_user_integrations(request: Request):
    """Get user's connected platform integrations"""
    user = await require_auth(request)
    
    integrations = await db.user_integrations.find(
        {"user_id": user.id},
        {"_id": 0}
    ).to_list(100)
    
    # Return with placeholder data - All major platforms
    platform_templates = {
        # Social Media - Major Platforms
        "instagram": {"icon": "📷", "name": "Instagram", "description": "Photos, stories, and interests"},
        "facebook": {"icon": "👥", "name": "Facebook", "description": "Social connections and interests"},
        "twitter": {"icon": "🐦", "name": "Twitter", "description": "Topics, trends, and interests"},
        "linkedin": {"icon": "💼", "name": "LinkedIn", "description": "Professional skills and interests"},
        "tiktok": {"icon": "🎵", "name": "TikTok", "description": "Video content and interests"},
        "snapchat": {"icon": "👻", "name": "Snapchat", "description": "Stories and interests"},
        "pinterest": {"icon": "📌", "name": "Pinterest", "description": "Boards, pins, and interests"},
        "reddit": {"icon": "🤖", "name": "Reddit", "description": "Subreddits and interests"},
        "discord": {"icon": "💬", "name": "Discord", "description": "Communities and interests"},
        "whatsapp": {"icon": "💚", "name": "WhatsApp", "description": "Messaging and contacts"},
        "telegram": {"icon": "✈️", "name": "Telegram", "description": "Groups and channels"},
        # Media & Entertainment - Major Platforms
        "spotify": {"icon": "🎵", "name": "Spotify", "description": "Music preferences and listening history"},
        "youtube": {"icon": "📺", "name": "YouTube", "description": "Video interests and subscriptions"},
        "netflix": {"icon": "🎬", "name": "Netflix", "description": "Movie and TV preferences"},
        "twitch": {"icon": "🎮", "name": "Twitch", "description": "Gaming and streaming interests"},
        "apple_music": {"icon": "🍎", "name": "Apple Music", "description": "Music library and playlists"},
        "soundcloud": {"icon": "☁️", "name": "SoundCloud", "description": "Music discovery and artists"},
        "hulu": {"icon": "🟢", "name": "Hulu", "description": "TV shows and movies"},
        "disney_plus": {"icon": "🏰", "name": "Disney+", "description": "Disney, Marvel, and Star Wars content"},
        "prime_video": {"icon": "📦", "name": "Prime Video", "description": "Movies and TV series"},
        "hbo_max": {"icon": "🎭", "name": "HBO Max", "description": "Premium TV and movies"},
        # E-commerce - Major Platforms
        "amazon": {"icon": "🛒", "name": "Amazon", "description": "Shopping preferences"},
        "ebay": {"icon": "💰", "name": "eBay", "description": "Auctions and purchases"},
        "etsy": {"icon": "🎨", "name": "Etsy", "description": "Handmade and vintage items"},
        "shopify": {"icon": "🛍️", "name": "Shopify", "description": "Online store preferences"},
        "walmart": {"icon": "🏪", "name": "Walmart", "description": "Shopping habits"},
        # Fitness & Health - Major Platforms
        "strava": {"icon": "🏃", "name": "Strava", "description": "Fitness activities"},
        "fitbit": {"icon": "⌚", "name": "Fitbit", "description": "Health and fitness tracking"},
        "myfitnesspal": {"icon": "🍎", "name": "MyFitnessPal", "description": "Nutrition and fitness"},
        "nike_run_club": {"icon": "✔️", "name": "Nike Run Club", "description": "Running activities"},
        "garmin": {"icon": "⌚", "name": "Garmin Connect", "description": "Fitness and health data"},
        # Reading & Learning - Major Platforms
        "goodreads": {"icon": "📚", "name": "Goodreads", "description": "Reading preferences"},
        "medium": {"icon": "📝", "name": "Medium", "description": "Articles and writing interests"},
        "kindle": {"icon": "📖", "name": "Kindle", "description": "E-books and reading habits"},
        "audible": {"icon": "🎧", "name": "Audible", "description": "Audiobooks and podcasts"},
        "coursera": {"icon": "🎓", "name": "Coursera", "description": "Online courses and learning"},
        "udemy": {"icon": "📚", "name": "Udemy", "description": "Skills and courses"}
    }
    
    # Create placeholder integrations
    available_platforms = []
    for platform_id, template in platform_templates.items():
        existing = next((i for i in integrations if i.get("platform_name") == platform_id), None)
        
        # For LinkedIn, only consider it connected if it has access_token (OAuth completed)
        is_connected = False
        if platform_id == "linkedin":
            is_connected = bool(existing and existing.get("access_token"))
        else:
            is_connected = bool(existing)
        
        platform_data = {
            "platform_name": platform_id,
            "connected": is_connected,
            "status": "connected" if is_connected else "available",
            **template
        }
        # For LinkedIn, include whether OAuth is completed (has access_token)
        # Don't expose the actual token, just whether it exists
        if platform_id == "linkedin" and existing:
            platform_data["access_token"] = bool(existing.get("access_token"))
        available_platforms.append(platform_data)
    
    return {"integrations": available_platforms}

@router.post("/integrations/connect")
async def connect_platform(request: Request):
    """Connect external platform - initiates OAuth flow for LinkedIn"""
    user = await require_auth(request)
    
    # Parse request body
    try:
        data = await request.json()
        logger.info(f"Received connect request data: {list(data.keys())}")
    except Exception as e:
        logger.error(f"Error parsing request body: {str(e)}")
        data = {}
    
    platform_name = data.get("platform_name")
    if not platform_name:
        raise HTTPException(status_code=400, detail="Platform name required")
    
    # For LinkedIn and YouTube, check if already connected with access_token
    if platform_name == "linkedin":
        existing = await db.user_integrations.find_one({
            "user_id": user.id,
            "platform_name": platform_name
        })
        
        # For LinkedIn, only consider it connected if it has access_token
        if existing and existing.get("access_token"):
            return {"message": "Platform already connected", "status": "connected"}
        
        # If existing but no access_token, delete it to start fresh
        if existing:
            await db.user_integrations.delete_one({"_id": existing["_id"]})
            logger.info(f"Deleted incomplete LinkedIn connection for user {user.id}, starting fresh OAuth")
    elif platform_name == "youtube":
        existing = await db.user_integrations.find_one({
            "user_id": user.id,
            "platform_name": platform_name
        })
        
        # For YouTube, only consider it connected if it has access_token
        if existing and existing.get("access_token"):
            return {"message": "Platform already connected", "status": "connected"}
        
        # If existing but no access_token, delete it to start fresh
        if existing:
            await db.user_integrations.delete_one({"_id": existing["_id"]})
            logger.info(f"Deleted incomplete YouTube connection for user {user.id}, starting fresh OAuth")
    else:
        # For other platforms, check if already connected
        existing = await db.user_integrations.find_one({
            "user_id": user.id,
            "platform_name": platform_name
        })
        
        if existing:
            return {"message": "Platform already connected", "status": "connected"}
    
    # For LinkedIn, initiate OAuth flow
    if platform_name == "linkedin":
        import os
        from urllib.parse import urlencode
        
        # LinkedIn OAuth credentials - check request body first, then environment variables
        client_id_from_request = data.get("client_id", "")
        client_secret_from_request = data.get("client_secret", "")
        
        logger.info(f"LinkedIn credentials from request - client_id: {bool(client_id_from_request)}, client_secret: {bool(client_secret_from_request)}")
        logger.info(f"Full data keys: {list(data.keys())}")
        
        # Strip whitespace if provided
        client_id = client_id_from_request.strip() if client_id_from_request else ""
        client_secret = client_secret_from_request.strip() if client_secret_from_request else ""
        
        # Fallback to environment variables if not provided in request
        if not client_id:
            client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
        if not client_secret:
            client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")
        
        # Build redirect URI - must match exactly what's in LinkedIn app settings
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8001")
        redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", f"{backend_url}/api/integrations/oauth/callback/linkedin")
        
        # Ensure no trailing slash and exact format
        redirect_uri = redirect_uri.rstrip('/')
        
        # Log for debugging
        logger.info(f"LinkedIn OAuth attempt - Final Client ID provided: {bool(client_id)}, Final Client Secret provided: {bool(client_secret)}")
        logger.info(f"Using redirect_uri: {redirect_uri}")
        
        if not client_id or not client_secret:
            # OAuth not configured - return error message instead of placeholder
            raise HTTPException(
                status_code=400,
                detail="LinkedIn OAuth not configured. Please provide Client ID and Client Secret. See https://www.linkedin.com/developers/apps to create an app."
            )
        
        # Generate state token for security
        import secrets
        state_token = secrets.token_urlsafe(32)
        
        # Store state in session/integration record (also store credentials temporarily for OAuth callback)
        integration = {
            "id": str(uuid.uuid4()),
            "user_id": user.id,
            "platform_name": platform_name,
            "platform_type": "social_media",
            "connected": False,  # Not connected yet, waiting for OAuth
            "oauth_state": state_token,
            "oauth_client_id": client_id,  # Store temporarily for callback
            "oauth_client_secret": client_secret,  # Store temporarily for callback
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.user_integrations.insert_one(integration)
        
        # LinkedIn OAuth scopes - using OpenID Connect scopes
        # These work with "Sign In with LinkedIn using OpenID Connect" product
        scopes = ["openid", "profile"]  # OAuth 2.0 scopes for OpenID Connect product
        scope_string = " ".join(scopes)
        
        # Build authorization URL
        auth_params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state_token,
            "scope": scope_string  # LinkedIn requires this parameter
        }
        auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(auth_params)}"
        
        logger.info(f"Generated LinkedIn OAuth URL with redirect_uri: {redirect_uri}")
        logger.info(f"OAuth URL generated, redirecting user to LinkedIn authorization")
        
        return {
            "message": "OAuth authorization required",
            "status": "pending",
            "auth_url": auth_url,
            "platform": platform_name,
            "redirect_uri": redirect_uri  # Include in response for debugging
        }
    
    # For YouTube, initiate OAuth flow (Google OAuth 2.0)
    if platform_name == "youtube":
        import os
        from urllib.parse import urlencode
        
        # YouTube/Google OAuth credentials - check request body first, then environment variables
        client_id_from_request = data.get("client_id", "")
        client_secret_from_request = data.get("client_secret", "")
        
        # Strip whitespace if provided
        client_id = client_id_from_request.strip() if client_id_from_request else ""
        client_secret = client_secret_from_request.strip() if client_secret_from_request else ""
        
        # Fallback to environment variables if not provided in request
        if not client_id:
            client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
        if not client_secret:
            client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
        
        # Build redirect URI
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8001")
        redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI", f"{backend_url}/api/integrations/oauth/callback/youtube")
        redirect_uri = redirect_uri.rstrip('/')
        
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=400,
                detail="YouTube OAuth not configured. Please provide Client ID and Client Secret. See https://console.cloud.google.com/apis/credentials to create OAuth credentials."
            )
        
        # Generate state token for security
        import secrets
        state_token = secrets.token_urlsafe(32)
        
        # Store state in integration record
        integration = {
            "id": str(uuid.uuid4()),
            "user_id": user.id,
            "platform_name": platform_name,
            "platform_type": "media_entertainment",
            "connected": False,
            "oauth_state": state_token,
            "oauth_client_id": client_id,
            "oauth_client_secret": client_secret,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.user_integrations.insert_one(integration)
        
        # YouTube Data API v3 scopes
        scopes = [
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl"
        ]
        scope_string = " ".join(scopes)
        
        # Build authorization URL (Google OAuth 2.0)
        auth_params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope_string,
            "state": state_token,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent"  # Force consent screen to get refresh token
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"
        
        logger.info(f"Generated YouTube OAuth URL with redirect_uri: {redirect_uri}")
        
        return {
            "message": "OAuth authorization required",
            "status": "pending",
            "auth_url": auth_url,
            "platform": platform_name,
            "redirect_uri": redirect_uri
        }
    
    # For other platforms, use placeholder for now
    platform_types = {
        "instagram": "social_media",
        "facebook": "social_media",
        "twitter": "social_media",
        "tiktok": "social_media",
        "snapchat": "social_media",
        "pinterest": "social_media",
        "reddit": "social_media",
        "discord": "social_media",
        "whatsapp": "social_media",
        "telegram": "social_media",
        "spotify": "media_entertainment",
        "youtube": "media_entertainment",
        "netflix": "media_entertainment",
        "twitch": "media_entertainment",
        "apple_music": "media_entertainment",
        "soundcloud": "media_entertainment",
        "hulu": "media_entertainment",
        "disney_plus": "media_entertainment",
        "prime_video": "media_entertainment",
        "hbo_max": "media_entertainment",
        "amazon": "ecommerce",
        "ebay": "ecommerce",
        "etsy": "ecommerce",
        "shopify": "ecommerce",
        "walmart": "ecommerce",
        "strava": "fitness_health",
        "fitbit": "fitness_health",
        "myfitnesspal": "fitness_health",
        "nike_run_club": "fitness_health",
        "garmin": "fitness_health",
        "goodreads": "reading_learning",
        "medium": "reading_learning",
        "kindle": "reading_learning",
        "audible": "reading_learning",
        "coursera": "reading_learning",
        "udemy": "reading_learning"
    }
    
    platform_type = platform_types.get(platform_name, "social_media")
    
    # Create placeholder integration
    integration = {
        "id": str(uuid.uuid4()),
        "user_id": user.id,
        "platform_name": platform_name,
        "platform_type": platform_type,
        "connected": True,
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "data_collected": 0
    }
    
    await db.user_integrations.insert_one(integration)
    
    return {
        "message": f"{platform_name} connected successfully (placeholder)",
        "status": "connected",
        "note": "OAuth integration coming soon for this platform."
    }

@router.get("/integrations/oauth/callback/linkedin")
async def linkedin_oauth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle LinkedIn OAuth callback"""
    import os
    from fastapi.responses import RedirectResponse
    
    if error:
        error_description = request.query_params.get("error_description", "")
        logger.error(f"LinkedIn OAuth error: {error} - {error_description}")
        
        # Provide helpful error message for scope errors
        if "scope" in error.lower() or "unauthorized" in error.lower():
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            # URL encode the error message
            from urllib.parse import quote
            encoded_message = quote(error_description)
            return RedirectResponse(
                url=f"{frontend_url}/settings?linkedin_error=scope&message={encoded_message}"
            )
        
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}. {error_description}")
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")
    
    # Find integration by state token
    integration = await db.user_integrations.find_one({"oauth_state": state})
    if not integration:
        raise HTTPException(status_code=400, detail="Invalid state token")
    
    user_id = integration["user_id"]
    
    # Exchange code for access token
    import os
    import base64
    
    # Get credentials from integration record (stored during connect) or environment
    client_id = integration.get("oauth_client_id") or os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret = integration.get("oauth_client_secret") or os.getenv("LINKEDIN_CLIENT_SECRET", "")
    
    # Build redirect URI - must match exactly what was used in authorization request
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8001")
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", f"{backend_url}/api/integrations/oauth/callback/linkedin")
    redirect_uri = redirect_uri.rstrip('/')  # Ensure no trailing slash
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="LinkedIn OAuth not configured")
    
    # Exchange authorization code for access token
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            token_info = token_response.json()
            access_token = token_info.get("access_token")
            
            if not access_token:
                raise HTTPException(status_code=400, detail="No access token received")
            
            # Fetch LinkedIn profile data - try OAuth 2.0 userinfo endpoint first
            logger.info("Fetching LinkedIn profile from /v2/userinfo endpoint")
            profile_response = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
            
            logger.info(f"userinfo response status: {profile_response.status_code}")
            
            # If userinfo fails, fall back to /v2/me endpoint
            if profile_response.status_code != 200:
                logger.warning(f"userinfo endpoint failed with {profile_response.status_code}, trying /v2/me")
                profile_response = await client.get(
                    "https://api.linkedin.com/v2/me"
                    "?projection=(id,localizedFirstName,localizedLastName,headline,profilePicture(displayImage~:playableStreams))",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0
                )
                logger.info(f"/v2/me response status: {profile_response.status_code}")
            
            profile_data = {}
            linkedin_id = None
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                # LinkedIn userinfo endpoint uses "sub" instead of "id"
                linkedin_id = profile_data.get("id") or profile_data.get("sub")
                logger.info(f"LinkedIn profile data received - keys: {list(profile_data.keys())}, linkedin_id: {linkedin_id}, has headline: {bool(profile_data.get('headline'))}, has summary: {bool(profile_data.get('summary'))}")
            
            # Note: Email address requires r_emailaddress scope which needs special LinkedIn approval
            # For now, we'll skip email fetching since we're using only r_liteprofile scope
            # Users can add email manually if needed
            email_data = {}
            logger.info("Skipping email fetch - r_emailaddress scope requires special LinkedIn approval")
            
            # Fetch additional data if we have LinkedIn ID
            skills_data = {}
            experience_data = {}
            education_data = {}
            activity_data = {}
            
            if linkedin_id:
                logger.info(f"Fetching additional LinkedIn data for ID: {linkedin_id}")
                # Fetch skills
                try:
                    skills_response = await client.get(
                        f"https://api.linkedin.com/v2/people/(id:{linkedin_id})/skills",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    if skills_response.status_code == 200:
                        skills_data = skills_response.json()
                        logger.info(f"LinkedIn skills data received - has elements: {bool(skills_data.get('elements'))}, count: {len(skills_data.get('elements', []))}")
                    else:
                        logger.warning(f"LinkedIn skills endpoint returned status {skills_response.status_code}")
                except Exception as e:
                    logger.warning(f"Could not fetch skills: {str(e)}")
                
                # Fetch experience/positions
                try:
                    experience_response = await client.get(
                        f"https://api.linkedin.com/v2/people/(id:{linkedin_id})/positions",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    logger.info(f"LinkedIn positions endpoint status: {experience_response.status_code}")
                    if experience_response.status_code == 200:
                        experience_data = experience_response.json()
                        logger.info(f"LinkedIn experience data received - has elements: {bool(experience_data.get('elements'))}, count: {len(experience_data.get('elements', []))}")
                    else:
                        logger.warning(f"LinkedIn positions endpoint returned {experience_response.status_code}: {experience_response.text[:200]}")
                except Exception as e:
                    logger.warning(f"Could not fetch experience: {str(e)}")
                
                # Fetch education
                try:
                    education_response = await client.get(
                        f"https://api.linkedin.com/v2/people/(id:{linkedin_id})/educations",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    logger.info(f"LinkedIn educations endpoint status: {education_response.status_code}")
                    if education_response.status_code == 200:
                        education_data = education_response.json()
                        logger.info(f"LinkedIn education data received - has elements: {bool(education_data.get('elements'))}, count: {len(education_data.get('elements', []))}")
                    else:
                        logger.warning(f"LinkedIn educations endpoint returned {education_response.status_code}: {education_response.text[:200]}")
                except Exception as e:
                    logger.warning(f"Could not fetch education: {str(e)}")
                
                # Fetch activity/posts (if available)
                try:
                    # Try to fetch recent activity - this may require additional permissions
                    activity_response = await client.get(
                        f"https://api.linkedin.com/v2/ugcPosts?authors=List({linkedin_id})&q=authors",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    if activity_response.status_code == 200:
                        activity_data = activity_response.json()
                        logger.info(f"LinkedIn activity data received - has elements: {bool(activity_data.get('elements'))}, count: {len(activity_data.get('elements', []))}")
                    else:
                        logger.warning(f"LinkedIn activity endpoint returned status {activity_response.status_code} (may require additional permissions)")
                except Exception as e:
                    logger.warning(f"Could not fetch activity: {str(e)}")
            
            # Store raw responses for debugging
            profile_data["_raw_email"] = email_data
            profile_data["_raw_skills"] = skills_data
            profile_data["_raw_experience"] = experience_data
            profile_data["_raw_education"] = education_data
            profile_data["_raw_activity"] = activity_data
            
            # Update integration with access token and mark as connected
            await db.user_integrations.update_one(
                {"id": integration["id"]},
                {
                    "$set": {
                        "connected": True,
                        "connected_at": datetime.now(timezone.utc).isoformat(),
                        "last_sync": datetime.now(timezone.utc).isoformat(),
                        "access_token": access_token,  # Store encrypted in production
                        "oauth_state": None,  # Clear state after use
                        "oauth_client_id": None,  # Clear credentials after use (security)
                        "oauth_client_secret": None,  # Clear credentials after use (security)
                        "profile_data": profile_data,  # Store profile snapshot
                        "data_collected": 0
                    }
                }
            )
            
            # Immediately sync the data
            await sync_linkedin_data(user_id, profile_data, skills_data, experience_data, education_data, activity_data, access_token)
            
            # Redirect to frontend success page
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=f"{frontend_url}/settings?linkedin=connected")
            
    except Exception as e:
        logger.error(f"LinkedIn OAuth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OAuth flow failed: {str(e)}")

@router.get("/integrations/oauth/callback/youtube")
async def youtube_oauth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle YouTube OAuth callback (Google OAuth 2.0)"""
    import os
    from fastapi.responses import RedirectResponse
    
    if error:
        error_description = request.query_params.get("error_description", "")
        logger.error(f"YouTube OAuth error: {error} - {error_description}")
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        from urllib.parse import quote
        encoded_message = quote(error_description)
        return RedirectResponse(
            url=f"{frontend_url}/settings?youtube_error=oauth&message={encoded_message}"
        )
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")
    
    # Find integration by state token
    integration = await db.user_integrations.find_one({"oauth_state": state})
    if not integration:
        raise HTTPException(status_code=400, detail="Invalid state token")
    
    user_id = integration["user_id"]
    
    # Exchange code for access token
    client_id = integration.get("oauth_client_id") or os.getenv("YOUTUBE_CLIENT_ID", "")
    client_secret = integration.get("oauth_client_secret") or os.getenv("YOUTUBE_CLIENT_SECRET", "")
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8001")
    redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI", f"{backend_url}/api/integrations/oauth/callback/youtube")
    redirect_uri = redirect_uri.rstrip('/')
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="YouTube OAuth not configured")
    
    # Exchange authorization code for access token
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"YouTube token exchange failed: {token_response.status_code} - {token_response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            token_info = token_response.json()
            access_token = token_info.get("access_token")
            refresh_token = token_info.get("refresh_token")  # Store for token refresh
            
            if not access_token:
                raise HTTPException(status_code=400, detail="No access token received")
            
            # Fetch YouTube channel data
            logger.info("Fetching YouTube channel data")
            channel_response = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={
                    "part": "snippet,contentDetails,statistics",
                    "mine": "true"
                },
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
            
            channel_data = {}
            if channel_response.status_code == 200:
                channel_result = channel_response.json()
                if channel_result.get("items"):
                    channel_data = channel_result["items"][0]
            
            # Fetch subscriptions with pagination - get ALL subscriptions
            subscriptions_data = []
            try:
                next_page_token = None
                while True:
                    params = {
                        "part": "snippet",
                        "mine": "true",
                        "maxResults": 50
                    }
                    if next_page_token:
                        params["pageToken"] = next_page_token
                    
                    subs_response = await client.get(
                        "https://www.googleapis.com/youtube/v3/subscriptions",
                        params=params,
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    if subs_response.status_code == 200:
                        subs_result = subs_response.json()
                        subscriptions_data.extend(subs_result.get("items", []))
                        next_page_token = subs_result.get("nextPageToken")
                        if not next_page_token:
                            break
                    else:
                        break
                logger.info(f"Fetched {len(subscriptions_data)} subscriptions (all pages)")
            except Exception as e:
                logger.warning(f"Could not fetch subscriptions: {str(e)}")
            
            # Fetch playlists with pagination - get ALL playlists
            playlists_data = []
            try:
                next_page_token = None
                while True:
                    params = {
                        "part": "snippet,contentDetails",
                        "mine": "true",
                        "maxResults": 50
                    }
                    if next_page_token:
                        params["pageToken"] = next_page_token
                    
                    playlists_response = await client.get(
                        "https://www.googleapis.com/youtube/v3/playlists",
                        params=params,
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    if playlists_response.status_code == 200:
                        playlists_result = playlists_response.json()
                        playlists_data.extend(playlists_result.get("items", []))
                        next_page_token = playlists_result.get("nextPageToken")
                        if not next_page_token:
                            break
                    else:
                        break
                logger.info(f"Fetched {len(playlists_data)} playlists (all pages)")
            except Exception as e:
                logger.warning(f"Could not fetch playlists: {str(e)}")
            
            # Fetch liked videos with pagination - get ALL liked videos
            liked_videos_data = []
            try:
                # Get channel ID first
                channel_id = channel_data.get("id") if channel_data else None
                if channel_id:
                    next_page_token = None
                    while True:
                        params = {
                            "part": "snippet,statistics,contentDetails",
                            "myRating": "like",
                            "maxResults": 50
                        }
                        if next_page_token:
                            params["pageToken"] = next_page_token
                        
                        liked_response = await client.get(
                            "https://www.googleapis.com/youtube/v3/videos",
                            params=params,
                            headers={"Authorization": f"Bearer {access_token}"}
                        )
                        if liked_response.status_code == 200:
                            liked_result = liked_response.json()
                            liked_videos_data.extend(liked_result.get("items", []))
                            next_page_token = liked_result.get("nextPageToken")
                            if not next_page_token:
                                break
                        else:
                            break
                    logger.info(f"Fetched {len(liked_videos_data)} liked videos (all pages)")
            except Exception as e:
                logger.warning(f"Could not fetch liked videos: {str(e)}")
            
            # Store YouTube data
            youtube_data = {
                "channel": channel_data,
                "subscriptions": subscriptions_data,
                "playlists": playlists_data,
                "liked_videos": liked_videos_data
            }
            
            # Update integration with access token and mark as connected
            # Keep client_id and client_secret for token refresh (user-provided, not sensitive)
            update_data = {
                "connected": True,
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "last_sync": datetime.now(timezone.utc).isoformat(),
                "access_token": access_token,
                "refresh_token": refresh_token,  # Store for token refresh
                "oauth_state": None,
                "profile_data": youtube_data,
                "data_collected": len(subscriptions_data) + len(playlists_data) + len(liked_videos_data)
            }
            # Keep client credentials for token refresh (don't clear them)
            # They're stored in oauth_client_id/oauth_client_secret and will be used for refresh
            
            await db.user_integrations.update_one(
                {"id": integration["id"]},
                {"$set": update_data}
            )
            
            # Immediately sync the data
            await sync_youtube_data(user_id, youtube_data, access_token)
            
            # Redirect to frontend success page
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            return RedirectResponse(url=f"{frontend_url}/settings?youtube=connected")
            
    except Exception as e:
        logger.error(f"YouTube OAuth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OAuth flow failed: {str(e)}")

async def sync_linkedin_data(user_id: str, profile_data: Dict[str, Any], skills_data: Dict[str, Any], 
                             experience_data: Dict[str, Any] = None, education_data: Dict[str, Any] = None, 
                             activity_data: Dict[str, Any] = None, access_token: str = None):
    """Sync real LinkedIn profile data to graph"""
    try:
        # Extract profession/job title
        job_title = None
        company = None
        industry = None
        
        # Extract job title from headline (common format: "Job Title at Company")
        headline = profile_data.get("headline", "")
        if headline and " at " in headline:
            parts = headline.split(" at ")
            job_title = parts[0].strip()
            company = parts[1].strip() if len(parts) > 1 else ""
        elif headline:
            # If no "at", use headline as job title
            job_title = headline.strip()
        
        # Extract skills
        skills = []
        if skills_data and skills_data.get("elements"):
            skills = [skill.get("name", "") for skill in skills_data["elements"] if skill.get("name")]
        elif isinstance(skills_data, list):
            skills = [s.get("name", "") for s in skills_data if s.get("name")]
        
        # Extract experience/positions
        experiences = []
        if experience_data and experience_data.get("elements"):
            for pos in experience_data["elements"]:
                exp = {
                    "title": pos.get("title", ""),
                    "company": pos.get("company", {}).get("name", "") if isinstance(pos.get("company"), dict) else pos.get("company", ""),
                    "start_date": pos.get("startDate", {}),
                    "end_date": pos.get("endDate", {}),
                    "description": pos.get("description", ""),
                    "location": pos.get("location", {}).get("name", "") if isinstance(pos.get("location"), dict) else pos.get("location", "")
                }
                if exp["title"]:
                    experiences.append(exp)
        
        # Extract education
        educations = []
        if education_data and education_data.get("elements"):
            for edu in education_data["elements"]:
                ed = {
                    "school": edu.get("schoolName", ""),
                    "degree": edu.get("degree", ""),
                    "field_of_study": edu.get("fieldOfStudy", ""),
                    "start_date": edu.get("startDate", {}),
                    "end_date": edu.get("endDate", {}),
                    "activities": edu.get("activities", "")
                }
                if ed["school"]:
                    educations.append(ed)
        
        # Extract activity/posts summary
        activity_summary = ""
        if activity_data and activity_data.get("elements"):
            activity_summary = f"Recent LinkedIn activity: {len(activity_data['elements'])} posts"
        
        # Build data structure for graph
        linkedin_data = {
            "skills": skills[:10],  # Top 10 skills
            "job_title": job_title or profile_data.get("job_title", "") or profile_data.get("headline", ""),
            "company": company or profile_data.get("company", ""),
            "industry": industry or profile_data.get("industry", ""),
            "headline": profile_data.get("headline", ""),
            "summary": profile_data.get("summary", ""),
            "experiences": experiences,
            "educations": educations,
            "activity_summary": activity_summary
        }
        
        logger.info(f"LinkedIn data extracted - skills: {len(linkedin_data['skills'])}, experiences: {len(experiences)}, educations: {len(educations)}, job_title: {linkedin_data['job_title']}, headline: {linkedin_data['headline']}")
        
        # Get user document
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user_doc:
            return
        
        profile_updates = {}
        
        # Update job title if we have it
        if linkedin_data.get("job_title") and not user_doc.get("job_title"):
            profile_updates["job_title"] = linkedin_data["job_title"]
        
        # Add skills as interests
        if linkedin_data.get("skills"):
            current_interests = user_doc.get("interests", []) or []
            skill_interests = [skill.lower() for skill in linkedin_data["skills"][:5] if skill]
            profile_updates["interests"] = list(set(current_interests + skill_interests))
        
        # Update profile
        if profile_updates:
            await db.users.update_one(
                {"id": user_id},
                {"$set": profile_updates}
            )
            logger.info(f"Updated profile for user {user_id} from LinkedIn")
        
        # Add to Graph RAG
        result = await get_graph_builder().add_external_platform_data(
            user_id, "linkedin", linkedin_data
        )
        
        # Create profession node if we have job title
        if linkedin_data.get("job_title"):
            profession_node = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "node_type": "preference",
                "label": f"profession:{linkedin_data['job_title'].lower().replace(' ', '_')}",
                "properties": {
                    "source": "linkedin",
                    "category": "profession",
                    "strength": 1.0,
                    "job_title": linkedin_data["job_title"],
                    "company": linkedin_data.get("company", "")
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            existing = await db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": "preference",
                "label": profession_node["label"]
            })
            if not existing:
                await db.graph_nodes.insert_one(profession_node)
                result["nodes_created"] += 1
        
        # Create experience nodes
        for exp in linkedin_data.get("experiences", []):
            if exp.get("title"):
                exp_label = f"experience:{exp['title'].lower().replace(' ', '_')}"
                existing = await db.graph_nodes.find_one({
                    "user_id": user_id,
                    "node_type": "experience",
                    "label": exp_label
                })
                if not existing:
                    exp_node = {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "node_type": "experience",
                        "label": exp_label,
                        "properties": {
                            "source": "linkedin",
                            "title": exp["title"],
                            "company": exp.get("company", ""),
                            "location": exp.get("location", ""),
                            "start_date": str(exp.get("start_date", "")),
                            "end_date": str(exp.get("end_date", "")),
                            "description": exp.get("description", "")[:500]  # Limit description length
                        },
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                    await db.graph_nodes.insert_one(exp_node)
                    result["nodes_created"] += 1
                    logger.info(f"Created experience node: {exp['title']} at {exp.get('company', 'Unknown')}")
        
        # Create education nodes
        for edu in linkedin_data.get("educations", []):
            if edu.get("school"):
                edu_label = f"education:{edu['school'].lower().replace(' ', '_')}"
                existing = await db.graph_nodes.find_one({
                    "user_id": user_id,
                    "node_type": "experience",  # Education is also an experience type
                    "label": edu_label
                })
                if not existing:
                    edu_node = {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "node_type": "experience",
                        "label": edu_label,
                        "properties": {
                            "source": "linkedin",
                            "category": "education",
                            "school": edu["school"],
                            "degree": edu.get("degree", ""),
                            "field_of_study": edu.get("field_of_study", ""),
                            "start_date": str(edu.get("start_date", "")),
                            "end_date": str(edu.get("end_date", ""))
                        },
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                    await db.graph_nodes.insert_one(edu_node)
                    result["nodes_created"] += 1
                    logger.info(f"Created education node: {edu['school']} - {edu.get('degree', '')}")
        
        # Use LLM to extract additional entities from profile summary/headline
        if get_azure_client() and (linkedin_data.get("summary") or linkedin_data.get("headline")):
            try:
                profile_text = f"LinkedIn Profile:\nHeadline: {linkedin_data.get('headline', '')}\nSummary: {linkedin_data.get('summary', '')}"
                extracted_nodes = await get_graph_builder().extract_entities_from_text(
                    profile_text,
                    user_id
                )
                for node in extracted_nodes:
                    node["properties"]["source"] = "linkedin"
                    existing = await db.graph_nodes.find_one({
                        "user_id": user_id,
                        "node_type": node["node_type"],
                        "label": node["label"]
                    })
                    if not existing:
                        await db.graph_nodes.insert_one(node)
                        result["nodes_created"] += 1
            except Exception as e:
                logger.error(f"Error extracting entities from LinkedIn profile: {str(e)}")
        
        # Update integration sync time
        integration = await db.user_integrations.find_one({"user_id": user_id, "platform_name": "linkedin"})
        if integration:
            await db.user_integrations.update_one(
                {"id": integration["id"]},
                {
                    "$set": {
                        "last_sync": datetime.now(timezone.utc).isoformat(),
                        "data_collected": result["nodes_created"]
                    }
                }
            )
        
        logger.info(f"Synced LinkedIn data for user {user_id}: {result['nodes_created']} nodes created")
        
    except Exception as e:
        logger.error(f"Error syncing LinkedIn data: {str(e)}")
        raise

async def sync_youtube_data(user_id: str, youtube_data: Dict[str, Any], access_token: str = None):
    """Sync YouTube data to graph - subscriptions, playlists, liked videos, watch history with LLM analysis"""
    try:
        # Extract channel info
        channel = youtube_data.get("channel", {})
        channel_title = channel.get("snippet", {}).get("title", "") if channel else ""
        channel_id = channel.get("id", "") if channel else ""
        
        # Extract subscriptions (channels user follows) - process ALL subscriptions
        subscriptions = youtube_data.get("subscriptions", [])
        subscription_channels = []
        for sub in subscriptions:  # Process all subscriptions
            channel_name = sub.get("snippet", {}).get("title", "")
            if channel_name:
                subscription_channels.append(channel_name)
        
        # Extract playlists - process ALL playlists
        playlists = youtube_data.get("playlists", [])
        playlist_names = []
        for playlist in playlists:  # Process all playlists
            playlist_title = playlist.get("snippet", {}).get("title", "")
            if playlist_title:
                playlist_names.append(playlist_title)
        
        # Extract liked videos (these represent watch history preferences) - process ALL liked videos
        liked_videos = youtube_data.get("liked_videos", [])
        liked_video_topics = []
        watch_history_summary = []  # For LLM analysis
        for video in liked_videos:  # Process all liked videos
            snippet = video.get("snippet", {})
            title = snippet.get("title", "")
            description = snippet.get("description", "")[:200]  # First 200 chars
            category = snippet.get("categoryId", "")
            tags = snippet.get("tags", [])
            channel_title_vid = snippet.get("channelTitle", "")
            published_at = snippet.get("publishedAt", "")
            
            if title:
                liked_video_topics.append({
                    "title": title,
                    "category": category,
                    "tags": tags[:5],  # Limit tags
                    "channel": channel_title_vid,
                    "description": description,
                    "published_at": published_at
                })
                # Build summary for LLM
                watch_history_summary.append(f"Video: {title} | Channel: {channel_title_vid} | Tags: {', '.join(tags[:3])}")
        
        # Extract activity data if provided (recent watch history)
        recent_watch_history = []
        activity_data = youtube_data.get("activity", [])
        logger.info(f"Processing {len(activity_data)} activity items from YouTube data")
        
        for activity in activity_data:
            snippet = activity.get("snippet", {})
            activity_type = snippet.get("type", "unknown")
            logger.debug(f"Activity type: {activity_type}, title: {snippet.get('title', 'N/A')}")
            
            # Include all activity types that might indicate watch history
            # YouTube activities can be: upload, recommendation, bulletin, channelItem, comment, favorite, like, playlistItem, promotedItem, social, subscription
            if activity_type in ["upload", "recommendation", "bulletin", "channelItem", "favorite", "like", "playlistItem"]:
                title = snippet.get("title", "")
                channel_name = snippet.get("channelTitle", "")
                published = snippet.get("publishedAt", "")
                if title:
                    recent_watch_history.append({
                        "title": title,
                        "channel": channel_name,
                        "watched_at": published,
                        "type": activity_type
                    })
                    logger.debug(f"Added to watch history: {title[:50]}... from {channel_name}")
        
        logger.info(f"Extracted {len(recent_watch_history)} items from activity data")
        
        # Also try to fetch activity feed if access_token provided and no activity data
        if access_token and not activity_data:
            logger.info("No activity data provided, attempting to fetch from YouTube API")
            try:
                async with httpx.AsyncClient() as client:
                    # Try to get activity feed with pagination - get ALL activities
                    next_page_token = None
                    total_activities_fetched = 0
                    
                    while True:
                        params = {
                            "part": "snippet,contentDetails",
                            "mine": "true",
                            "maxResults": 50
                        }
                        if next_page_token:
                            params["pageToken"] = next_page_token
                        
                        activity_response = await client.get(
                            "https://www.googleapis.com/youtube/v3/activities",
                            params=params,
                            headers={"Authorization": f"Bearer {access_token}"},
                            timeout=10.0
                        )
                        
                        if activity_response.status_code == 200:
                            activity_result = activity_response.json()
                            activities = activity_result.get("items", [])
                            total_activities_fetched += len(activities)
                            
                            logger.info(f"Fetched {len(activities)} activities from YouTube API (page)")
                            
                            for activity in activities:
                                snippet = activity.get("snippet", {})
                                activity_type = snippet.get("type", "unknown")
                                
                                # Log all activity types for debugging
                                if activity_type in ["upload", "recommendation", "bulletin", "channelItem", "favorite", "like", "playlistItem"]:
                                    title = snippet.get("title", "")
                                    channel_name = snippet.get("channelTitle", "")
                                    published = snippet.get("publishedAt", "")
                                    if title:
                                        recent_watch_history.append({
                                            "title": title,
                                            "channel": channel_name,
                                            "watched_at": published,
                                            "type": activity_type
                                        })
                            
                            next_page_token = activity_result.get("nextPageToken")
                            if not next_page_token:
                                break
                        elif activity_response.status_code == 403:
                            logger.warning("YouTube Activities API returned 403 - may require additional permissions or may not be available")
                            break
                        else:
                            logger.warning(f"YouTube Activities API returned status {activity_response.status_code}: {activity_response.text[:200]}")
                            break
                    
                    logger.info(f"Total activities fetched from API: {total_activities_fetched}, watch history items extracted: {len(recent_watch_history)}")
            except Exception as e:
                logger.error(f"Error fetching activity feed: {str(e)}", exc_info=True)
        
        # Combine all data for watch history tracking - store ALL watch history
        all_watch_data = liked_video_topics + recent_watch_history
        
        logger.info(f"=== YouTube Data Extraction Summary ===")
        logger.info(f"Subscriptions: {len(subscription_channels)}")
        logger.info(f"Playlists: {len(playlist_names)}")
        logger.info(f"Liked videos (used as watch history proxy): {len(liked_video_topics)}")
        logger.info(f"Activity feed items (recent watch history): {len(recent_watch_history)}")
        logger.info(f"Total watch history items to store: {len(all_watch_data)}")
        
        # Log sample of watch history for verification
        if liked_video_topics:
            logger.info(f"Sample liked videos (first 5): {[v.get('title', 'N/A')[:50] for v in liked_video_topics[:5]]}")
        if recent_watch_history:
            logger.info(f"Sample activity items (first 5): {[v.get('title', 'N/A')[:50] for v in recent_watch_history[:5]]}")
        
        # Get user document
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user_doc:
            return
        
        result = {"nodes_created": 0}
        
        # ========== STEP 1: Use LLM to analyze watch history and derive character traits ==========
        character_traits_from_llm = []
        logger.info(f"LLM Analysis Check - get_openai_client() available: {get_openai_client() is not None}, watch_history_summary length: {len(watch_history_summary)}")
        logger.info(f"Watch history summary sample (first 3): {watch_history_summary[:3] if watch_history_summary else 'NONE'}")
        
        if not get_openai_client():
            logger.warning("OpenAI client not available - LLM analysis will be skipped. Check OPENAI_API_KEY environment variable.")
        
        if get_openai_client() and watch_history_summary:
            try:
                # Prepare comprehensive watch history text for LLM analysis
                # Use up to 200 items for LLM (to stay within token limits) but analyze all patterns
                # For better analysis, we'll use a representative sample if there are too many
                max_llm_items = 200
                if len(watch_history_summary) > max_llm_items:
                    # Use first 100 and last 100 to get both recent and historical patterns
                    watch_history_text = "\n".join(
                        watch_history_summary[:max_llm_items//2] + 
                        watch_history_summary[-max_llm_items//2:]
                    )
                else:
                    watch_history_text = "\n".join(watch_history_summary)
                
                # Include all subscriptions and playlists in LLM analysis (they're usually not too many)
                subscriptions_text = ", ".join(subscription_channels)
                playlists_text = ", ".join(playlist_names)
                
                llm_prompt = f"""Analyze this user's YouTube watch history and viewing patterns to derive their DEEP PERSONALITY TRAITS, CORE VALUES, and THEMATIC INTERESTS.

Subscriptions (channels they follow): {subscriptions_text}
Playlists: {playlists_text}
Watch History (liked videos and recent activity):
{watch_history_text}

CRITICAL INSTRUCTIONS:
1. **Personality Traits**: Derive personality traits from viewing patterns. For example:
   - Watching "journey of purpose", spiritual content → traits: "spiritual", "philosophical", "introspective", "mindful"
   - Watching educational content → traits: "curious", "analytical", "intellectual", "lifelong learner"
   - Watching music/soundtracks → traits: "artistic", "emotionally expressive", "aesthetically inclined"
   - Watching comedy/entertainment → traits: "humorous", "lighthearted", "social", "entertainment-seeking"

2. **Core Values**: Identify what the user values based on content choices:
   - Spiritual/philosophical content → values: "spirituality", "self-discovery", "meaning", "wisdom"
   - Educational content → values: "knowledge", "growth", "learning", "intellectual development"
   - Music/arts → values: "beauty", "creativity", "emotional expression", "artistic appreciation"

3. **Thematic Interests (NOT individual videos)**: Identify BROAD themes and genres, not specific videos:
   - Aggregate similar content into categories (e.g., "Spiritual Content", "Philosophy", "Film Soundtracks", "Educational Mathematics")
   - Only include interests that appear frequently or are clearly a pattern
   - DO NOT list individual video titles or channel names as interests

4. **Frequency Analysis**: Focus on patterns that appear multiple times, not one-off videos.

Return ONLY a JSON array with entities in this exact format:
[
  {{"type": "trait", "label": "spiritual", "properties": {{"confidence": 0.9, "evidence": "frequently watches journey of purpose and philosophical content"}}}},
  {{"type": "trait", "label": "philosophical", "properties": {{"confidence": 0.85, "evidence": "engages with deep thinking and purpose-driven content"}}}},
  {{"type": "value", "label": "spirituality", "properties": {{"importance": "high", "evidence": "consistent viewing of spiritual and philosophical channels"}}}},
  {{"type": "value", "label": "self-discovery", "properties": {{"importance": "high", "evidence": "watches content about personal growth and purpose"}}}},
  {{"type": "interest", "label": "spiritual content", "properties": {{"intensity": "high", "evidence": "frequent engagement with spiritual channels"}}}},
  {{"type": "interest", "label": "film soundtracks", "properties": {{"intensity": "medium", "evidence": "watches movie soundtracks like Dune and Hans Zimmer"}}}}
]

Entity types: trait, value, interest
- Focus on PERSONALITY INSIGHTS, not just content topics
- Aggregate into themes/genres, not individual items
- Only include traits/values/interests with strong evidence from viewing patterns
- Minimum 5 traits, 3 values, 3-5 thematic interests
Return ONLY the JSON array, no explanation."""

                logger.info("Sending YouTube watch history to LLM for character analysis")
                content = await call_openai(get_azure_client(), get_azure_deployment(), llm_prompt)
                
                # Extract JSON from response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                character_traits_from_llm = json.loads(content)
                logger.info(f"LLM extracted {len(character_traits_from_llm)} character traits/values/interests from YouTube watch history")
                logger.info(f"LLM analysis results: {json.dumps(character_traits_from_llm[:5], indent=2)}")  # Log first 5 for debugging
                
                # Create graph nodes from LLM analysis
                for entity in character_traits_from_llm:
                    node_type = entity.get("type", "interest")
                    label = entity.get("label", "").lower()
                    properties = entity.get("properties", {})
                    
                    if not label:
                        continue
                    
                    # Create proper label format
                    if node_type == "trait":
                        node_label = f"trait:{label}"
                    elif node_type == "value":
                        node_label = f"value:{label}"
                    else:
                        node_label = f"interest:{label}"
                    
                    # Check if node already exists
                    existing = await db.graph_nodes.find_one({
                        "user_id": user_id,
                        "node_type": node_type,
                        "label": node_label
                    })
                    
                    if not existing:
                        node = {
                            "id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "node_type": node_type,
                            "label": node_label,
                            "properties": {
                                **properties,
                                "source": "youtube",
                                "service": "llm_analysis",
                                "derived_from": "watch_history_analysis",
                                "strength": float(properties.get("confidence", properties.get("importance", 0.8))) if isinstance(properties.get("confidence", properties.get("importance", 0.8)), (int, float)) else 0.8
                            },
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                        await db.graph_nodes.insert_one(node)
                        result["nodes_created"] += 1
                    else:
                        # Update existing node with new evidence
                        await db.graph_nodes.update_one(
                            {"id": existing["id"]},
                            {
                                "$set": {
                                    "properties.source": "youtube",
                                    "properties.service": "llm_analysis",
                                    "properties.derived_from": "watch_history_analysis",
                                    "updated_at": datetime.now(timezone.utc).isoformat()
                                }
                            }
                        )
                
            except Exception as e:
                logger.error(f"Error in LLM analysis of YouTube watch history: {str(e)}")
                logger.error(f"LLM response content: {content[:500] if 'content' in locals() else 'N/A'}")
        
        # ========== STEP 2: Aggregate watch history by genre/category (NOT individual videos) ==========
        # Analyze watch history to identify frequent genres/categories, NOT individual videos
        from collections import Counter
        
        # Aggregate by category/genre
        category_frequency = Counter()
        channel_frequency = Counter()
        tag_frequency = Counter()
        
        for watch_item in all_watch_data:
            category = watch_item.get("category", "")
            channel = watch_item.get("channel", "")
            tags = watch_item.get("tags", [])
            
            if category:
                category_frequency[category] += 1
            if channel:
                channel_frequency[channel.lower()] += 1
            for tag in tags[:3]:
                tag_frequency[tag.lower()] += 1
        
        # Only create interest nodes for frequently watched categories/genres (minimum 3 occurrences)
        MIN_FREQUENCY = 3
        frequent_categories = {cat: count for cat, count in category_frequency.items() if count >= MIN_FREQUENCY}
        frequent_channels = {ch: count for ch, count in channel_frequency.items() if count >= MIN_FREQUENCY}
        frequent_tags = {tag: count for tag, count in tag_frequency.items() if count >= MIN_FREQUENCY}
        
        logger.info(f"Aggregated watch history - Frequent categories: {len(frequent_categories)}, channels: {len(frequent_channels)}, tags: {len(frequent_tags)}")
        
        # Create interest nodes only for frequent patterns (not individual videos)
        aggregated_interests_created = 0
        for category, count in frequent_categories.items():
            category_label = f"interest:youtube_category_{category.lower().replace(' ', '_')}"
            existing = await db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": "interest",
                "label": category_label
            })
            if not existing:
                category_node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "interest",
                    "label": category_label,
                    "properties": {
                        "source": "youtube",
                        "service": "watch_history",
                        "category": "watch_history_genre",
                        "genre": category,
                        "watch_count": count,
                        "strength": min(count / 10.0, 1.0)  # Normalize based on frequency
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await db.graph_nodes.insert_one(category_node)
                result["nodes_created"] += 1
                aggregated_interests_created += 1
        
        logger.info(f"Created {aggregated_interests_created} aggregated genre/category interest nodes (filtered by frequency >= {MIN_FREQUENCY})")
        
        # ========== STEP 3: Create traditional interest nodes from subscriptions/playlists ==========
        # Build data structure for graph
        youtube_graph_data = {
            "channel_title": channel_title,
            "subscriptions": subscription_channels,
            "playlists": playlist_names,
            "liked_videos": liked_video_topics
        }
        
        # Add to Graph RAG (traditional method)
        graph_result = await get_graph_builder().add_external_platform_data(
            user_id, "youtube", youtube_graph_data
        )
        result["nodes_created"] += graph_result.get("nodes_created", 0)
        
        # Create interest nodes for subscriptions - create nodes for ALL subscriptions
        for sub in subscription_channels:  # All subscriptions
            sub_label = f"interest:youtube_channel_{sub.lower().replace(' ', '_').replace('-', '_')}"
            existing = await db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": "interest",
                "label": sub_label
            })
            if not existing:
                sub_node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "interest",
                    "label": sub_label,
                    "properties": {
                        "source": "youtube",
                        "service": "subscriptions",
                        "category": "subscription",
                        "channel_name": sub,
                        "strength": 1.0
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await db.graph_nodes.insert_one(sub_node)
                result["nodes_created"] += 1
        
        # Create preference nodes for playlists - create nodes for ALL playlists
        for playlist in playlist_names:  # All playlists
            playlist_label = f"preference:youtube_playlist_{playlist.lower().replace(' ', '_').replace('-', '_')}"
            existing = await db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": "preference",
                "label": playlist_label
            })
            if not existing:
                playlist_node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "preference",
                    "label": playlist_label,
                    "properties": {
                        "source": "youtube",
                        "service": "playlists",
                        "category": "playlist",
                        "playlist_name": playlist,
                        "strength": 1.0
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await db.graph_nodes.insert_one(playlist_node)
                result["nodes_created"] += 1
        
        # Aggregate liked video topics by frequency - only create nodes for frequent patterns
        from collections import Counter
        liked_video_categories = Counter()
        liked_video_tags = Counter()
        
        for video in liked_video_topics:
            category = video.get("category", "")
            tags = video.get("tags", [])
            if category:
                liked_video_categories[category] += 1
            for tag in tags[:3]:  # Top 3 tags per video
                tag_lower = tag.lower().replace(" ", "_")
                liked_video_tags[tag_lower] += 1
        
        # Only create nodes for frequently liked categories/tags (minimum 2 occurrences for liked videos)
        MIN_LIKED_FREQUENCY = 2
        frequent_liked_categories = {cat: count for cat, count in liked_video_categories.items() if count >= MIN_LIKED_FREQUENCY}
        frequent_liked_tags = {tag: count for tag, count in liked_video_tags.items() if count >= MIN_LIKED_FREQUENCY}
        
        logger.info(f"Liked videos aggregated - Frequent categories: {len(frequent_liked_categories)}, tags: {len(frequent_liked_tags)}")
        
        # Create nodes only for frequent patterns
        for category, count in sorted(frequent_liked_categories.items(), key=lambda x: x[1], reverse=True):
            category_label = f"interest:youtube_liked_{category}"
            existing = await db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": "interest",
                "label": category_label
            })
            if not existing:
                category_node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "interest",
                    "label": category_label,
                    "properties": {
                        "source": "youtube",
                        "service": "liked_videos",
                        "category": "liked_video_genre",
                        "genre": category,
                        "like_count": count,
                        "strength": min(count / 5.0, 1.0)  # Normalize strength based on frequency
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await db.graph_nodes.insert_one(category_node)
                result["nodes_created"] += 1
        
        # ========== STEP 4: Update user profile based on LLM analysis ==========
        profile_updates = {}
        current_interests = user_doc.get("interests", []) or []
        youtube_interests = []
        
        # Add interests from LLM analysis - include ALL
        for entity in character_traits_from_llm:
            if entity.get("type") == "interest":
                interest_label = entity.get("label", "").lower().replace(" ", "_")
                if interest_label and interest_label not in current_interests:
                    youtube_interests.append(interest_label)
        
        # Also add subscription channel names as interests - include ALL subscriptions
        for sub in subscription_channels:  # All subscriptions
            interest_key = sub.lower().replace(" ", "_")
            if interest_key not in current_interests:
                youtube_interests.append(interest_key)
        
        # Add playlist names as interests - include ALL playlists
        for playlist in playlist_names:  # All playlists
            interest_key = playlist.lower().replace(" ", "_")
            if interest_key not in current_interests:
                youtube_interests.append(interest_key)
        
        if youtube_interests:
            profile_updates["interests"] = list(set(current_interests + youtube_interests))
        
        # Update profile
        if profile_updates:
            await db.users.update_one(
                {"id": user_id},
                {"$set": profile_updates}
            )
            logger.info(f"Updated profile for user {user_id} from YouTube (including LLM-derived traits)")
        
        # Update integration sync time
        integration = await db.user_integrations.find_one({"user_id": user_id, "platform_name": "youtube"})
        if integration:
            await db.user_integrations.update_one(
                {"id": integration["id"]},
                {
                    "$set": {
                        "last_sync": datetime.now(timezone.utc).isoformat(),
                        "data_collected": result["nodes_created"],
                        "llm_analysis_performed": True,
                        "watch_history_tracked": len(all_watch_data)
                    }
                }
            )
        
        logger.info(f"=== YouTube Sync Complete ===")
        logger.info(f"Total nodes created: {result['nodes_created']}")
        logger.info(f"  - LLM-derived traits/values/interests: {len(character_traits_from_llm)}")
        logger.info(f"  - Aggregated genre/category interests: {aggregated_interests_created}")
        logger.info(f"  - Subscription nodes: {len(subscription_channels)}")
        logger.info(f"  - Playlist nodes: {len(playlist_names)}")
        logger.info(f"Watch history items processed: {len(all_watch_data)} (liked videos: {len(liked_video_topics)}, activity: {len(recent_watch_history)})")
        
        # Log breakdown of LLM analysis results
        if character_traits_from_llm:
            traits_count = sum(1 for e in character_traits_from_llm if e.get("type") == "trait")
            values_count = sum(1 for e in character_traits_from_llm if e.get("type") == "value")
            interests_count = sum(1 for e in character_traits_from_llm if e.get("type") == "interest")
            logger.info(f"LLM Analysis Breakdown - Traits: {traits_count}, Values: {values_count}, Thematic Interests: {interests_count}")
        
    except Exception as e:
        logger.error(f"Error syncing YouTube data: {str(e)}")
        raise

async def process_youtube_watch_history(user_id: str, watch_history_data: List[Dict[str, Any]]):
    """Process YouTube Takeout watch history JSON and create knowledge graph nodes"""
    import re
    from collections import Counter
    
    try:
        logger.info(f"Processing {len(watch_history_data)} watch history entries for user {user_id}")
        
        # Extract video data from Takeout format
        video_entries = []
        for item in watch_history_data:
            url = item.get("titleUrl") or item.get("titleUrl".capitalize())
            time = item.get("time")
            title = item.get("title", "")
            channel_name = None
            if item.get("subtitles"):
                channel_name = item.get("subtitles")[0].get("name") if isinstance(item.get("subtitles"), list) else None
            
            if url and "watch?v=" in url:
                video_id_match = re.search(r"v=([A-Za-z0-9_-]{11})", url)
                if video_id_match:
                    video_id = video_id_match.group(1)
                    video_entries.append({
                        "watched_at": time,
                        "videoId": video_id,
                        "title": title,
                        "channel_name": channel_name,
                        "url": url
                    })
        
        logger.info(f"Extracted {len(video_entries)} valid video entries from watch history")
        
        if not video_entries:
            return {"nodes_created": 0, "message": "No valid video entries found in watch history"}
        
        # Enrich with YouTube Data API if available
        integration = await db.user_integrations.find_one({"user_id": user_id, "platform_name": "youtube"})
        access_token = integration.get("access_token") if integration else None
        
        enriched_videos = []
        if access_token:
            # Fetch video metadata in batches of 50 (YouTube API limit)
            video_ids = [v["videoId"] for v in video_entries[:500]]  # Limit to 500 for processing
            async with httpx.AsyncClient() as client:
                for i in range(0, len(video_ids), 50):
                    batch = video_ids[i:i+50]
                    try:
                        response = await client.get(
                            "https://www.googleapis.com/youtube/v3/videos",
                            params={
                                "part": "snippet,statistics,contentDetails",
                                "id": ",".join(batch)
                            },
                            headers={"Authorization": f"Bearer {access_token}"},
                            timeout=10.0
                        )
                        if response.status_code == 200:
                            result = response.json()
                            for video in result.get("items", []):
                                enriched_videos.append({
                                    "videoId": video["id"],
                                    "title": video.get("snippet", {}).get("title", ""),
                                    "channel_title": video.get("snippet", {}).get("channelTitle", ""),
                                    "category_id": video.get("snippet", {}).get("categoryId", ""),
                                    "tags": video.get("snippet", {}).get("tags", [])[:5],
                                    "description": video.get("snippet", {}).get("description", "")[:200]
                                })
                    except Exception as e:
                        logger.warning(f"Error enriching batch {i}: {str(e)}")
                        continue
        
        # Create a mapping of videoId to enriched data
        enriched_map = {v["videoId"]: v for v in enriched_videos}
        
        # Analyze watch patterns to extract interests
        channel_counter = Counter()
        category_counter = Counter()
        tag_counter = Counter()
        topic_keywords = []
        
        for entry in video_entries[:500]:  # Process top 500
            video_id = entry.get("videoId")
            channel_name = entry.get("channel_name", "")
            
            # Count channels
            if channel_name:
                channel_counter[channel_name.lower()] += 1
            
            # Get enriched data if available
            if video_id in enriched_map:
                enriched = enriched_map[video_id]
                category_id = enriched.get("category_id", "")
                tags = enriched.get("tags", [])
                title = enriched.get("title", "")
                
                if category_id:
                    category_counter[category_id] += 1
                
                for tag in tags:
                    tag_lower = tag.lower().replace(" ", "_")
                    tag_counter[tag_lower] += 1
                
                # Extract keywords from title
                if title:
                    words = title.lower().split()
                    topic_keywords.extend([w for w in words if len(w) > 3])
        
        # Get top interests
        top_channels = [ch for ch, count in channel_counter.most_common(20)]
        top_categories = [cat for cat, count in category_counter.most_common(10)]
        top_tags = [tag for tag, count in tag_counter.most_common(30)]
        top_keywords = Counter(topic_keywords).most_common(20)
        
        logger.info(f"Extracted interests - channels: {len(top_channels)}, categories: {len(top_categories)}, tags: {len(top_tags)}")
        
        # Create nodes in knowledge graph
        nodes_created = 0
        
        # Create interest nodes for top watched channels
        for channel in top_channels:
            channel_label = f"interest:youtube_watch_channel_{channel.lower().replace(' ', '_').replace('-', '_')}"
            existing = await db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": "interest",
                "label": channel_label
            })
            if not existing:
                strength = min(channel_counter[channel] / 10.0, 1.0)  # Normalize based on watch count
                channel_node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "interest",
                    "label": channel_label,
                    "properties": {
                        "source": "youtube",
                        "service": "watch_history_upload",
                        "category": "watched_channel",
                        "channel_name": channel,
                        "watch_count": channel_counter[channel],
                        "strength": strength
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await db.graph_nodes.insert_one(channel_node)
                nodes_created += 1
        
        # Create interest nodes for video categories
        category_names = {
            "1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music",
            "15": "Pets & Animals", "17": "Sports", "19": "Travel & Events",
            "20": "Gaming", "22": "People & Blogs", "23": "Comedy",
            "24": "Entertainment", "25": "News & Politics", "26": "Howto & Style",
            "27": "Education", "28": "Science & Technology"
        }
        
        for category_id in top_categories:
            category_name = category_names.get(category_id, f"Category_{category_id}")
            category_label = f"interest:youtube_category_{category_name.lower().replace(' ', '_').replace('&', 'and')}"
            existing = await db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": "interest",
                "label": category_label
            })
            if not existing:
                strength = min(category_counter[category_id] / 5.0, 1.0)
                category_node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "interest",
                    "label": category_label,
                    "properties": {
                        "source": "youtube",
                        "service": "watch_history_upload",
                        "category": "video_category",
                        "category_name": category_name,
                        "category_id": category_id,
                        "watch_count": category_counter[category_id],
                        "strength": strength
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await db.graph_nodes.insert_one(category_node)
                nodes_created += 1
        
        # Create interest nodes for top tags
        for tag, count in top_tags[:20]:  # Top 20 tags
            tag_label = f"interest:youtube_tag_{tag}"
            existing = await db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": "interest",
                "label": tag_label
            })
            if not existing:
                strength = min(count / 5.0, 1.0)
                tag_node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "interest",
                    "label": tag_label,
                    "properties": {
                        "source": "youtube",
                        "service": "watch_history_upload",
                        "category": "video_tag",
                        "tag": tag,
                        "watch_count": count,
                        "strength": strength
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await db.graph_nodes.insert_one(tag_node)
                nodes_created += 1
        
        # Update user interests in profile
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user_doc:
            current_interests = user_doc.get("interests", []) or []
            new_interests = []
            
            # Add top channels as interests
            for channel in top_channels[:10]:
                interest_key = channel.lower().replace(" ", "_")
                if interest_key not in current_interests:
                    new_interests.append(interest_key)
            
            # Add top categories as interests
            for category_id in top_categories[:5]:
                category_name = category_names.get(category_id, "")
                if category_name:
                    interest_key = category_name.lower().replace(" ", "_").replace("&", "and")
                    if interest_key not in current_interests:
                        new_interests.append(interest_key)
            
            if new_interests:
                await db.users.update_one(
                    {"id": user_id},
                    {"$set": {"interests": list(set(current_interests + new_interests))}}
                )
                logger.info(f"Updated user {user_id} interests from watch history")
        
        # Update integration with watch history stats
        if integration:
            await db.user_integrations.update_one(
                {"id": integration["id"]},
                {
                    "$set": {
                        "watch_history_processed": True,
                        "watch_history_entries": len(video_entries),
                        "watch_history_processed_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
        
        logger.info(f"Processed YouTube watch history for user {user_id}: {nodes_created} nodes created")
        return {"nodes_created": nodes_created, "entries_processed": len(video_entries)}
        
    except Exception as e:
        logger.error(f"Error processing YouTube watch history: {str(e)}")
        raise

@router.get("/integrations/youtube/watch-history-status")
async def get_youtube_watch_history_status(request: Request):
    """Get status of YouTube watch history data - what we have stored"""
    user = await require_auth(request)
    
    # Check if YouTube is connected
    integration = await db.user_integrations.find_one({
        "user_id": user.id,
        "platform_name": "youtube"
    })
    
    if not integration:
        raise HTTPException(status_code=404, detail="YouTube not connected")
    
    # Count watch history nodes (from uploaded Takeout data)
    watch_history_count = await db.graph_nodes.count_documents({
        "user_id": user.id,
        "node_type": "preference",
        "properties.source": "youtube",
        "properties.service": "watch_history_upload"
    })
    
    # Get sample watch history items
    watch_history_samples = await db.graph_nodes.find(
        {
            "user_id": user.id,
            "node_type": "preference",
            "properties.source": "youtube",
            "properties.service": "watch_history_upload"
        },
        {"properties.video_title": 1, "properties.channel": 1, "properties.watched_at": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    # Count liked videos (used as watch history proxy)
    liked_videos_count = await db.graph_nodes.count_documents({
        "user_id": user.id,
        "properties.source": "youtube",
        "properties.category": "liked_video_topic"
    })
    
    # Get integration stats
    integration_stats = {
        "last_sync": integration.get("last_sync"),
        "watch_history_tracked": integration.get("watch_history_tracked", 0),
        "llm_analysis_performed": integration.get("llm_analysis_performed", False),
        "data_collected": integration.get("data_collected", 0)
    }
    
    return {
        "youtube_connected": True,
        "watch_history_nodes": watch_history_count,
        "liked_videos_count": liked_videos_count,
        "integration_stats": integration_stats,
        "sample_watch_history": [
            {
                "title": item.get("properties", {}).get("video_title", "N/A"),
                "channel": item.get("properties", {}).get("channel", "N/A"),
                "watched_at": item.get("properties", {}).get("watched_at", "N/A"),
                "stored_at": item.get("created_at", "N/A")
            }
            for item in watch_history_samples
        ],
        "note": "Watch history is derived from: (1) Liked videos, (2) Activity feed (if available). For complete history, use YouTube Takeout upload."
    }

@router.post("/integrations/youtube/upload-watch-history")
async def upload_youtube_watch_history(request: Request, file: UploadFile = File(...)):
    """Upload and process YouTube Takeout watch history JSON file"""
    user = await require_auth(request)
    
    # Check if YouTube is connected
    integration = await db.user_integrations.find_one({
        "user_id": user.id,
        "platform_name": "youtube"
    })
    
    if not integration:
        raise HTTPException(
            status_code=400,
            detail="YouTube must be connected first. Please connect YouTube before uploading watch history."
        )
    
    # Validate file type
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    try:
        # Read and parse JSON file
        content = await file.read()
        watch_history_data = json.loads(content.decode('utf-8'))
        
        if not isinstance(watch_history_data, list):
            raise HTTPException(status_code=400, detail="JSON must be an array of watch history entries")
        
        logger.info(f"Received watch history file with {len(watch_history_data)} entries from user {user.id}")
        
        # Process watch history
        result = await process_youtube_watch_history(user.id, watch_history_data)
        
        return {
            "message": "Watch history processed successfully",
            "nodes_created": result["nodes_created"],
            "entries_processed": result.get("entries_processed", 0)
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Error processing watch history file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process watch history: {str(e)}")

@router.post("/integrations/youtube/update-credentials")
async def update_youtube_credentials(request: Request, data: Dict[str, Any]):
    """Update YouTube OAuth credentials for token refresh"""
    user = await require_auth(request)
    
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="client_id and client_secret required")
    
    # Find YouTube integration
    integration = await db.user_integrations.find_one({
        "user_id": user.id,
        "platform_name": "youtube"
    })
    
    if not integration:
        raise HTTPException(status_code=404, detail="YouTube integration not found")
    
    # Update credentials
    await db.user_integrations.update_one(
        {"id": integration["id"]},
        {
            "$set": {
                "oauth_client_id": client_id,
                "oauth_client_secret": client_secret
            }
        }
    )
    
    logger.info(f"Updated YouTube credentials for user {user.id}")
    
    return {
        "message": "YouTube credentials updated successfully",
        "can_refresh_token": bool(integration.get("refresh_token"))
    }

@router.post("/integrations/disconnect")
async def disconnect_platform(request: Request, data: Dict[str, Any]):
    """Disconnect external platform"""
    user = await require_auth(request)
    
    platform_name = data.get("platform_name")
    if not platform_name:
        raise HTTPException(status_code=400, detail="Platform name required")
    
    result = await db.user_integrations.delete_one({
        "user_id": user.id,
        "platform_name": platform_name
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return {"message": f"{platform_name} disconnected successfully"}

@router.post("/integrations/sync")
async def sync_platform_data(request: Request, data: Dict[str, Any]):
    """Sync data from connected platform and update profile + Graph RAG"""
    user = await require_auth(request)
    
    platform_name = data.get("platform_name")
    if not platform_name:
        raise HTTPException(status_code=400, detail="Platform name required")
    
    # Check if connected
    integration = await db.user_integrations.find_one({
        "user_id": user.id,
        "platform_name": platform_name
    })
    
    if not integration:
        raise HTTPException(status_code=404, detail="Platform not connected")
    
    # For LinkedIn, require access_token (OAuth must be completed)
    if platform_name == "linkedin":
        if not integration.get("access_token"):
            raise HTTPException(
                status_code=400, 
                detail="LinkedIn OAuth not completed. Please complete the OAuth flow first."
            )
    
    # Get full user document from database (not just Pydantic model)
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if we have real OAuth data for LinkedIn
    if platform_name == "linkedin" and integration.get("access_token"):
        # Fetch fresh data from LinkedIn API
        try:
            async with httpx.AsyncClient() as client:
                # Try OAuth 2.0 userinfo endpoint first, fall back to /v2/me
                profile_response = await client.get(
                    "https://api.linkedin.com/v2/userinfo",
                    headers={"Authorization": f"Bearer {integration['access_token']}"}
                )
                
                if profile_response.status_code != 200:
                    profile_response = await client.get(
                        "https://api.linkedin.com/v2/me"
                        "?projection=(id,localizedFirstName,localizedLastName,headline,profilePicture(displayImage~:playableStreams))",
                        headers={"Authorization": f"Bearer {integration['access_token']}"}
                    )
                
                profile_data = {}
                linkedin_id = None
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    # LinkedIn userinfo endpoint uses "sub" instead of "id"
                    linkedin_id = profile_data.get("id") or profile_data.get("sub")
                    logger.info(f"LinkedIn ID extracted: {linkedin_id}, profile keys: {list(profile_data.keys())}")
                
                # Note: Email address requires r_emailaddress scope which needs special LinkedIn approval
                # Skipping email fetch since we're using only r_liteprofile scope
                
                # Fetch additional data if we have LinkedIn ID
                skills_data = {}
                experience_data = {}
                education_data = {}
                activity_data = {}
                
                if linkedin_id:
                    logger.info(f"Fetching additional LinkedIn data for ID: {linkedin_id}")
                    # Fetch skills
                    try:
                        skills_response = await client.get(
                            f"https://api.linkedin.com/v2/people/(id:{linkedin_id})/skills",
                            headers={"Authorization": f"Bearer {integration['access_token']}"}
                        )
                        if skills_response.status_code == 200:
                            skills_data = skills_response.json()
                    except:
                        pass
                    
                    # Fetch experience/positions
                    try:
                        experience_response = await client.get(
                            f"https://api.linkedin.com/v2/people/(id:{linkedin_id})/positions",
                            headers={"Authorization": f"Bearer {integration['access_token']}"}
                        )
                        logger.info(f"LinkedIn positions endpoint status: {experience_response.status_code}")
                        if experience_response.status_code == 200:
                            experience_data = experience_response.json()
                            logger.info(f"LinkedIn experience data received - has elements: {bool(experience_data.get('elements'))}, count: {len(experience_data.get('elements', []))}")
                        else:
                            logger.warning(f"LinkedIn positions endpoint returned {experience_response.status_code}: {experience_response.text[:200]}")
                    except Exception as e:
                        logger.warning(f"Could not fetch experience: {str(e)}")
                    
                    # Fetch education
                    try:
                        education_response = await client.get(
                            f"https://api.linkedin.com/v2/people/(id:{linkedin_id})/educations",
                            headers={"Authorization": f"Bearer {integration['access_token']}"}
                        )
                        logger.info(f"LinkedIn educations endpoint status: {education_response.status_code}")
                        if education_response.status_code == 200:
                            education_data = education_response.json()
                            logger.info(f"LinkedIn education data received - has elements: {bool(education_data.get('elements'))}, count: {len(education_data.get('elements', []))}")
                        else:
                            logger.warning(f"LinkedIn educations endpoint returned {education_response.status_code}: {education_response.text[:200]}")
                    except Exception as e:
                        logger.warning(f"Could not fetch education: {str(e)}")
                    
                    # Fetch activity/posts (if available)
                    try:
                        activity_response = await client.get(
                            f"https://api.linkedin.com/v2/ugcPosts?authors=List({linkedin_id})&q=authors",
                            headers={"Authorization": f"Bearer {integration['access_token']}"}
                        )
                        if activity_response.status_code == 200:
                            activity_data = activity_response.json()
                    except:
                        pass
                
                # Sync real data
                await sync_linkedin_data(user.id, profile_data, skills_data, experience_data, education_data, activity_data, integration['access_token'])
                
                # Get updated node count
                node_count = await db.graph_nodes.count_documents({
                    "user_id": user.id,
                    "properties.source": "linkedin"
                })
                
                return {
                    "message": f"Synced real data from {platform_name}",
                    "nodes_added": node_count,
                    "profile_updated": True
                }
        except Exception as e:
            logger.error(f"Error fetching real LinkedIn data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to sync LinkedIn data: {str(e)}")
    
    # For YouTube, fetch fresh data from YouTube API
    if platform_name == "youtube" and integration.get("access_token"):
        try:
            async with httpx.AsyncClient() as client:
                access_token = integration.get("access_token")
                refresh_token = integration.get("refresh_token")
                
                # Try to refresh token if we have a refresh token and access token is expired
                if refresh_token:
                    # Test if access token is valid by making a simple API call
                    test_response = await client.get(
                        "https://www.googleapis.com/youtube/v3/channels",
                        params={"part": "snippet", "mine": "true"},
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=5.0
                    )
                    
                    # If token is expired (401), refresh it
                    if test_response.status_code == 401:
                        logger.info("YouTube access token expired, attempting to refresh...")
                        import os
                        client_id = integration.get("oauth_client_id") or os.getenv("YOUTUBE_CLIENT_ID", "")
                        client_secret = integration.get("oauth_client_secret") or os.getenv("YOUTUBE_CLIENT_SECRET", "")
                        
                        if client_id and client_secret:
                            refresh_data = {
                                "grant_type": "refresh_token",
                                "refresh_token": refresh_token,
                                "client_id": client_id,
                                "client_secret": client_secret
                            }
                            
                            refresh_response = await client.post(
                                "https://oauth2.googleapis.com/token",
                                data=refresh_data,
                                headers={"Content-Type": "application/x-www-form-urlencoded"},
                                timeout=10.0
                            )
                            
                            if refresh_response.status_code == 200:
                                token_info = refresh_response.json()
                                new_access_token = token_info.get("access_token")
                                if new_access_token:
                                    access_token = new_access_token
                                    # Update integration with new access token
                                    await db.user_integrations.update_one(
                                        {"id": integration["id"]},
                                        {"$set": {"access_token": new_access_token}}
                                    )
                                    logger.info("Successfully refreshed YouTube access token")
                                else:
                                    logger.warning("Token refresh succeeded but no access token in response")
                            else:
                                logger.warning(f"Failed to refresh token: {refresh_response.status_code} - {refresh_response.text[:200]}")
                        else:
                            logger.warning("Cannot refresh token - missing client credentials")
                
                # Fetch channel data
                channel_data = {}
                channel_response = await client.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={"part": "snippet,contentDetails,statistics", "mine": "true"},
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if channel_response.status_code == 200:
                    channel_result = channel_response.json()
                    if channel_result.get("items"):
                        channel_data = channel_result["items"][0]
                
                # Fetch subscriptions with pagination - get ALL subscriptions
                subscriptions_data = []
                try:
                    next_page_token = None
                    while True:
                        params = {"part": "snippet", "mine": "true", "maxResults": 50}
                        if next_page_token:
                            params["pageToken"] = next_page_token
                        
                        subs_response = await client.get(
                            "https://www.googleapis.com/youtube/v3/subscriptions",
                            params=params,
                            headers={"Authorization": f"Bearer {access_token}"}
                        )
                        if subs_response.status_code == 200:
                            subs_result = subs_response.json()
                            subscriptions_data.extend(subs_result.get("items", []))
                            next_page_token = subs_result.get("nextPageToken")
                            if not next_page_token:
                                break
                        else:
                            break
                    logger.info(f"Fetched {len(subscriptions_data)} subscriptions during sync (all pages)")
                except Exception as e:
                    logger.warning(f"Could not fetch subscriptions during sync: {str(e)}")
                
                # Fetch playlists with pagination - get ALL playlists
                playlists_data = []
                try:
                    next_page_token = None
                    while True:
                        params = {"part": "snippet,contentDetails", "mine": "true", "maxResults": 50}
                        if next_page_token:
                            params["pageToken"] = next_page_token
                        
                        playlists_response = await client.get(
                            "https://www.googleapis.com/youtube/v3/playlists",
                            params=params,
                            headers={"Authorization": f"Bearer {access_token}"}
                        )
                        if playlists_response.status_code == 200:
                            playlists_result = playlists_response.json()
                            playlists_data.extend(playlists_result.get("items", []))
                            next_page_token = playlists_result.get("nextPageToken")
                            if not next_page_token:
                                break
                        else:
                            break
                    logger.info(f"Fetched {len(playlists_data)} playlists during sync (all pages)")
                except Exception as e:
                    logger.warning(f"Could not fetch playlists during sync: {str(e)}")
                
                # Fetch liked videos with pagination - get ALL liked videos
                liked_videos_data = []
                try:
                    next_page_token = None
                    while True:
                        params = {"part": "snippet,statistics,contentDetails", "myRating": "like", "maxResults": 50}
                        if next_page_token:
                            params["pageToken"] = next_page_token
                        
                        liked_response = await client.get(
                            "https://www.googleapis.com/youtube/v3/videos",
                            params=params,
                            headers={"Authorization": f"Bearer {access_token}"}
                        )
                        if liked_response.status_code == 200:
                            liked_result = liked_response.json()
                            liked_videos_data.extend(liked_result.get("items", []))
                            next_page_token = liked_result.get("nextPageToken")
                            if not next_page_token:
                                break
                        else:
                            break
                    logger.info(f"Fetched {len(liked_videos_data)} liked videos during sync (all pages)")
                except Exception as e:
                    logger.warning(f"Could not fetch liked videos during sync: {str(e)}")
                
                # Try to fetch activity feed (recent watch history)
                activity_data = []
                try:
                    activity_response = await client.get(
                        "https://www.googleapis.com/youtube/v3/activities",
                        params={
                            "part": "snippet,contentDetails",
                            "mine": "true",
                            "maxResults": 50
                        },
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=10.0
                    )
                    if activity_response.status_code == 200:
                        activity_result = activity_response.json()
                        activity_data = activity_result.get("items", [])
                except Exception as e:
                    logger.warning(f"Could not fetch activity feed during sync: {str(e)}")
                
                youtube_data = {
                    "channel": channel_data,
                    "subscriptions": subscriptions_data,
                    "playlists": playlists_data,
                    "liked_videos": liked_videos_data,
                    "activity": activity_data
                }
                
                # Sync real data
                await sync_youtube_data(user.id, youtube_data, access_token)
                
                # Get updated node count - count ALL YouTube-related nodes (all have source: "youtube")
                node_count = await db.graph_nodes.count_documents({
                    "user_id": user.id,
                    "properties.source": "youtube"
                })
                
                logger.info(f"YouTube sync complete for user {user.id}: {node_count} total YouTube nodes in graph")
                
                return {
                    "message": f"Synced real data from {platform_name}",
                    "nodes_added": node_count,
                    "profile_updated": True
                }
        except Exception as e:
            logger.error(f"Error fetching real YouTube data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to sync YouTube data: {str(e)}")
    
    # Placeholder sync - in real implementation, this would fetch actual data via OAuth
    # Note: LinkedIn should never reach here since we require access_token above
    # For now, generate realistic mock data based on platform
    placeholder_data = {}
    profile_updates = {}  # Updates to user's Sense profile
    
    if platform_name == "spotify":
        placeholder_data = {
            "top_artists": ["The Weeknd", "Taylor Swift", "Drake", "Billie Eilish", "Post Malone"],
            "top_genres": ["pop", "hip-hop", "indie", "electronic", "rock"]
        }
        # Extract music interests for profile
        music_interests = ["music", "concerts", "songwriting"] + placeholder_data["top_genres"][:2]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + music_interests))
        
    elif platform_name == "youtube":
        placeholder_data = {
            "favorite_topics": ["technology", "travel vlogs", "cooking tutorials", "gaming", "fitness"],
            "watch_history_summary": "Interested in tech reviews, travel content, and cooking"
        }
        # Extract interests from YouTube topics
        youtube_interests = placeholder_data["favorite_topics"][:3]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + youtube_interests))
        
    elif platform_name == "instagram":
        placeholder_data = {
            "interests": ["photography", "travel", "food", "fitness", "art", "fashion"],
            "bio_keywords": ["photographer", "traveler", "foodie"],
            "hashtags_followed": ["#photography", "#travel", "#food", "#fitness"]
        }
        # Update profile with Instagram interests
        instagram_interests = placeholder_data["interests"][:5]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + instagram_interests))
        # Update bio if it's empty or short
        current_bio = user_doc.get("bio", "") or ""
        if not current_bio or len(current_bio) < 50:
            profile_updates["bio"] = f"Passionate about {', '.join(instagram_interests[:3])}"
            
    elif platform_name == "facebook":
        placeholder_data = {
            "interests": ["technology", "travel", "food", "sports", "music"],
            "pages_liked": ["Tech News", "Travel Blog", "Food Network"],
            "groups_joined": ["Tech Enthusiasts", "Travelers", "Food Lovers"]
        }
        facebook_interests = placeholder_data["interests"][:4]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + facebook_interests))
        
    elif platform_name == "twitter":
        placeholder_data = {
            "topics_followed": ["technology", "AI", "startups", "design", "productivity"],
            "tweet_themes": ["tech news", "productivity tips", "design inspiration"]
        }
        twitter_interests = placeholder_data["topics_followed"][:3]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + twitter_interests))
        
    elif platform_name == "linkedin":
        placeholder_data = {
            "skills": ["Python", "Machine Learning", "Data Science", "Software Engineering"],
            "industry": "Technology",
            "job_title": "Software Engineer"
        }
        # Update job title if not set
        if not user_doc.get("job_title"):
            profile_updates["job_title"] = placeholder_data["job_title"]
        # Add skills as interests
        skill_interests = [skill.lower() for skill in placeholder_data["skills"][:3]]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + skill_interests))
        
    elif platform_name == "tiktok":
        placeholder_data = {
            "interests": ["dancing", "comedy", "fashion", "cooking", "fitness", "travel"],
            "hashtags_followed": ["#fyp", "#viral", "#fitness", "#cooking"],
            "content_themes": ["lifestyle", "entertainment", "education"]
        }
        tiktok_interests = placeholder_data["interests"][:4]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + tiktok_interests))
        
    elif platform_name == "snapchat":
        placeholder_data = {
            "interests": ["photography", "social", "entertainment", "travel"],
            "story_themes": ["daily life", "travel", "food"]
        }
        snapchat_interests = placeholder_data["interests"][:3]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + snapchat_interests))
        
    elif platform_name == "pinterest":
        placeholder_data = {
            "boards": ["Travel Ideas", "Food Recipes", "Home Decor", "Fashion"],
            "interests": ["travel", "cooking", "interior design", "fashion", "diy"],
            "pins_saved": 500
        }
        pinterest_interests = placeholder_data["interests"][:4]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + pinterest_interests))
        
    elif platform_name == "reddit":
        placeholder_data = {
            "subreddits": ["r/programming", "r/technology", "r/startups", "r/productivity"],
            "interests": ["programming", "technology", "startups", "productivity", "discussion"],
            "topics": ["tech", "business", "self-improvement"]
        }
        reddit_interests = placeholder_data["interests"][:4]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + reddit_interests))
        
    elif platform_name == "discord":
        placeholder_data = {
            "servers": ["Gaming", "Technology", "Art"],
            "interests": ["gaming", "technology", "art", "community"],
            "activity": "active in tech and gaming communities"
        }
        discord_interests = placeholder_data["interests"][:3]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + discord_interests))
        
    elif platform_name == "twitch":
        placeholder_data = {
            "games_watched": ["Just Chatting", "League of Legends", "Valorant"],
            "interests": ["gaming", "streaming", "esports", "entertainment"],
            "streamers_followed": ["Popular Streamer 1", "Popular Streamer 2"]
        }
        twitch_interests = placeholder_data["interests"][:3]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + twitch_interests))
        
    elif platform_name == "apple_music":
        placeholder_data = {
            "top_artists": ["The Weeknd", "Taylor Swift", "Drake"],
            "top_genres": ["pop", "hip-hop", "r&b"],
            "playlists": ["My Favorites", "Workout Mix"]
        }
        apple_music_interests = ["music", "apple music"] + placeholder_data["top_genres"][:2]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + apple_music_interests))
        
    elif platform_name == "soundcloud":
        placeholder_data = {
            "favorite_artists": ["Indie Artist 1", "Electronic Producer 1"],
            "genres": ["electronic", "indie", "hip-hop"],
            "tracks_liked": 500
        }
        soundcloud_interests = ["music", "soundcloud"] + placeholder_data["genres"][:2]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + soundcloud_interests))
        
    elif platform_name in ["hulu", "disney_plus", "prime_video", "hbo_max"]:
        placeholder_data = {
            "watch_history": ["Action", "Comedy", "Drama", "Sci-Fi"],
            "interests": ["movies", "tv shows", "entertainment", "streaming"],
            "favorite_genres": ["action", "comedy", "drama"]
        }
        streaming_interests = placeholder_data["interests"][:3]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + streaming_interests))
        
    elif platform_name in ["ebay", "etsy", "shopify", "walmart"]:
        placeholder_data = {
            "purchase_categories": ["electronics", "clothing", "home", "books"],
            "interests": ["shopping", "fashion", "technology", "home decor"],
            "purchase_history_summary": "Interested in tech, fashion, and home items"
        }
        shopping_interests = placeholder_data["interests"][:3]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + shopping_interests))
        
    elif platform_name in ["fitbit", "myfitnesspal", "nike_run_club", "garmin"]:
        placeholder_data = {
            "activities": ["running", "cycling", "weight training", "yoga"],
            "interests": ["fitness", "health", "exercise", "wellness"],
            "goals": ["weight loss", "muscle gain", "endurance"]
        }
        fitness_interests = placeholder_data["interests"][:3]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + fitness_interests))
        
    elif platform_name in ["medium", "kindle", "audible"]:
        placeholder_data = {
            "topics": ["technology", "self-improvement", "fiction", "business"],
            "interests": ["reading", "writing", "learning", "books"],
            "favorite_authors": ["Author 1", "Author 2"]
        }
        reading_interests = placeholder_data["interests"][:3]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + reading_interests))
        
    elif platform_name in ["coursera", "udemy"]:
        placeholder_data = {
            "courses_taken": ["Machine Learning", "Web Development", "Data Science"],
            "interests": ["learning", "education", "skills", "professional development"],
            "topics": ["programming", "data science", "business"]
        }
        learning_interests = placeholder_data["interests"][:2] + placeholder_data["topics"][:2]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + learning_interests))
        
    elif platform_name in ["whatsapp", "telegram"]:
        placeholder_data = {
            "groups": ["Tech Enthusiasts", "Travel", "Fitness"],
            "interests": ["messaging", "communication", "community"],
            "activity": "Active in tech and travel groups"
        }
        messaging_interests = placeholder_data["interests"][:2]
        current_interests = user_doc.get("interests", []) or []
        profile_updates["interests"] = list(set(current_interests + messaging_interests))
    
    # Update user profile (Sense world) with extracted data
    if profile_updates:
        await db.users.update_one(
            {"id": user.id},
            {"$set": profile_updates}
        )
        logger.info(f"Updated profile for user {user.id} from {platform_name}")
    
    # Enrich Graph RAG with platform data
    if placeholder_data:
        result = await get_graph_builder().add_external_platform_data(
            user.id, platform_name, placeholder_data
        )
        
        logger.info(f"Added {result['nodes_created']} nodes from {platform_name} to graph for user {user.id}")
        
        # Also extract entities from combined data using LLM for better extraction
        if get_azure_client() and placeholder_data:
            # Create a text summary of the data for entity extraction
            data_summary = json.dumps(placeholder_data, indent=2)
            try:
                extracted_nodes = await get_graph_builder().extract_entities_from_text(
                    f"Platform data from {platform_name}: {data_summary}",
                    user.id
                )
                # Mark these as coming from the platform
                for node in extracted_nodes:
                    node["properties"]["source"] = platform_name
                    # Check if exists, if not create
                    existing = await db.graph_nodes.find_one({
                        "user_id": user.id,
                        "node_type": node["node_type"],
                        "label": node["label"]
                    })
                    if not existing:
                        await db.graph_nodes.insert_one(node)
                        result["nodes_created"] += 1
                        logger.info(f"Added LLM-extracted node: {node['node_type']}:{node['label']} from {platform_name}")
            except Exception as e:
                logger.error(f"Error extracting entities from {platform_name} data: {str(e)}")
        
        # Verify nodes were created
        node_count = await db.graph_nodes.count_documents({
            "user_id": user.id,
            "properties.source": platform_name
        })
        logger.info(f"Total nodes from {platform_name} for user {user.id}: {node_count}")
        
        # Update integration sync time
        await db.user_integrations.update_one(
            {"id": integration["id"]},
            {
                "$set": {
                    "last_sync": datetime.now(timezone.utc).isoformat(),
                    "data_collected": result["nodes_created"]
                }
            }
        )
        
        return {
            "message": f"Synced data from {platform_name}",
            "nodes_added": result["nodes_created"],
            "profile_updated": bool(profile_updates),
            "profile_updates": list(profile_updates.keys()) if profile_updates else []
        }
    
    return {"message": "Sync completed", "nodes_added": 0}

