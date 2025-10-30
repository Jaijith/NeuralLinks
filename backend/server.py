from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
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
import random

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
    interests: List[str] = Field(default_factory=list)
    
    # Avatar profile fields (parallel to real profile)
    avatar_name: Optional[str] = None
    avatar_picture: Optional[str] = None
    avatar_bio: Optional[str] = None
    avatar_job_title: Optional[str] = None
    avatar_location: Optional[str] = None
    avatar_interests: List[str] = Field(default_factory=list)
    
    # Profile completion status
    profile_completed: bool = False
    onboarding_stage: str = "start"  # start, basic_info, personality, interests, complete

class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GraphNode(BaseModel):
    """Represents a node in the knowledge graph"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    node_type: str  # interest, trait, value, experience, preference
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GraphEdge(BaseModel):
    """Represents a relationship between nodes"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_node_id: str
    to_node_id: str
    relationship_type: str  # likes, dislikes, similar_to, part_of
    weight: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AIAgent(BaseModel):
    """Represents a user's AI agent"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    personality_summary: str = ""
    conversation_style: str = "friendly"
    knowledge_graph_version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentConversation(BaseModel):
    """Conversation between two AI agents"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent1_user_id: str
    agent2_user_id: str
    messages: List[Dict[str, str]] = Field(default_factory=list)
    compatibility_score: Optional[float] = None
    conversation_summary: str = ""
    status: str = "active"  # active, completed, archived
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Match(BaseModel):
    """Represents a match between two users"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    matched_user_id: str
    compatibility_score: float
    shared_interests: List[str] = Field(default_factory=list)
    personality_compatibility: float = 0.0
    conversation_quality: float = 0.0
    agent_conversation_id: str
    status: str = "pending"  # pending, accepted, rejected
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class HumanConversation(BaseModel):
    """Real conversation between matched users"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserIntegration(BaseModel):
    """User's connected platform integration"""
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
    """Friendship/connection between users"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    friend_id: str
    status: str  # pending, accepted, blocked
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = None

# ============ AUTH HELPERS ============

async def get_current_user(request: Request) -> Optional[User]:
    """Get current authenticated user from session token"""
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

async def require_auth(request: Request) -> User:
    """Require authentication"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

# ============ AUTH ROUTES ============

@api_router.get("/auth/session-data")
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
                # Create new user with BOTH real and avatar profiles
                # Generate avatar nickname
                avatar_prefixes = ['Cyber', 'Neon', 'Digital', 'Quantum', 'Stellar', 'Phoenix', 'Dragon', 'Storm']
                avatar_suffixes = ['Walker', 'Rider', 'Hunter', 'Seeker', 'Warrior', 'Spirit', 'Dream', 'Star']
                avatar_nickname = f"{random.choice(avatar_prefixes)}{random.choice(avatar_suffixes)}"
                
                # Generate avatar image
                avatar_seed = f"{data['name']}{random.randint(100, 999)}"
                avatar_picture = f"https://api.dicebear.com/7.x/adventurer/svg?seed={avatar_seed}"
                
                user = User(
                    email=data['email'],
                    name=data['name'],
                    picture=data.get('picture'),
                    # Avatar profile (auto-created)
                    avatar_name=avatar_nickname,
                    avatar_picture=avatar_picture,
                    avatar_bio="Digital warrior in the virtual realm",
                    avatar_job_title="Virtual Explorer",
                    avatar_location="Cyberspace",
                    avatar_interests=[],
                    avatar_posts=[]
                )
                user_dict = user.model_dump()
                user_dict['created_at'] = user_dict['created_at'].isoformat()
                await db.users.insert_one(user_dict)
                user_id = user.id
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

@api_router.get("/auth/me")
async def get_me(request: Request):
    """Get current user"""
    user = await require_auth(request)
    return user

@api_router.get("/users/{user_id}")
async def get_user_profile(user_id: str, world_mode: str = "real", request: Request = None):
    """Get user profile by ID with world mode support"""
    user = await require_auth(request)
    
    # Get the target user
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Apply world mode transformations for bots
    if target_user.get('is_bot') and world_mode == 'avatar':
        # Use avatar identity
        if 'avatar_name' in target_user:
            target_user['display_name'] = target_user['avatar_name']
            target_user['display_picture'] = target_user.get('avatar_picture', target_user['picture'])
            target_user['display_bio'] = target_user.get('avatar_bio', target_user['bio'])
        else:
            target_user['display_name'] = target_user['name']
            target_user['display_picture'] = target_user['picture']
            target_user['display_bio'] = target_user['bio']
    else:
        # Use real identity
        target_user['display_name'] = target_user['name']
        target_user['display_picture'] = target_user['picture']
        target_user['display_bio'] = target_user['bio']
    
    # Check friendship status
    friendship = await db.friendships.find_one({
        "$or": [
            {"user_id": user.id, "friend_id": user_id},
            {"user_id": user_id, "friend_id": user.id}
        ]
    })
    
    target_user['friendship_status'] = friendship['status'] if friendship else 'none'
    target_user['is_friend'] = friendship['status'] == 'accepted' if friendship else False
    
    return target_user

