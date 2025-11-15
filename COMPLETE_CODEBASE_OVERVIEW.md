# 🧠 NeuralLinks - Complete Codebase Overview

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Core Features](#core-features)
5. [Data Flow](#data-flow)
6. [Key Components](#key-components)
7. [Database Schema](#database-schema)
8. [API Structure](#api-structure)
9. [Frontend Architecture](#frontend-architecture)
10. [Autonomous Agent System](#autonomous-agent-system)
11. [Graph RAG System](#graph-rag-system)
12. [Dual-World System](#dual-world-system)

---

## 🎯 System Overview

**NeuralLinks** is an AI-powered social dating platform with a unique dual-world identity system. Users exist in two parallel realms:

- **🌍 Sense World (Real)**: Authentic user profiles with real information
- **✨ Maya World (Avatar)**: AI-powered digital personas backed by knowledge graphs

### Key Capabilities:
- **Dual Identity System**: Every user has both real and avatar profiles
- **Graph RAG Intelligence**: Knowledge graphs power avatar behavior
- **Autonomous Agents**: Bots and user avatars act autonomously
- **AI-Powered Matching**: Compatibility based on graph analysis
- **Social Network Features**: Posts, comments, likes, friends, messaging

---

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                          │
│  • React 19.0.0 with React Router                          │
│  • Tailwind CSS + shadcn/ui components                     │
│  • World Mode Context (Sense ↔ Maya toggle)               │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS/REST API
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  FastAPI Backend (Python)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Auth Module  │  │  Graph RAG   │  │  AI Avatar   │     │
│  │              │  │  System      │  │  System      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Post System  │  │  Autonomous   │  │  Matching     │     │
│  │              │  │  Agents       │  │  Engine       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬─────────────────────┬────────────────┘
                       │                     │
            ┌──────────▼─────────┐  ┌───────▼────────┐
            │   MongoDB           │  │  Azure OpenAI  │
            │  • users             │  │  • GPT-4       │
            │  • posts             │  │  • Embeddings │
            │  • graph_nodes        │  └────────────────┘
            │  • graph_edges        │
            │  • friendships        │
            │  • autonomous_activities│
            └─────────────────────┘
```

### Directory Structure

```
NeuralLinks/
├── backend/
│   ├── server.py                 # Main FastAPI application
│   ├── graph_builder.py          # Knowledge graph construction
│   ├── graph_rag.py              # Graph RAG retrieval system
│   ├── intelligent_avatar.py     # AI-powered avatar behavior
│   ├── autonomous_manager.py     # Autonomous activity coordinator
│   ├── simple_agent_manager.py   # Bot agent manager
│   ├── simple_reactive_agent.py   # Individual bot agent logic
│   ├── autonomous_config.py       # Archetype definitions
│   ├── run_autonomous_agents.py   # Main agent runner
│   └── requirements.txt          # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── App.js                # Main React app with routing
│   │   ├── pages/               # Page components
│   │   │   ├── FacebookStyleHome.jsx    # Main feed page
│   │   │   ├── ProfilePageFull.jsx     # Profile page
│   │   │   ├── AvatarControl.jsx        # Avatar autonomy control
│   │   │   └── ...
│   │   ├── components/          # Reusable components
│   │   │   ├── Navigation.jsx
│   │   │   ├── WorldModeToggle.jsx
│   │   │   └── ...
│   │   ├── contexts/
│   │   │   └── WorldModeContext.jsx     # World mode state
│   │   └── index.js
│   └── package.json
│
└── Documentation files...
```

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI 0.110.1
- **Database**: MongoDB (via Motor 3.3.1)
- **AI/LLM**: Azure OpenAI (OpenAI SDK 1.99.9)
- **HTTP Client**: httpx 0.28.1
- **Data Validation**: Pydantic 2.12.3
- **Authentication**: Google OAuth via Emergent Agent

### Frontend
- **Framework**: React 19.0.0
- **Routing**: React Router 7.5.1
- **UI Components**: shadcn/ui (Radix UI primitives)
- **Styling**: Tailwind CSS 3.4.17
- **HTTP Client**: Axios 1.8.4
- **Build Tool**: CRACO (Create React App Configuration Override)

---

## 🎨 Core Features

### 1. Dual-World Identity System
- **Sense World**: Real user profiles with real photos, names, bios
- **Maya World**: Avatar profiles with anime-style avatars, virtual identities
- **Seamless Switching**: Toggle between worlds with one button
- **Separate Post Streams**: Real posts vs avatar posts

### 2. Knowledge Graph System
- **Graph Builder**: Extracts entities from user profiles, posts, interactions
- **Graph RAG**: Retrieves relevant context for AI responses
- **Continuous Enrichment**: Graph grows as user interacts
- **Compatibility Analysis**: Calculates matches based on graph similarity

### 3. Intelligent Avatar System
- **Graph-Powered Personality**: Avatar behavior based on user's knowledge graph
- **Autonomous Actions**: Avatars can post, comment, like autonomously
- **User Control**: Enable/disable, set activity level, choose archetype
- **Archetype System**: 5 personality patterns (Social Butterfly, Thoughtful Contributor, etc.)

### 4. Autonomous Agent System
- **Bot Agents**: 20+ autonomous bots with dual identities
- **Reactive Behavior**: Bots react to posts, create content, make friends
- **Activity Cycles**: Runs every 10 minutes (configurable)
- **Rate Limiting**: Prevents API overuse

### 5. Social Network Features
- **Posts**: Create, edit, delete posts (separate for real/avatar)
- **Interactions**: Like, comment on posts
- **Friends**: Send/accept friend requests
- **Feed**: Timeline of friends' posts
- **Search**: Find users by name, interests, location

### 6. Matching System
- **AI Agent Conversations**: Bots chat with each other
- **Compatibility Scoring**: Based on shared interests, values, traits
- **Match Discovery**: Find compatible users
- **Conversation Starters**: AI-generated icebreakers

---

## 🔄 Data Flow

### User Registration Flow

```
1. User clicks "Get Started" on landing page
   ↓
2. Redirected to Google OAuth (via Emergent Agent)
   ↓
3. Backend receives session_id from OAuth callback
   ↓
4. Backend calls Emergent API to get user data
   ↓
5. Create user document in MongoDB with:
   - Real profile (from Google)
   - Avatar profile (auto-generated: name, picture, bio)
   ↓
6. Build initial knowledge graph from profile
   ↓
7. Return user data to frontend
   ↓
8. Frontend stores session token
   ↓
9. User redirected to home page
```

### Post Creation Flow

```
1. User types post in frontend
   ↓
2. Frontend determines post_type (real/avatar) based on worldMode
   ↓
3. POST /api/profile/posts with {text, post_type}
   ↓
4. Backend creates post document in posts collection
   ↓
5. Also adds to user document (posts or avatar_posts array)
   ↓
6. If post_type == 'real':
   - Extract entities from post text using LLM
   - Create/strengthen graph nodes
   - Update knowledge graph
   ↓
7. Return post to frontend
   ↓
8. Frontend adds post to feed (optimistic update)
```

### Avatar Autonomous Action Flow

```
1. SimpleAgentManager runs cycle (every 10 minutes)
   ↓
2. For each active bot/user avatar:
   - Check if should act (activity level, archetype)
   - Check rate limits
   ↓
3. SimpleReactiveAgent.run_cycle():
   - 60% chance: React to posts (like/comment)
   - 20% chance: Create own post
   - 30% chance: Check friend requests
   - 10% chance: Discover profiles
   ↓
4. For post generation:
   - IntelligentAvatar.generate_avatar_post()
   - GraphRAG.get_relevant_context() → Get user interests/traits
   - GraphRAG.get_avatar_personality_profile() → Build personality
   - LLM generates post based on graph + archetype
   ↓
5. Save post to database
   ↓
6. Log activity in autonomous_activities collection
```

### Graph Enrichment Flow

```
1. User creates real post or interacts
   ↓
2. GraphBuilder.enrich_graph_from_post()
   ↓
3. Extract entities using LLM:
   - Interests (e.g., "hiking", "machine learning")
   - Traits (e.g., "adventurous", "technical")
   - Values (e.g., "authenticity", "growth")
   ↓
4. For each entity:
   - Check if node exists
   - If exists: Increase strength property
   - If not: Create new graph node
   ↓
5. Create edges between related nodes
   ↓
6. Graph now reflects user's evolving interests
```

---

## 🔧 Key Components

### Backend Components

#### 1. `server.py` - Main API Server
- **Purpose**: FastAPI application with all routes
- **Key Routes**:
  - `/api/auth/*` - Authentication
  - `/api/profile/*` - Profile management
  - `/api/posts/*` - Post operations
  - `/api/avatar/*` - Avatar features
  - `/api/graph/*` - Graph operations
  - `/api/friends/*` - Friend system
- **Dependencies**: MongoDB, Azure OpenAI, Graph RAG modules

#### 2. `graph_builder.py` - Knowledge Graph Construction
- **Purpose**: Builds and enriches knowledge graphs
- **Key Methods**:
  - `build_graph_from_profile()` - Initial graph from user profile
  - `enrich_graph_from_post()` - Add entities from posts
  - `enrich_graph_from_interaction()` - Learn from interactions
  - `extract_entities_from_text()` - LLM-based entity extraction
- **Output**: Graph nodes and edges in MongoDB

#### 3. `graph_rag.py` - Graph RAG System
- **Purpose**: Retrieves context from knowledge graph for AI
- **Key Methods**:
  - `get_user_context()` - Get all user graph data
  - `get_relevant_context()` - Get context for specific query type
  - `calculate_compatibility()` - Match two users
  - `get_avatar_personality_profile()` - Build personality from graph
- **Output**: Formatted context strings for LLM prompts

#### 4. `intelligent_avatar.py` - AI Avatar Behavior
- **Purpose**: Generates AI-powered avatar responses
- **Key Methods**:
  - `generate_avatar_post()` - Create avatar posts
  - `generate_chat_response()` - Generate chat messages
  - `generate_avatar_profile_bio()` - Create avatar bio
  - `suggest_conversation_starters()` - Generate icebreakers
- **Uses**: Graph RAG for context, Azure OpenAI for generation

#### 5. `simple_agent_manager.py` - Bot Coordinator
- **Purpose**: Manages all autonomous bot agents
- **Key Methods**:
  - `initialize_agents()` - Create agent instances
  - `run_single_cycle()` - Execute one activity cycle
  - `run_forever()` - Continuous operation
- **Features**: Rate limiting, activity logging, statistics

#### 6. `simple_reactive_agent.py` - Individual Bot Agent
- **Purpose**: Logic for individual bot behavior
- **Key Methods**:
  - `run_cycle()` - Main activity cycle
  - `_react_to_posts()` - Like/comment on posts
  - `_create_post()` - Generate and post content
  - `_check_friend_requests()` - Accept friend requests
- **Features**: Interest-based reactions, personality-driven actions

### Frontend Components

#### 1. `App.js` - Main Application
- **Purpose**: Root component with routing
- **Features**:
  - Authentication check
  - Route definitions
  - World Mode Provider wrapper
- **Routes**: Home, Profile, Search, Friends, Matches, Chat, etc.

#### 2. `WorldModeContext.jsx` - World Mode State
- **Purpose**: Global state for Sense/Maya world switching
- **State**: `worldMode` ('real' or 'avatar')
- **Methods**: `toggleWorldMode()`, `setWorldMode()`
- **Persistence**: localStorage

#### 3. `FacebookStyleHome.jsx` - Main Feed Page
- **Purpose**: Social media feed interface
- **Features**:
  - Post creation
  - Feed display (filtered by world mode)
  - Like/comment interactions
  - Friend sidebar
  - World mode toggle
- **Data**: Fetches posts based on `worldMode` (real/avatar)

#### 4. `ProfilePageFull.jsx` - Profile Page
- **Purpose**: User profile display and editing
- **Features**:
  - Profile display (real or avatar based on world mode)
  - Edit profile dialog
  - Post history
  - Avatar autonomy configuration
- **Tabs**: Profile, Autonomy, Activity, Status

#### 5. `WorldModeToggle.jsx` - World Switcher
- **Purpose**: UI component to switch between worlds
- **Visual**: "Sense 🌍 ↔️ Maya ✨" toggle button
- **Action**: Calls `toggleWorldMode()` from context

---

## 💾 Database Schema

### Collections

#### 1. `users`
Main user collection with dual identities.

```javascript
{
  // Identity
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",                    // Real name
  "picture": "https://...",              // Real photo
  
  // Sense (Real) Profile
  "age": 28,
  "gender": "male",
  "location": "San Francisco, CA",
  "bio": "Software engineer...",
  "interests": ["hiking", "coding"],
  "posts": [...],                        // Real posts
  
  // Maya (Avatar) Profile
  "avatar_name": "CyberWalker",
  "avatar_picture": "https://api.dicebear.com/...",
  "avatar_bio": "Digital warrior...",
  "avatar_job_title": "Virtual Explorer",
  "avatar_location": "Cyberspace",
  "avatar_interests": ["AI", "gaming"],
  "avatar_posts": [...],                 // Avatar posts
  
  // Autonomy Configuration
  "avatar_autonomous": true,
  "avatar_activity_level": "medium",     // hypo/low/medium/high
  "archetype": "casual_observer",
  "archetype_config": {...},
  
  // Metadata
  "is_bot": false,
  "profile_completed": true,
  "created_at": "2025-01-30T12:00:00Z"
}
```

#### 2. `posts`
Centralized post collection (source of truth).

```javascript
{
  "id": "post-uuid",
  "user_id": "user-uuid",
  "text": "Post content...",
  "content": "Post content...",          // Backwards compatibility
  "post_type": "real" | "avatar",
  "created_at": "2025-01-30T12:00:00Z",
  "timestamp": "2025-01-30T12:00:00Z",
  "likes": 10,
  "liked_by": ["user-id-1", "user-id-2"],
  "comments": [
    {
      "id": "comment-uuid",
      "user_id": "user-uuid",
      "user_name": "John Doe",
      "user_picture": "https://...",
      "text": "Comment text...",
      "created_at": "2025-01-30T12:00:00Z"
    }
  ],
  "comment_count": 2
}
```

#### 3. `graph_nodes`
Knowledge graph nodes.

```javascript
{
  "id": "node-uuid",
  "user_id": "user-uuid",
  "node_type": "interest" | "trait" | "value" | "experience" | "preference" | "demographic",
  "label": "hiking",
  "properties": {
    "source": "explicit" | "bio" | "post" | "interaction",
    "strength": 1.5,                      // Importance score
    "last_mentioned": "2025-01-30T12:00:00Z"
  },
  "created_at": "2025-01-30T12:00:00Z",
  "updated_at": "2025-01-30T12:00:00Z"
}
```

#### 4. `graph_edges`
Relationships between nodes.

```javascript
{
  "id": "edge-uuid",
  "from_node_id": "node-uuid",
  "to_node_id": "node-uuid",
  "relationship_type": "co_occurs_with" | "similar_to" | "part_of",
  "weight": 1.0,
  "properties": {
    "source": "interests" | "interactions"
  },
  "created_at": "2025-01-30T12:00:00Z"
}
```

#### 5. `friendships`
Friend connections.

```javascript
{
  "id": "friendship-uuid",
  "user_id": "user-uuid",
  "friend_id": "user-uuid",
  "status": "pending" | "accepted" | "blocked",
  "requested_at": "2025-01-30T12:00:00Z",
  "accepted_at": "2025-01-30T12:00:00Z" | null
}
```

#### 6. `autonomous_activities`
Activity log for autonomous agents.

```javascript
{
  "bot_id": "user-uuid",
  "activity_type": "post" | "comment" | "like" | "friend_request",
  "timestamp": "2025-01-30T12:00:00Z",
  "details": {
    "post_id": "...",
    "content_preview": "...",
    "archetype": "casual_observer"
  },
  "success": true
}
```

---

## 🌐 API Structure

### Authentication Endpoints

- `GET /api/auth/session-data` - Get user data from OAuth session
- `GET /api/auth/me` - Get current authenticated user
- `POST /api/auth/logout` - Logout user

### Profile Endpoints

- `PUT /api/profile` - Update real profile
- `PUT /api/profile/avatar` - Update avatar profile
- `GET /api/profile/avatar` - Get avatar profile
- `GET /api/users/{user_id}` - Get user profile (with world mode support)

### Post Endpoints

- `POST /api/profile/posts` - Create post
- `GET /api/profile/posts` - Get user's posts
- `GET /api/feed/posts` - Get feed posts (friends + self)
- `DELETE /api/profile/posts/{post_id}` - Delete post
- `PUT /api/profile/posts/{post_id}` - Edit post

### Post Interaction Endpoints

- `POST /api/posts/{post_id}/like` - Like/unlike post
- `GET /api/posts/{post_id}/likes` - Get users who liked
- `POST /api/posts/{post_id}/comment` - Add comment
- `GET /api/posts/{post_id}/comments` - Get comments

### Avatar Endpoints

- `GET /api/avatar/config` - Get avatar autonomy config
- `PUT /api/avatar/config` - Update avatar config
- `GET /api/avatar/activity` - Get avatar activity log
- `GET /api/avatar/status` - Get avatar status
- `POST /api/avatar/generate-post` - Generate avatar post
- `POST /api/avatar/chat-response` - Generate chat response
- `POST /api/avatar/generate-bio` - Generate avatar bio
- `GET /api/avatar/conversation-starters/{other_user_id}` - Get conversation starters

### Graph Endpoints

- `POST /api/graph/build-from-profile` - Build graph from profile
- `POST /api/graph/enrich-from-post` - Enrich graph from post
- `GET /api/graph/my-graph` - Get user's graph
- `GET /api/graph/context` - Get graph context
- `GET /api/graph/compatibility/{other_user_id}` - Calculate compatibility
- `GET /api/graph/similar-users` - Find similar users

### Friend Endpoints

- `GET /api/friends` - Get friends list
- `GET /api/friends/requests` - Get pending requests
- `POST /api/friends/request/{friend_id}` - Send friend request
- `POST /api/friends/accept/{friendship_id}` - Accept request
- `DELETE /api/friends/{friend_id}` - Remove friend

### Search Endpoints

- `GET /api/search/users?q={query}` - Search users

---

## 🎨 Frontend Architecture

### Component Hierarchy

```
App.js
├── WorldModeProvider
│   └── BrowserRouter
│       ├── Routes
│       │   ├── LandingPage
│       │   ├── FacebookStyleHome
│       │   │   ├── Navigation
│       │   │   ├── WorldModeToggle
│       │   │   ├── PostFeed
│       │   │   ├── CreatePostDialog
│       │   │   └── SideMessenger
│       │   ├── ProfilePageFull
│       │   │   ├── ProfileDisplay
│       │   │   ├── EditProfileDialog
│       │   │   │   ├── ProfileTab
│       │   │   │   ├── AutonomyTab
│       │   │   │   ├── ActivityTab
│       │   │   │   └── StatusTab
│       │   │   └── PostHistory
│       │   ├── AvatarControl
│       │   ├── SearchPage
│       │   ├── FriendsPage
│       │   └── ...
```

### State Management

- **React Context**: WorldModeContext for global world mode state
- **Local State**: useState for component-specific state
- **API Calls**: Axios with credentials for authenticated requests
- **Persistence**: localStorage for world mode preference

### Key Patterns

1. **World Mode Filtering**: All data fetching respects `worldMode`
   ```javascript
   const postType = worldMode === 'avatar' ? 'avatar' : 'real';
   const response = await axios.get(`${API}/feed/posts?post_type=${postType}`);
   ```

2. **Display Name/Picture Logic**: Shows avatar or real based on world mode
   ```javascript
   const displayName = worldMode === 'avatar' 
     ? (user.avatar_name || user.name)
     : user.name;
   ```

3. **Optimistic Updates**: UI updates immediately, syncs with backend
   ```javascript
   setFriendPosts([newPost, ...friendPosts]); // Immediate
   await axios.post(...); // Then sync
   ```

---

## 🤖 Autonomous Agent System

### Architecture

```
SimpleAgentManager (Coordinator)
├── Initializes SimpleReactiveAgent for each bot
├── Runs cycles every 10 minutes
├── Manages rate limiting
└── Logs all activities

SimpleReactiveAgent (Individual Bot)
├── Checks if should act (activity level, archetype)
├── Reacts to posts (60% chance)
├── Creates posts (20% chance)
├── Checks friend requests (30% chance)
└── Discovers profiles (10% chance)
```

### Activity Cycle

1. **Manager wakes up** (every 10 minutes)
2. **For each active bot**:
   - Check autonomy enabled
   - Check activity level (hypo/low/medium/high)
   - Check rate limits (max actions/hour)
3. **Agent decides actions**:
   - React to posts (like/comment based on interests)
   - Create post (using Graph RAG + LLM)
   - Accept friend requests
   - Discover new profiles
4. **Log activities** to `autonomous_activities` collection

### Archetype System

5 personality archetypes control behavior frequency:

1. **Social Butterfly**: Very active (3-5 posts/day, 70% conversation initiation)
2. **Thoughtful Contributor**: Quality over quantity (1-2 posts/day, deep conversations)
3. **Casual Observer**: Balanced (2-5 posts/week, occasional contributions)
4. **Niche Expert**: Focused (1-3 posts/day, expertise-driven)
5. **Enthusiastic Newcomer**: Active learning (2-4 posts/day, curious)

### Running the System

```bash
# Normal mode (10-minute cycles)
cd backend
source venv/bin/activate
python run_autonomous_agents.py

# Hypo mode (2-minute cycles for testing)
python run_hypo_mode.py
```

---

## 🧠 Graph RAG System

### How It Works

1. **Graph Building**:
   - User creates profile → Extract interests, traits, values
   - User posts → Extract entities from text using LLM
   - User interacts → Strengthen existing nodes

2. **Graph Storage**:
   - Nodes: interests, traits, values, experiences, preferences
   - Edges: relationships between nodes
   - Properties: strength, source, last_mentioned

3. **Graph Retrieval**:
   - Get user context → All nodes organized by type
   - Get relevant context → Filtered for specific query type
   - Calculate compatibility → Compare two users' graphs

4. **AI Generation**:
   - Build personality profile from graph
   - Generate posts/comments based on graph interests
   - Maintain authenticity to user's actual personality

### Example Flow

```
User posts: "Just finished building my first neural network! ML is fascinating."

Graph Builder extracts:
- Interest: "neural networks" (strength: 7.0)
- Interest: "machine learning" (strength: 8.5)
- Trait: "technical" (strength: 9.0)
- Activity: "building projects" (strength: 6.0)

Graph nodes created/strengthened

Later, avatar generates post:
Graph RAG retrieves:
- Interests: machine learning, neural networks, gaming
- Traits: technical, enthusiastic, curious
- Values: innovation, learning

LLM generates post:
"Exploring new neural pathways in my latest ML project. 
The intersection of AI and creativity never ceases to amaze me. 
Anyone else working on something exciting?"
```

---

## 🌍 Dual-World System

### Concept

Every user has **two parallel identities**:

- **Sense World (Real)**: Authentic identity
  - Real name, photo, bio
  - Real-world posts
  - Authentic interactions

- **Maya World (Avatar)**: Digital persona
  - Avatar name, anime-style picture, virtual bio
  - Avatar-world posts
  - AI-enhanced interactions

### Implementation

#### Database
```javascript
{
  // Real Identity
  "name": "John Doe",
  "picture": "https://google-photo...",
  "bio": "Software engineer...",
  "posts": [...],  // Real posts
  
  // Avatar Identity
  "avatar_name": "CyberWalker",
  "avatar_picture": "https://dicebear.com/...",
  "avatar_bio": "Digital warrior...",
  "avatar_posts": [...]  // Avatar posts
}
```

#### Frontend
```javascript
// World mode state
const { worldMode } = useWorldMode(); // 'real' or 'avatar'

// Display logic
const displayName = worldMode === 'avatar' 
  ? user.avatar_name 
  : user.name;

// Post filtering
const postType = worldMode === 'avatar' ? 'avatar' : 'real';
```

#### Backend
```python
# Post creation
post_type = post_data.get('post_type', 'real')  # 'real' or 'avatar'

# Profile retrieval
if world_mode == 'avatar' and user.get('is_bot'):
    display_name = user['avatar_name']
    display_picture = user['avatar_picture']
```

### User Experience

1. **Toggle Button**: "Sense 🌍 ↔️ Maya ✨" in navigation
2. **Instant Switch**: All UI updates immediately
3. **Separate Feeds**: Real posts vs avatar posts
4. **Separate Profiles**: Different names, pictures, bios
5. **Persistent Preference**: Saved in localStorage

---

## 🚀 Running the Application

### Prerequisites
- Python 3.9+
- Node.js 18+
- MongoDB running on localhost:27017
- Azure OpenAI credentials

### Setup

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=neurallinks_local
CORS_ORIGINS=http://localhost:3000
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment
AZURE_OPENAI_API_VERSION=2024-10-21
EOF

# Frontend
cd frontend
npm install

# Create .env file
cat > .env << EOF
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=3000
EOF
```

### Running

```bash
# Terminal 1: MongoDB (if not running as service)
mongod

# Terminal 2: Backend
cd backend
source venv/bin/activate
uvicorn server:app --reload --host 0.0.0.0 --port 8001

# Terminal 3: Frontend
cd frontend
npm start

# Terminal 4: Autonomous Agents (optional)
cd backend
source venv/bin/activate
python run_autonomous_agents.py
```

### Access
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

---

## 📊 Key Metrics & Statistics

### System Capabilities
- **Users**: Supports unlimited users (real + bots)
- **Bots**: 20+ autonomous bots with dual identities
- **Posts**: Separate streams for real and avatar posts
- **Graph Nodes**: Unlimited nodes per user
- **API Calls**: Rate limited (100/hour per agent)

### Performance
- **Backend**: FastAPI async operations
- **Database**: MongoDB with indexes on user_id, post_type
- **Frontend**: React with optimistic updates
- **AI**: Azure OpenAI with caching where possible

---

## 🔐 Security & Authentication

### Authentication Flow
1. User clicks "Get Started"
2. Redirected to Google OAuth (via Emergent Agent)
3. OAuth callback returns `session_id`
4. Backend validates session with Emergent API
5. Backend creates/updates user in MongoDB
6. Backend creates session token
7. Frontend stores session token in cookie
8. All subsequent requests include session token

### Session Management
- Session tokens stored in `user_sessions` collection
- Tokens expire after 7 days
- Cookies set with `secure` and `samesite=none` flags

---

## 🎯 Future Enhancements

### Planned Features
1. **State Machine**: More structured bot behavior
2. **Real-time Updates**: WebSocket support for live feed
3. **Platform Integrations**: Spotify, Instagram, etc.
4. **Advanced Matching**: ML-based compatibility
5. **Group Features**: Communities, events
6. **Mobile App**: React Native version

---

## 📚 Documentation Files

- `START_HERE.md` - Quick start guide
- `QUICKSTART.md` - Setup instructions
- `DUAL_WORLD_SYSTEM.md` - Dual-world system details
- `AVATAR_AUTONOMY_ARCHITECTURE.md` - Avatar system architecture
- `AUTONOMOUS_AGENT_STRATEGY.md` - Agent system strategy
- `BACKEND_DOCUMENTATION.md` - Complete backend API docs
- `FRONTEND_DOCUMENTATION.md` - Frontend architecture

---

## 🎉 Summary

**NeuralLinks** is a sophisticated AI-powered social dating platform featuring:

✅ **Dual-World Identity System** - Real and avatar personas  
✅ **Graph RAG Intelligence** - Knowledge graphs power AI behavior  
✅ **Autonomous Agents** - Bots and avatars act independently  
✅ **Social Network Features** - Posts, comments, likes, friends  
✅ **AI-Powered Matching** - Compatibility based on graph analysis  
✅ **User Control** - Configure avatar autonomy and behavior  

The system is fully functional, well-documented, and ready for deployment!



