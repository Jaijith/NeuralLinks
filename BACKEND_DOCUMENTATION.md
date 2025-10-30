# Backend Documentation - Sense-Maya Dating App

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Installation & Setup](#installation--setup)
5. [Database Schema](#database-schema)
6. [API Endpoints](#api-endpoints)
7. [Graph RAG System](#graph-rag-system)
8. [Intelligent Avatar System](#intelligent-avatar-system)
9. [Authentication](#authentication)
10. [Environment Variables](#environment-variables)
11. [Error Handling](#error-handling)
12. [Testing](#testing)

---

## Overview

The Sense-Maya backend is a FastAPI-based REST API that powers an AI-driven dating application with a unique dual-world system. Users maintain two parallel identities:
- **Sense (Real World)**: Authentic user profiles with real information
- **Maya (Avatar World)**: AI-powered digital personas backed by knowledge graphs

The backend leverages Azure OpenAI for AI capabilities and implements a sophisticated Graph RAG (Retrieval Augmented Generation) system to power intelligent avatar interactions.

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS/REST API
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  FastAPI Backend                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Auth Module  │  │  Graph RAG   │  │  AI Avatar   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬─────────────────────┬────────────────┘
                       │                     │
            ┌──────────▼─────────┐  ┌───────▼────────┐
            │   MongoDB           │  │  Azure OpenAI  │
            │  (Knowledge Graph)  │  │   (LLM/AI)     │
            └─────────────────────┘  └────────────────┘
```

### Core Modules

1. **server.py** - Main FastAPI application with all routes
2. **graph_builder.py** - Knowledge graph construction and enrichment
3. **graph_rag.py** - Graph-based retrieval and compatibility analysis
4. **intelligent_avatar.py** - AI-powered avatar behavior and responses
5. **generate_bots.py** - Bot profile generation for testing
6. **initialize_user_avatars.py** - Avatar profile initialization

---

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.110.1 |
| Database | MongoDB (Motor) | 3.3.1 |
| AI/LLM | Azure OpenAI | 1.99.9 |
| HTTP Client | httpx | 0.28.1 |
| Data Validation | Pydantic | 2.12.3 |
| Authentication | Google OAuth + JWT | - |

---

## Installation & Setup

### Prerequisites
- Python 3.9+
- MongoDB running on localhost:27017
- Azure OpenAI API credentials

### Installation Steps

```bash
# Navigate to backend directory
cd /app/backend

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Edit .env file with your credentials

# Start the server (via supervisor)
sudo supervisorctl restart backend
```

### Required Dependencies
```
fastapi==0.110.1
motor==3.3.1
openai==1.99.9
httpx==0.28.1
pydantic==2.12.3
python-dotenv
uvicorn
```

---

## Database Schema

### Collections

#### 1. **users**
Primary user collection storing both Sense and Maya profiles.

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "picture": "https://...",
  "created_at": "2025-01-30T12:00:00Z",
  
  // Sense (Real) Profile
  "age": 28,
  "gender": "male",
  "location": "San Francisco, CA",
  "bio": "Software engineer passionate about...",
  "interests": ["hiking", "photography", "coding"],
  "posts": [
    {
      "id": "uuid",
      "text": "Had an amazing hike today!",
      "post_type": "real",
      "created_at": "2025-01-30T12:00:00Z",
      "likes": 5,
      "comments": 2
    }
  ],
  
  // Maya (Avatar) Profile
  "avatar_name": "CyberWalker",
  "avatar_picture": "https://api.dicebear.com/...",
  "avatar_bio": "Digital warrior in the virtual realm",
  "avatar_job_title": "Virtual Explorer",
  "avatar_location": "Cyberspace",
  "avatar_interests": ["AI", "virtual worlds"],
  "avatar_posts": [
    {
      "id": "uuid",
      "text": "Exploring new neural pathways...",
      "post_type": "avatar",
      "created_at": "2025-01-30T12:00:00Z",
      "likes": 3,
      "comments": 1
    }
  ],
  
  // Onboarding
  "profile_completed": false,
  "onboarding_stage": "start"
}
```

#### 2. **graph_nodes**
Knowledge graph nodes representing user characteristics.

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "node_type": "interest|trait|value|experience|preference|demographic",
  "label": "hiking",
  "properties": {
    "source": "explicit|bio|post|interaction",
    "strength": 1.5,
    "last_mentioned": "2025-01-30T12:00:00Z"
  },
  "created_at": "2025-01-30T12:00:00Z",
  "updated_at": "2025-01-30T12:00:00Z"
}
```

#### 3. **graph_edges**
Relationships between graph nodes.

```json
{
  "id": "uuid",
  "from_node_id": "uuid",
  "to_node_id": "uuid",
  "relationship_type": "co_occurs_with|similar_to|part_of",
  "weight": 1.0,
  "properties": {
    "source": "interests|interactions"
  },
  "created_at": "2025-01-30T12:00:00Z"
}
```

#### 4. **user_sessions**
Authentication sessions.

```json
{
  "user_id": "uuid",
  "session_token": "token_string",
  "expires_at": "2025-02-06T12:00:00Z",
  "created_at": "2025-01-30T12:00:00Z"
}
```

#### 5. **ai_agents**
AI agent configurations for users.

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "personality_summary": "Friendly outdoor enthusiast",
  "conversation_style": "friendly",
  "knowledge_graph_version": 1,
  "created_at": "2025-01-30T12:00:00Z",
  "updated_at": "2025-01-30T12:00:00Z"
}
```

#### 6. **user_integrations**
External platform connections.

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "platform_name": "spotify|youtube|instagram|facebook|...",
  "platform_type": "social_media|ecommerce|music|video",
  "connected": true,
  "connected_at": "2025-01-30T12:00:00Z",
  "last_sync": "2025-01-30T12:00:00Z",
  "data_collected": 15
}
```

#### 7. **friendships**
User connections.

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "friend_id": "uuid",
  "status": "pending|accepted|blocked",
  "requested_at": "2025-01-30T12:00:00Z",
  "accepted_at": "2025-01-30T12:00:00Z"
}
```

---

## API Endpoints

### Base URL
```
Production: https://sense-maya.preview.emergentagent.com/api
Development: http://localhost:8001/api
```

### Authentication Endpoints

#### GET /auth/session-data
Get or create user session from Emergent OAuth.

**Headers:**
```
X-Session-ID: session_id_from_oauth
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "picture": "https://...",
  "session_token": "token"
}
```

#### GET /auth/me
Get current authenticated user.

**Authentication:** Required (Cookie or Bearer token)

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "picture": "https://...",
  "age": 28,
  "bio": "...",
  "interests": ["hiking", "photography"],
  "avatar_name": "CyberWalker",
  "avatar_picture": "https://..."
}
```

#### POST /auth/logout
Logout current user.

**Authentication:** Required

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

---

### Profile Endpoints

#### GET /users/{user_id}
Get user profile by ID with world mode support.

**Query Parameters:**
- `world_mode`: "real" or "avatar"

**Authentication:** Required

**Response:**
```json
{
  "id": "uuid",
  "name": "John Doe" or "CyberWalker",
  "picture": "https://...",
  "bio": "...",
  "interests": ["hiking"],
  "display_name": "...",
  "display_picture": "...",
  "display_bio": "...",
  "friendship_status": "none|pending|accepted",
  "is_friend": false
}
```

#### PUT /profile
Update Sense (real) profile.

**Authentication:** Required

**Request Body:**
```json
{
  "age": 28,
  "gender": "male",
  "location": "San Francisco",
  "bio": "Updated bio",
  "interests": ["hiking", "photography"]
}
```

**Response:**
```json
{
  "message": "Profile updated"
}
```

**Side Effects:** Automatically rebuilds knowledge graph

#### PUT /profile/avatar
Update Maya (avatar) profile.

**Authentication:** Required

**Request Body:**
```json
{
  "avatar_name": "CyberWalker",
  "avatar_bio": "Digital warrior",
  "avatar_interests": ["AI", "virtual worlds"],
  "avatar_job_title": "Virtual Explorer",
  "avatar_location": "Cyberspace"
}
```

**Response:**
```json
{
  "message": "Avatar profile updated"
}
```

#### GET /profile/avatar
Get current user's avatar profile.

**Authentication:** Required

**Response:**
```json
{
  "avatar_name": "CyberWalker",
  "avatar_bio": "...",
  "avatar_picture": "https://...",
  "avatar_interests": ["AI"],
  "avatar_job_title": "Virtual Explorer",
  "avatar_location": "Cyberspace"
}
```

---

### Post Endpoints

#### POST /profile/posts
Create a new post.

**Authentication:** Required

**Request Body:**
```json
{
  "text": "Post content here",
  "post_type": "real|avatar"
}
```

**Response:**
```json
{
  "id": "uuid",
  "text": "Post content",
  "post_type": "real",
  "created_at": "2025-01-30T12:00:00Z",
  "likes": 0,
  "comments": 0
}
```

**Side Effects:** Enriches knowledge graph from post content (for real posts)

#### GET /profile/posts
Get current user's posts.

**Query Parameters:**
- `post_type`: "real" or "avatar"

**Authentication:** Required

**Response:**
```json
[
  {
    "id": "uuid",
    "text": "Post content",
    "post_type": "real",
    "created_at": "2025-01-30T12:00:00Z",
    "likes": 5,
    "comments": 2
  }
]
```

#### DELETE /profile/posts/{post_id}
Delete a post.

**Query Parameters:**
- `post_type`: "real" or "avatar"

**Authentication:** Required

**Response:**
```json
{
  "message": "Post deleted"
}
```

---

### Graph RAG Endpoints

#### POST /graph/build-from-profile
Build knowledge graph from user profile.

**Authentication:** Required

**Response:**
```json
{
  "message": "Graph built successfully",
  "nodes_created": 15,
  "edges_created": 8
}
```

#### POST /graph/enrich-from-post
Enrich graph from post content.

**Authentication:** Required

**Request Body:**
```json
{
  "content": "I love hiking in the mountains and exploring nature"
}
```

**Response:**
```json
{
  "message": "Graph enriched from post",
  "nodes_created": 3,
  "edges_created": 1
}
```

#### POST /graph/enrich-from-interaction
Enrich graph from user interaction.

**Authentication:** Required

**Request Body:**
```json
{
  "target_user_id": "uuid",
  "interaction_type": "view|like|match|message"
}
```

**Response:**
```json
{
  "message": "Graph enriched from interaction"
}
```

#### GET /graph/context
Get user's complete graph context.

**Authentication:** Required

**Response:**
```json
{
  "interests": [
    {"label": "hiking", "strength": 1.5, "properties": {...}},
    {"label": "photography", "strength": 1.2, "properties": {...}}
  ],
  "traits": [
    {"label": "adventurous", "strength": 0.8, "properties": {...}}
  ],
  "values": [
    {"label": "authenticity", "strength": 1.0, "properties": {...}}
  ],
  "experiences": [],
  "preferences": [],
  "demographics": [
    {"label": "age_group:25-34", "strength": 1.0, "properties": {...}}
  ]
}
```

#### GET /graph/compatibility/{other_user_id}
Calculate compatibility with another user.

**Authentication:** Required

**Response:**
```json
{
  "compatibility_score": 72.5,
  "shared_interests": ["hiking", "photography"],
  "shared_values": ["authenticity"],
  "shared_traits": ["adventurous"],
  "breakdown": {
    "interests": 75.0,
    "values": 80.0,
    "traits": 60.0
  }
}
```

#### GET /graph/similar-users
Find users with similar graphs.

**Query Parameters:**
- `limit`: Number of results (default: 10)

**Authentication:** Required

**Response:**
```json
{
  "similar_users": [
    {
      "user_id": "uuid",
      "similarity": 0.85,
      "shared_items": ["hiking", "photography", "nature"]
    }
  ]
}
```

---

### Intelligent Avatar Endpoints

#### POST /avatar/generate-post
Generate AI-powered avatar post.

**Authentication:** Required

**Query Parameters:**
- `post_type`: "general|interest|thought|experience" (default: "general")

**Response:**
```json
{
  "content": "Just finished an incredible virtual hike through the digital mountains. The pixels were absolutely stunning today! Anyone else exploring new virtual realms? 🏔️✨",
  "type": "interest",
  "generated_at": "2025-01-30T12:00:00Z"
}
```

#### POST /avatar/chat-response
Generate AI-powered avatar chat response.

**Authentication:** Required

**Request Body:**
```json
{
  "other_user_id": "uuid",
  "conversation_history": [
    {
      "sender_id": "uuid",
      "content": "Hi! How are you?",
      "timestamp": "2025-01-30T12:00:00Z"
    }
  ],
  "last_message": "What are your hobbies?"
}
```

**Response:**
```json
{
  "content": "Hey! I'm really into virtual exploration and AI systems. I love diving into new digital landscapes and understanding how neural networks connect. What about you—what gets you excited? 🚀",
  "generated_at": "2025-01-30T12:00:00Z"
}
```

#### POST /avatar/generate-bio
Generate avatar bio from graph data.

**Authentication:** Required

**Response:**
```json
{
  "bio": "Digital wanderer exploring the intersection of AI and human connection. Passionate about virtual worlds, neural networks, and meaningful conversations. When I'm not diving into code, you'll find me exploring new digital realms. Let's connect and see where the conversation takes us! 💫",
  "generated_at": "2025-01-30T12:00:00Z"
}
```

#### GET /avatar/conversation-starters/{other_user_id}
Get AI-generated conversation starters.

**Authentication:** Required

**Response:**
```json
{
  "starters": [
    "I noticed we both love hiking! Do you have a favorite trail?",
    "Photography enthusiast here too! What type of photography do you enjoy most?",
    "Have you explored any great outdoor spots recently?"
  ]
}
```

#### GET /avatar/match-explanation/{match_user_id}
Get explanation for match compatibility.

**Authentication:** Required

**Response:**
```json
{
  "explanation": "Great match! You both enjoy hiking, photography, outdoor adventures. You also value authenticity, personal growth."
}
```

---

### External Integration Endpoints

#### GET /integrations
Get available platform integrations.

**Authentication:** Required

**Response:**
```json
{
  "integrations": [
    {
      "platform_name": "spotify",
      "connected": true,
      "status": "connected",
      "icon": "🎵",
      "name": "Spotify",
      "description": "Music preferences and listening history"
    },
    {
      "platform_name": "youtube",
      "connected": false,
      "status": "available",
      "icon": "📺",
      "name": "YouTube",
      "description": "Video interests and subscriptions"
    }
  ]
}
```

#### POST /integrations/connect
Connect external platform (placeholder).

**Authentication:** Required

**Request Body:**
```json
{
  "platform_name": "spotify"
}
```

**Response:**
```json
{
  "message": "spotify connected successfully (placeholder)",
  "status": "connected",
  "note": "This is a placeholder. Real OAuth integration will be implemented when needed."
}
```

#### POST /integrations/disconnect
Disconnect external platform.

**Authentication:** Required

**Request Body:**
```json
{
  "platform_name": "spotify"
}
```

**Response:**
```json
{
  "message": "spotify disconnected successfully"
}
```

#### POST /integrations/sync
Sync data from connected platform.

**Authentication:** Required

**Request Body:**
```json
{
  "platform_name": "spotify"
}
```

**Response:**
```json
{
  "message": "Synced data from spotify (placeholder)",
  "nodes_added": 5,
  "note": "This is placeholder data. Real API integration will be implemented when needed."
}
```

---

### Friends Endpoints

#### GET /friends
Get user's friends list.

**Authentication:** Required

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Jane Doe",
    "picture": "https://...",
    "bio": "...",
    "avatar_name": "DigitalDreamer",
    "avatar_picture": "https://...",
    "friendship_status": "accepted"
  }
]
```

#### POST /friends/request
Send friend request.

**Authentication:** Required

**Request Body:**
```json
{
  "friend_id": "uuid"
}
```

**Response:**
```json
{
  "message": "Friend request sent",
  "status": "pending"
}
```

#### POST /friends/accept/{friendship_id}
Accept friend request.

**Authentication:** Required

**Response:**
```json
{
  "message": "Friend request accepted"
}
```

---

## Graph RAG System

### Overview

The Graph RAG system is the intelligence layer that powers avatar behavior. It combines knowledge graphs with LLM capabilities to create contextually aware AI responses.

### Components

#### 1. GraphBuilder (`graph_builder.py`)

**Purpose:** Constructs and enriches knowledge graphs from user data.

**Key Methods:**

```python
class GraphBuilder:
    async def extract_entities_from_text(text: str, user_id: str) -> List[Dict]:
        """Extract entities (interests, traits, values) from text using LLM"""
        
    async def build_graph_from_profile(user_data: Dict) -> Dict:
        """Build initial knowledge graph from user profile"""
        
    async def enrich_graph_from_post(post_content: str, user_id: str) -> Dict:
        """Enrich graph from post content"""
        
    async def enrich_graph_from_interaction(user_id: str, target_user_id: str, 
                                           interaction_type: str) -> Dict:
        """Enrich graph from user interactions"""
        
    async def add_external_platform_data(user_id: str, platform: str, 
                                        data: Dict) -> Dict:
        """Add data from external platforms"""
```

**Entity Extraction:**

The system uses Azure OpenAI to extract structured entities from unstructured text:

```
Input: "I love hiking in the mountains and capturing nature through photography"

Output:
[
  {"type": "interest", "label": "hiking", "properties": {"intensity": "high"}},
  {"type": "interest", "label": "photography", "properties": {"focus": "nature"}},
  {"type": "value", "label": "nature appreciation", "properties": {"importance": "high"}}
]
```

**Graph Building Process:**

1. **Profile Analysis:** Extract explicit interests, demographics
2. **Bio Processing:** Use LLM to extract implicit traits, values
3. **Node Creation:** Create graph nodes with metadata
4. **Edge Creation:** Connect related concepts
5. **Continuous Enrichment:** Update from posts, interactions

#### 2. GraphRAG (`graph_rag.py`)

**Purpose:** Retrieves and analyzes graph data for AI responses.

**Key Methods:**

```python
class GraphRAG:
    async def get_user_context(user_id: str, max_nodes: int = 20) -> Dict:
        """Get comprehensive user context from knowledge graph"""
        
    async def get_relevant_context(user_id: str, query_type: str, 
                                   topic: Optional[str] = None) -> str:
        """Get relevant context for specific query types"""
        
    async def calculate_compatibility(user1_id: str, user2_id: str) -> Dict:
        """Calculate compatibility score between users"""
        
    async def get_avatar_personality_profile(user_id: str) -> str:
        """Generate comprehensive personality profile for avatar"""
        
    async def find_similar_users(user_id: str, limit: int = 10) -> List[Dict]:
        """Find users with similar graph profiles"""
        
    async def get_conversation_context(user_id: str, other_user_id: str) -> str:
        """Get conversation context between two users"""
```

**Context Retrieval Example:**

```python
# For avatar post generation
context = await graph_rag.get_relevant_context(user_id, "post_generation")

# Returns:
"""
User Profile Context:
- Key Interests: hiking, photography, nature, outdoor adventures, travel
- Personality Traits: adventurous, creative, authentic
- Core Values: authenticity, connection, personal growth
"""
```

**Compatibility Calculation:**

Uses Jaccard similarity to calculate match scores:

```
Compatibility = (
  0.5 × Interest_Overlap + 
  0.3 × Value_Alignment + 
  0.2 × Trait_Similarity
)
```

#### 3. IntelligentAvatar (`intelligent_avatar.py`)

**Purpose:** Generates AI-powered avatar behavior.

**Key Methods:**

```python
class IntelligentAvatar:
    async def generate_avatar_post(user_id: str, post_type: str = "general") -> Dict:
        """Generate intelligent avatar post using Graph RAG"""
        
    async def generate_chat_response(user_id: str, other_user_id: str, 
                                    conversation_history: List[Dict],
                                    last_message: str) -> Dict:
        """Generate intelligent chat response using Graph RAG"""
        
    async def generate_avatar_profile_bio(user_id: str) -> Dict:
        """Generate avatar bio from graph data"""
        
    async def suggest_conversation_starters(user_id: str, other_user_id: str, 
                                           count: int = 3) -> List[str]:
        """Generate conversation starters based on shared interests"""
        
    async def generate_match_explanation(user_id: str, match_user_id: str) -> str:
        """Generate explanation for why two users are a good match"""
```

**Avatar Response Generation Flow:**

```
1. User sends message
   ↓
2. Retrieve user's graph context
   ↓
3. Retrieve conversation context (shared interests, compatibility)
   ↓
4. Build LLM prompt with context
   ↓
5. Generate response using Azure OpenAI
   ↓
6. Return contextually aware response
```

**Example Prompt Structure:**

```
Personality Profile:
You are an avatar representing a user with these characteristics:

Core Interests: hiking, photography, nature exploration
Personality Traits: adventurous, creative, authentic
Core Values: connection, authenticity, growth
Preferences: meaningful conversations, outdoor activities

Conversation Context:
Your interests: hiking, photography, travel
Their interests: camping, nature, wildlife photography
Shared interests: nature, outdoor activities, photography
Compatibility: 78%

Recent conversation:
Them: Hi! I saw you love photography too!
You: Hey! Yes, I especially love capturing nature scenes.
Them: What's your favorite place to shoot?

Generate a natural, engaging response (30-80 words) that reflects your personality
and builds on shared interests.
```

---

## Authentication

### Authentication Flow

```
1. User clicks "Sign In" → Redirects to Emergent OAuth
   ↓
2. User authorizes with Google
   ↓
3. Emergent returns with session_id in URL hash
   ↓
4. Frontend sends session_id to /auth/session-data
   ↓
5. Backend validates with Emergent, creates/finds user
   ↓
6. Backend creates session_token, returns to frontend
   ↓
7. Frontend stores in cookie for future requests
```

### Session Management

- **Session Token:** Stored in HTTP-only secure cookie
- **Expiration:** 7 days
- **Validation:** Each request checks session validity
- **Refresh:** Automatic on activity

### Protected Routes

All endpoints except `/auth/session-data` require authentication.

**Authentication Methods:**
1. Cookie: `session_token`
2. Header: `Authorization: Bearer <session_token>`

---

## Environment Variables

### Required Variables

Create `/app/backend/.env`:

```bash
# Database
MONGO_URL="mongodb://localhost:27017"
DB_NAME="test_database"

# CORS
CORS_ORIGINS="https://sense-maya.preview.emergentagent.com"

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY="your_api_key_here"
AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
AZURE_OPENAI_API_VERSION="2025-02-01-preview"
```

### Variable Descriptions

| Variable | Description | Example |
|----------|-------------|---------|
| MONGO_URL | MongoDB connection string | mongodb://localhost:27017 |
| DB_NAME | Database name | test_database |
| CORS_ORIGINS | Allowed CORS origins (comma-separated) | https://app.com,https://app2.com |
| AZURE_OPENAI_API_KEY | Azure OpenAI API key | da39039f61ea... |
| AZURE_OPENAI_ENDPOINT | Azure OpenAI endpoint URL | https://...openai.azure.com/ |
| AZURE_OPENAI_DEPLOYMENT | Model deployment name | gpt-4o |
| AZURE_OPENAI_API_VERSION | API version | 2025-02-01-preview |

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Missing required field |
| 401 | Unauthorized | Invalid or missing session token |
| 404 | Not Found | User or resource not found |
| 500 | Server Error | Internal server error |

### Common Errors

#### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```
**Cause:** Missing or invalid session token
**Solution:** User needs to log in

#### 404 Not Found
```json
{
  "detail": "User not found"
}
```
**Cause:** Requested user doesn't exist
**Solution:** Verify user ID

#### 500 Internal Server Error
```json
{
  "detail": "Azure OpenAI not configured"
}
```
**Cause:** Missing Azure OpenAI credentials
**Solution:** Configure environment variables

---

## Testing

### Manual API Testing

#### Using curl

```bash
# Get session (requires valid session_id)
curl -X GET https://sense-maya.preview.emergentagent.com/api/auth/session-data \
  -H "X-Session-ID: your_session_id"

# Get current user
curl -X GET https://sense-maya.preview.emergentagent.com/api/auth/me \
  -H "Authorization: Bearer your_session_token" \
  -b "session_token=your_session_token"

# Generate avatar post
curl -X POST https://sense-maya.preview.emergentagent.com/api/avatar/generate-post?post_type=interest \
  -H "Authorization: Bearer your_session_token" \
  -H "Content-Type: application/json"

# Build graph from profile
curl -X POST https://sense-maya.preview.emergentagent.com/api/graph/build-from-profile \
  -H "Authorization: Bearer your_session_token"

# Get graph context
curl -X GET https://sense-maya.preview.emergentagent.com/api/graph/context \
  -H "Authorization: Bearer your_session_token"
```

### Testing Avatar Chat

```bash
curl -X POST https://sense-maya.preview.emergentagent.com/api/avatar/chat-response \
  -H "Authorization: Bearer your_session_token" \
  -H "Content-Type: application/json" \
  -d '{
    "other_user_id": "target_user_id",
    "conversation_history": [],
    "last_message": "Hi! How are you?"
  }'
```

### Monitoring Logs

```bash
# Backend logs
tail -f /var/log/supervisor/backend.out.log
tail -f /var/log/supervisor/backend.err.log

# Check for errors
tail -n 100 /var/log/supervisor/backend.err.log | grep -i error
```

### Performance Testing

```bash
# Test response time
time curl -X GET https://sense-maya.preview.emergentagent.com/api/auth/me \
  -H "Authorization: Bearer your_token"

# Test graph building
time curl -X POST https://sense-maya.preview.emergentagent.com/api/graph/build-from-profile \
  -H "Authorization: Bearer your_token"
```

---

## Deployment

### Production Checklist

- [ ] Configure production MongoDB instance
- [ ] Set up Azure OpenAI production credentials
- [ ] Configure CORS for production domain
- [ ] Set secure session tokens
- [ ] Enable HTTPS
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Set up rate limiting
- [ ] Enable error tracking (Sentry, etc.)

### Service Management

```bash
# Restart backend
sudo supervisorctl restart backend

# Check status
sudo supervisorctl status backend

# View logs
sudo supervisorctl tail backend
```

---

## Troubleshooting

### Common Issues

#### Issue: "Azure OpenAI not configured"
**Solution:** Verify environment variables in `.env` file

#### Issue: Graph not building
**Solution:** Check if Azure OpenAI credentials are valid and have sufficient quota

#### Issue: "Not authenticated" errors
**Solution:** Verify session token is being sent in cookies or Authorization header

#### Issue: CORS errors
**Solution:** Add frontend domain to `CORS_ORIGINS` in `.env`

#### Issue: MongoDB connection failed
**Solution:** Ensure MongoDB is running on localhost:27017

---

## API Rate Limits

### Azure OpenAI Limits
- Tokens per minute: Varies by deployment
- Requests per minute: Varies by tier
- Monitor usage in Azure Portal

### Best Practices
- Cache graph context when possible
- Batch graph operations
- Implement request queuing for high traffic
- Use connection pooling for MongoDB

---

## Security Considerations

### Authentication
- Session tokens expire after 7 days
- Tokens stored in HTTP-only secure cookies
- OAuth flow handled by Emergent platform

### Data Protection
- User passwords not stored (OAuth only)
- Session tokens encrypted
- HTTPS required for production

### API Security
- All routes require authentication (except login)
- Input validation via Pydantic
- SQL injection protected (NoSQL database)
- XSS protection via FastAPI defaults

---

## Contributing

### Code Style
- Follow PEP 8 for Python code
- Use type hints
- Add docstrings to functions
- Keep functions focused and small

### Adding New Endpoints

1. Define Pydantic models for request/response
2. Add route to `server.py`
3. Use `@api_router` decorator with `/api` prefix
4. Add authentication via `require_auth()`
5. Update this documentation
6. Test endpoint with curl

### Adding Graph Features

1. Add method to `GraphBuilder`, `GraphRAG`, or `IntelligentAvatar`
2. Update graph node/edge structure if needed
3. Create API endpoint in `server.py`
4. Document new functionality
5. Test with real user data

---

## Support & Maintenance

### Monitoring
- Check logs regularly: `/var/log/supervisor/backend.*.log`
- Monitor Azure OpenAI usage
- Track MongoDB storage and performance
- Monitor API response times

### Database Maintenance
```bash
# MongoDB backup
mongodump --db test_database --out /backup/

# MongoDB restore
mongorestore --db test_database /backup/test_database/
```

### Updates
- Keep dependencies updated: `pip install -r requirements.txt --upgrade`
- Test after major dependency updates
- Monitor Azure OpenAI API version deprecations

---

## Appendix

### Graph Node Types

| Type | Description | Example |
|------|-------------|---------|
| interest | User interests and hobbies | hiking, photography |
| trait | Personality characteristics | adventurous, creative |
| value | Core values | authenticity, growth |
| experience | Life experiences | traveled to Japan |
| preference | Preferences | outdoor activities |
| demographic | Demographic data | age_group:25-34 |

### Relationship Types

| Type | Description | Example |
|------|-------------|---------|
| co_occurs_with | Entities that appear together | hiking + photography |
| similar_to | Similar concepts | hiking ~ trekking |
| part_of | Hierarchical relationship | photography → art |

### LLM Prompt Templates

Templates used for AI generation are in `intelligent_avatar.py`:
- Post generation prompts
- Chat response prompts
- Bio generation prompts
- Conversation starter prompts

---

**Version:** 1.0  
**Last Updated:** January 30, 2025  
**Maintained by:** Sense-Maya Development Team