async def get_me(request: Request):
    """Get current user"""
    user = await require_auth(request)
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie("session_token")
    return {"message": "Logged out"}

# ============ PROFILE ROUTES ============

@api_router.put("/profile")
async def update_profile(profile_data: Dict[str, Any], request: Request):
    """Update user's real profile"""
    user = await require_auth(request)
    
    # Only update real profile fields (not avatar fields)
    real_fields = {}
    for key, value in profile_data.items():
        if not key.startswith('avatar_'):
            real_fields[key] = value
    
    # Update user
    await db.users.update_one(
        {"id": user.id},
        {"$set": real_fields}
    )
    
    return {"message": "Profile updated"}

@api_router.put("/profile/avatar")
async def update_avatar_profile(avatar_data: Dict[str, Any], request: Request):
    """Update user's avatar profile (separate from real profile)"""
    user = await require_auth(request)
    
    # Prefix all avatar fields
    avatar_update = {}
    for key, value in avatar_data.items():
        if not key.startswith('avatar_'):
            avatar_update[f'avatar_{key}'] = value
        else:
            avatar_update[key] = value
    
    # Update user's avatar data
    await db.users.update_one(
        {"id": user.id},
        {"$set": avatar_update}
    )
    
    return {"message": "Avatar profile updated"}

@api_router.get("/profile/avatar")
async def get_avatar_profile(request: Request):
    """Get current user's avatar profile"""
    user = await require_auth(request)
    
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    
    # Extract avatar-specific fields
    avatar_profile = {
        "avatar_name": user_doc.get("avatar_name", ""),
        "avatar_bio": user_doc.get("avatar_bio", ""),
        "avatar_picture": user_doc.get("avatar_picture", ""),
        "avatar_interests": user_doc.get("avatar_interests", []),
        "avatar_job_title": user_doc.get("avatar_job_title", ""),
        "avatar_location": user_doc.get("avatar_location", "")
    }
    
    return avatar_profile

@api_router.post("/profile/posts")
async def create_post(post_data: Dict[str, str], request: Request):
    """Create a new post on user's profile"""
    user = await require_auth(request)
    
    # Determine post type (real or avatar)
    post_type = post_data.get('post_type', 'real')  # 'real' or 'avatar'
    
    new_post = {
        'id': str(uuid.uuid4()),
        'text': post_data.get('text', ''),
        'post_type': post_type,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'likes': 0,
        'comments': 0
    }
    
    # Add post to appropriate array based on type
    if post_type == 'avatar':
        await db.users.update_one(
            {"id": user.id},
            {"$push": {"avatar_posts": new_post}}
        )
    else:
        await db.users.update_one(
            {"id": user.id},
            {"$push": {"posts": new_post}}
        )
    
    return new_post

@api_router.get("/profile/posts")
async def get_user_posts(post_type: str = "real", request: Request = None):
    """Get current user's posts"""
    user = await require_auth(request)
    
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0, "posts": 1, "avatar_posts": 1})
    
    if post_type == 'avatar':
        posts = user_doc.get('avatar_posts', []) if user_doc else []
    else:
        posts = user_doc.get('posts', []) if user_doc else []
    
    # Sort by created_at descending
    posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return posts

@api_router.delete("/profile/posts/{post_id}")
async def delete_post(post_id: str, post_type: str = "real", request: Request = None):
    """Delete a user's post"""
    user = await require_auth(request)
    
    if post_type == 'avatar':
        await db.users.update_one(
            {"id": user.id},
            {"$pull": {"avatar_posts": {"id": post_id}}}
        )
    else:
        await db.users.update_one(
            {"id": user.id},
            {"$pull": {"posts": {"id": post_id}}}
        )
    
    return {"message": "Post deleted"}

