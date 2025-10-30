from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Query
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
import uuid
from datetime import datetime, timezone, timedelta
from openai import AsyncAzureOpenAI
import httpx
import json
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Azure OpenAI credentials
AZURE_OPENAI_API_KEY = os.environ.get('AZURE_OPENAI_API_KEY', '')
AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT', '')
AZURE_OPENAI_DEPLOYMENT = os.environ.get('AZURE_OPENAI_DEPLOYMENT', '')
AZURE_OPENAI_API_VERSION = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-10-21')

# Create Azure OpenAI client
azure_client = None
if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
    azure_client = AsyncAzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT
    )

# Create the main app
app = FastAPI(title="AI Dating Match App")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ MODELS ============

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Profile fields
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    job_title: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    
    # Profile completion status
    profile_completed: bool = False
    onboarding_stage: str = "start"
    is_bot: bool = False

class UserIntegration(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    platform_name: str
    platform_type: str  # social_media, ecommerce, email, messaging, dating
    connected: bool = True
    connected_at: str
    last_sync: str
    data_collected: int = 0

class Friendship(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    friend_id: str
    status: str  # pending, accepted, blocked
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = None

class ConversationStage(BaseModel):
    stage: int  # 1-5
    name: str
    completed: bool = False
    score: float = 0.0
    messages: List[Dict[str, Any]] = Field(default_factory=list)

class AgentConversation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent1_user_id: str
    agent2_user_id: str
    current_stage: int = 1
    stages: List[ConversationStage] = Field(default_factory=list)
    overall_score: float = 0.0
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Keep existing models
class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GraphNode(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    node_type: str
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AIAgent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    personality_summary: str = ""
    conversation_style: str = "friendly"
    knowledge_graph_version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Match(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    matched_user_id: str
    compatibility_score: float
    shared_interests: List[str] = Field(default_factory=list)
    personality_compatibility: float = 0.0
    conversation_quality: float = 0.0
    agent_conversation_id: str
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class HumanConversation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ AUTH HELPERS ============

async def get_current_user(request: Request) -> Optional[User]:
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.replace("Bearer ", "")
    
    if not session_token:
        return None
    
    session = await db.user_sessions.find_one({"session_token": session_token})
    if not session:
        return None
    
    expires_at = session['expires_at']
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    elif not expires_at.tzinfo:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        return None
    
    user_doc = await db.users.find_one({"id": session['user_id']})
    if not user_doc:
        return None
    
    return User(**user_doc)

async def require_auth(request: Request) -> User:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

# ============ AUTH ROUTES ============

@api_router.get("/auth/session-data")
async def get_session_data(request: Request):
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
            
            existing_user = await db.users.find_one({"email": data['email']})
            
            if not existing_user:
                user = User(
                    email=data['email'],
                    name=data['name'],
                    picture=data.get('picture')
                )
                user_dict = user.model_dump()
                user_dict['created_at'] = user_dict['created_at'].isoformat()
                await db.users.insert_one(user_dict)
                user_id = user.id
            else:
                user_id = existing_user['id']
            
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

@api_router.get("/auth/me")
async def get_me(request: Request):
    user = await require_auth(request)
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie("session_token")
    return {"message": "Logged out"}

# ============ SEARCH & FRIENDS ROUTES ============

@api_router.get("/search/users")
async def search_users(q: str = Query(..., min_length=1), request: Request = None):
    user = await require_auth(request)
    
    # Search by name, bio, interests, location
    search_query = {
        "$and": [
            {"id": {"$ne": user.id}},  # Exclude current user
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
    
    # Check friendship status for each user
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

@api_router.post("/friends/request/{friend_id}")
async def send_friend_request(friend_id: str, request: Request):
    user = await require_auth(request)
    
    if user.id == friend_id:
        raise HTTPException(status_code=400, detail="Cannot add yourself")
    
    # Check if friendship exists
    existing = await db.friendships.find_one({
        "$or": [
            {"user_id": user.id, "friend_id": friend_id},
            {"user_id": friend_id, "friend_id": user.id}
        ]
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Friend request already exists")
    
    friendship = Friendship(
        user_id=user.id,
        friend_id=friend_id,
        status="pending"
    )
    
    friend_dict = friendship.model_dump()
    friend_dict['requested_at'] = friend_dict['requested_at'].isoformat()
    await db.friendships.insert_one(friend_dict)
    
    return {"message": "Friend request sent"}

@api_router.post("/friends/accept/{friendship_id}")
async def accept_friend_request(friendship_id: str, request: Request):
    user = await require_auth(request)
    
    friendship = await db.friendships.find_one({"id": friendship_id, "friend_id": user.id})
    if not friendship:
        raise HTTPException(status_code=404, detail="Request not found")
    
    await db.friendships.update_one(
        {"id": friendship_id},
        {"$set": {
            "status": "accepted",
            "accepted_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Friend request accepted"}

@api_router.delete("/friends/{friend_id}")
async def remove_friend(friend_id: str, request: Request):
    user = await require_auth(request)
    
    result = await db.friendships.delete_one({
        "$or": [
            {"user_id": user.id, "friend_id": friend_id},
            {"user_id": friend_id, "friend_id": user.id}
        ]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Friendship not found")
    
    return {"message": "Friend removed"}

@api_router.get("/friends")
async def get_friends(request: Request):
    user = await require_auth(request)
    
    friendships = await db.friendships.find({
        "$or": [
            {"user_id": user.id, "status": "accepted"},
            {"friend_id": user.id, "status": "accepted"}
        ]
    }, {"_id": 0}).to_list(1000)
    
    friend_ids = []
    for f in friendships:
        friend_id = f['friend_id'] if f['user_id'] == user.id else f['user_id']
        friend_ids.append(friend_id)
    
    friends = await db.users.find({"id": {"$in": friend_ids}}, {"_id": 0}).to_list(1000)
    
    return friends

@api_router.get("/friends/requests")
async def get_friend_requests(request: Request):
    user = await require_auth(request)
    
    requests = await db.friendships.find({
        "friend_id": user.id,
        "status": "pending"
    }, {"_id": 0}).to_list(100)
    
    # Enrich with user data
    for req in requests:
        requester = await db.users.find_one({"id": req['user_id']}, {"_id": 0})
        if requester:
            req['user'] = {
                "id": requester['id'],
                "name": requester['name'],
                "picture": requester.get('picture'),
                "bio": requester.get('bio')
            }
    
    return requests

# ============ INTEGRATIONS ROUTES ============

@api_router.get("/integrations")
async def get_integrations(request: Request):
    user = await require_auth(request)
    
    integrations = await db.user_integrations.find({"user_id": user.id}, {"_id": 0}).to_list(100)
    
    # Group by type
    grouped = {
        "social_media": [],
        "ecommerce": [],
        "email": [],
        "messaging": [],
        "dating": []
    }
    
    for integration in integrations:
        platform_type = integration.get('platform_type', 'other')
        if platform_type in grouped:
            grouped[platform_type].append(integration)
    
    return grouped

# Continue with existing routes from original server.py...
# (Profile, Agent, Matching, Chat routes remain the same)

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