@api_router.put("/profile/posts/{post_id}")
async def edit_post(post_id: str, post_data: Dict[str, str], request: Request):
    """Edit a user's post"""
    user = await require_auth(request)
    
    post_type = post_data.get('post_type', 'real')
    
    # Update the specific post in the array
    if post_type == 'avatar':
        await db.users.update_one(
            {"id": user.id, "avatar_posts.id": post_id},
            {"$set": {"avatar_posts.$.text": post_data.get('text', '')}}
        )
    else:
        await db.users.update_one(
            {"id": user.id, "posts.id": post_id},
            {"$set": {"posts.$.text": post_data.get('text', '')}}
        )
    
    return {"message": "Post updated"}

@api_router.post("/profile/onboarding-chat")
async def onboarding_chat(message: Dict[str, str], request: Request):
    """Chat with AI agent during onboarding"""
    user = await require_auth(request)
    
    if not azure_client:
        raise HTTPException(status_code=500, detail="Azure OpenAI not configured")
    
    user_message = message.get("message", "")
    
    # Get user's current profile
    user_doc = await db.users.find_one({"id": user.id})
    
    # Build context from user's profile
    context = f"""
You are helping {user.name} create their dating profile through a friendly conversation.
Current profile status:
- Age: {user_doc.get('age', 'Not set')}
- Gender: {user_doc.get('gender', 'Not set')}
- Location: {user_doc.get('location', 'Not set')}
- Bio: {user_doc.get('bio', 'Not set')}
- Interests: {', '.join(user_doc.get('interests', []))}
- Onboarding stage: {user_doc.get('onboarding_stage', 'start')}

Guide them through completing their profile naturally. Ask about:
1. Basic info (age, gender, location)
2. Personality traits and values
3. Interests and hobbies
4. What they're looking for in a match

Extract information from their responses and provide it in a structured way.
Be warm, engaging, and conversational.
"""
    
    try:
        response = await azure_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        ai_response = response.choices[0].message.content
        
        # Store conversation in graph for future learning
        # Extract insights and update graph
        
        return {
            "response": ai_response,
            "profile_completion": 50  # Calculate actual completion
        }
    except Exception as e:
        logger.error(f"Onboarding chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ GRAPH RAG ROUTES ============

@api_router.post("/graph/add-node")
async def add_graph_node(node_data: Dict[str, Any], request: Request):
    """Add a node to user's knowledge graph"""
    user = await require_auth(request)
    
    node = GraphNode(
        user_id=user.id,
        node_type=node_data['node_type'],
        label=node_data['label'],
        properties=node_data.get('properties', {})
    )
    
    node_dict = node.model_dump()
    node_dict['created_at'] = node_dict['created_at'].isoformat()
    node_dict['updated_at'] = node_dict['updated_at'].isoformat()
    await db.graph_nodes.insert_one(node_dict)
    
    return node

@api_router.get("/graph/my-graph")
async def get_my_graph(request: Request):
    """Get user's knowledge graph"""
    user = await require_auth(request)
    
    nodes = await db.graph_nodes.find({"user_id": user.id}, {"_id": 0}).to_list(1000)
    edges = await db.graph_edges.find(
        {"$or": [
            {"from_node_id": {"$in": [n['id'] for n in nodes]}},
            {"to_node_id": {"$in": [n['id'] for n in nodes]}}
        ]},
        {"_id": 0}
    ).to_list(1000)
    
    return {"nodes": nodes, "edges": edges}

# ============ AI AGENT ROUTES ============

@api_router.post("/agent/create")
async def create_agent(request: Request):
    """Create AI agent for user"""
    user = await require_auth(request)
    
    # Check if agent exists
    existing = await db.ai_agents.find_one({"user_id": user.id})
    if existing:
        return AIAgent(**existing)
    
    # Create agent
    agent = AIAgent(
        user_id=user.id,
        personality_summary=f"{user.name}'s AI agent"
    )
    
    agent_dict = agent.model_dump()
    agent_dict['created_at'] = agent_dict['created_at'].isoformat()
    agent_dict['updated_at'] = agent_dict['updated_at'].isoformat()
    await db.ai_agents.insert_one(agent_dict)
    
    return agent

@api_router.post("/agent/start-conversation/{target_user_id}")
async def start_agent_conversation(target_user_id: str, request: Request):
    """Start AI agent conversation with another user"""
    user = await require_auth(request)
    
    if not azure_client:
        raise HTTPException(status_code=500, detail="Azure OpenAI not configured")
    
    # Get both users' profiles and graphs
    user1_doc = await db.users.find_one({"id": user.id})
    user2_doc = await db.users.find_one({"id": target_user_id})
    
    if not user2_doc:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # Get knowledge graphs
    user1_nodes = await db.graph_nodes.find({"user_id": user.id}, {"_id": 0}).to_list(100)
    user2_nodes = await db.graph_nodes.find({"user_id": target_user_id}, {"_id": 0}).to_list(100)
    
    # Create conversation
    conversation = AgentConversation(
        agent1_user_id=user.id,
        agent2_user_id=target_user_id
    )
    
    # Simulate AI agent conversation (simplified)
    messages = []
    
    # Agent 1 introduces
    agent1_context = f"""You are {user1_doc['name']}'s AI dating agent. Your personality: {', '.join(user1_doc.get('interests', []))}.
Introduce yourself briefly and ask an interesting question."""
    
    response1 = await azure_client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[{"role": "system", "content": agent1_context}],
        temperature=0.8,
        max_tokens=150
    )
    
    agent1_msg = response1.choices[0].message.content
    messages.append({"sender": user.id, "message": agent1_msg, "timestamp": datetime.now(timezone.utc).isoformat()})
    
    # Agent 2 responds
    agent2_context = f"""You are {user2_doc['name']}'s AI dating agent. Your personality: {', '.join(user2_doc.get('interests', []))}.
Respond to the introduction and share something interesting about yourself."""
    
    response2 = await azure_client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": agent2_context},
            {"role": "user", "content": agent1_msg}
        ],
        temperature=0.8,
        max_tokens=150
    )
    
    agent2_msg = response2.choices[0].message.content
    messages.append({"sender": target_user_id, "message": agent2_msg, "timestamp": datetime.now(timezone.utc).isoformat()})
    
    conversation.messages = messages
    
    # Calculate basic compatibility score
    shared_interests = list(set(user1_doc.get('interests', [])) & set(user2_doc.get('interests', [])))
    conversation.compatibility_score = min(len(shared_interests) * 15, 100)
    conversation.conversation_summary = f"Agents discussed common interests: {', '.join(shared_interests)}"
    
    conv_dict = conversation.model_dump()
    conv_dict['created_at'] = conv_dict['created_at'].isoformat()
    conv_dict['updated_at'] = conv_dict['updated_at'].isoformat()
    await db.agent_conversations.insert_one(conv_dict)
    
    return conversation

# ============ MATCHING ROUTES ============

@api_router.get("/matches")
async def get_matches(request: Request):
    """Get user's matches"""
    user = await require_auth(request)
    
    matches = await db.matches.find({"user_id": user.id}, {"_id": 0}).to_list(100)
    
    # Enrich with user data
    for match in matches:
        matched_user = await db.users.find_one({"id": match['matched_user_id']}, {"_id": 0})
        if matched_user:
            match['matched_user'] = {
                "name": matched_user['name'],
                "picture": matched_user.get('picture'),
                "age": matched_user.get('age'),
                "bio": matched_user.get('bio')
            }
    
    return matches

@api_router.post("/matches/discover")
async def discover_matches(request: Request):
    """Discover potential matches using AI agents"""
    user = await require_auth(request)
    
    # Get other users with completed profiles
    other_users = await db.users.find({
        "id": {"$ne": user.id},
        "profile_completed": True
    }, {"_id": 0}).to_list(50)
    
    matches = []
    
    for other_user in other_users[:5]:  # Limit to 5 for demo
        # Check if already matched
        existing = await db.matches.find_one({
            "user_id": user.id,
            "matched_user_id": other_user['id']
        })
        
        if existing:
            continue
        
        # Start agent conversation
        try:
            # Simplified matching logic
            shared_interests = list(set(user.interests) & set(other_user.get('interests', [])))
            compatibility = min(len(shared_interests) * 20, 100)
            
            if compatibility > 30:  # Threshold
                match = Match(
                    user_id=user.id,
                    matched_user_id=other_user['id'],
                    compatibility_score=compatibility,
                    shared_interests=shared_interests,
                    personality_compatibility=compatibility * 0.8,
                    conversation_quality=compatibility * 0.9,
                    agent_conversation_id=""
                )
                
                match_dict = match.model_dump()
                match_dict['created_at'] = match_dict['created_at'].isoformat()
                await db.matches.insert_one(match_dict)
                
                matches.append(match)
        except Exception as e:
            logger.error(f"Error creating match: {str(e)}")
    
    return matches

@api_router.get("/matches/{match_id}/conversation")
async def get_agent_conversation(match_id: str, request: Request):
    """Get AI agent conversation for a match"""
    user = await require_auth(request)
    
    match = await db.matches.find_one({"id": match_id, "user_id": user.id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if match.get('agent_conversation_id'):
        conversation = await db.agent_conversations.find_one(
            {"id": match['agent_conversation_id']},
            {"_id": 0}
        )
        return conversation
    
    return {"messages": [], "summary": "No conversation yet"}

# ============ HUMAN CHAT ROUTES ============

@api_router.post("/chat/send")
async def send_message(data: Dict[str, Any], request: Request):
    """Send message in human conversation"""
    user = await require_auth(request)
    
    match_id = data['match_id']
    message_text = data['message']
    
    # Verify match
    match = await db.matches.find_one({"id": match_id, "user_id": user.id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Get or create conversation
    conversation = await db.human_conversations.find_one({"match_id": match_id})
    
    if not conversation:
        conversation = HumanConversation(match_id=match_id, messages=[])
        conv_dict = conversation.model_dump()
        conv_dict['created_at'] = conv_dict['created_at'].isoformat()
        await db.human_conversations.insert_one(conv_dict)
    
    # Add message
    new_message = {
        "sender_id": user.id,
        "message": message_text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.human_conversations.update_one(
        {"match_id": match_id},
        {"$push": {"messages": new_message}}
    )
    
    return new_message

@api_router.get("/chat/{match_id}/messages")
async def get_messages(match_id: str, request: Request):
    """Get messages for a match"""
    user = await require_auth(request)
    
    conversation = await db.human_conversations.find_one({"match_id": match_id}, {"_id": 0})
    if not conversation:
        return {"messages": []}
    
    return conversation

# Include router

# ============ SEARCH & FRIENDS ROUTES ============

@api_router.get("/search/users")
async def search_users(q: str, request: Request):
    """Search for users by name, bio, interests, location"""
    user = await require_auth(request)
    
    if len(q) < 1:
        return []
    
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

@api_router.post("/friends/request/{friend_id}")
async def send_friend_request(friend_id: str, request: Request):
    """Send a friend request"""
    user = await require_auth(request)
    
    if user.id == friend_id:
        raise HTTPException(status_code=400, detail="Cannot add yourself")
    
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
    
    return {"message": "Friend request sent", "friendship_id": friendship.id}

@api_router.post("/friends/accept/{friendship_id}")
async def accept_friend_request(friendship_id: str, request: Request):
    """Accept a friend request"""
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
    """Remove a friend"""
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
    """Get user's friends list"""
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
    """Get pending friend requests"""
    user = await require_auth(request)
    
    requests = await db.friendships.find({
        "friend_id": user.id,
        "status": "pending"
    }, {"_id": 0}).to_list(100)
    
    for req in requests:
        requester = await db.users.find_one({

"id": req['user_id']}, {"_id": 0})
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
    """Get user's connected platform integrations"""
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

# ============ AVATAR ACTIVITY ROUTES ============

@api_router.get("/avatar/activity/{user_id}")
async def get_avatar_activity(user_id: str, request: Request):
    """Get avatar's activity feed"""
    user = await require_auth(request)
    
    # Get avatar's conversations
    conversations = await db.agent_conversations.find({
        "$or": [
            {"agent1_user_id": user_id},
            {"agent2_user_id": user_id}
        ]
    }, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    
    # Enrich with user data
    activities = []
    for conv in conversations:
        other_user_id = conv['agent2_user_id'] if conv['agent1_user_id'] == user_id else conv['agent1_user_id']
        other_user = await db.users.find_one({"id": other_user_id}, {"_id": 0})
        
        if other_user:
            activities.append({
                "type": "conversation",
                "timestamp": conv.get('created_at'),
                "other_user": {
                    "id": other_user['id'],
                    "name": other_user['name'],
                    "picture": other_user.get('picture')
                },
                "score": conv.get('overall_score', conv.get('compatibility_score', 0)),
                "status": conv.get('status'),
                "message_count": len(conv.get('messages', []))
            })
    
    return activities

@api_router.get("/avatar/conversations")
async def get_avatar_conversations(request: Request):
    """Get all avatar conversations for current user"""
    user = await require_auth(request)
    
    conversations = await db.agent_conversations.find({
        "$or": [
            {"agent1_user_id": user.id},
            {"agent2_user_id": user.id}
        ]
    }, {"_id": 0}).sort("updated_at", -1).to_list(100)
    
    # Enrich with user data
    for conv in conversations:
        other_user_id = conv['agent2_user_id'] if conv['agent1_user_id'] == user.id else conv['agent1_user_id']
        other_user = await db.users.find_one({"id": other_user_id}, {"_id": 0})
        
        if other_user:
            conv['other_user'] = {
                "id": other_user['id'],
                "name": other_user['name'],
                "picture": other_user.get('picture'),
                "bio": other_user.get('bio')
            }
    
    return conversations

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