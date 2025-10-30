# Frontend Documentation - Sense-Maya Dating App

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Installation & Setup](#installation--setup)
5. [Project Structure](#project-structure)
6. [Core Concepts](#core-concepts)
7. [Pages & Components](#pages--components)
8. [State Management](#state-management)
9. [Routing](#routing)
10. [API Integration](#api-integration)
11. [Styling & UI](#styling--ui)
12. [Testing](#testing)
13. [Deployment](#deployment)

---

## Overview

The Sense-Maya frontend is a React-based single-page application (SPA) that provides an immersive dual-world dating experience. Users seamlessly switch between:

- **Sense (Real World)**: Traditional dating profiles with authentic information
- **Maya (Avatar World)**: AI-powered digital personas with stylized aesthetics

The app features social media-style interactions, real-time messaging with AI avatars, and a sophisticated Graph RAG-powered matching system.

---

## Architecture

### High-Level Architecture

```
┌────────────────────────────────────────────────────────┐
│                    React Application                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Pages      │  │  Components  │  │   Contexts   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────────────────────────────────────────┐  │
│  │            API Layer (axios)                     │  │
│  └──────────────────────────────────────────────────┘  │
└───────────────────────┬────────────────────────────────┘
                        │ REST API
                        ▼
            ┌───────────────────────┐
            │   Backend API         │
            │  (FastAPI/MongoDB)    │
            └───────────────────────┘
```

### Component Hierarchy

```
App.js (Root)
├── WorldModeProvider (Context)
├── BrowserRouter
│   └── Routes
│       ├── LandingPage
│       ├── FacebookStyleHome
│       │   ├── AppHeader
│       │   ├── WorldModeToggle
│       │   └── SideMessenger
│       ├── ProfilePageFull
│       │   ├── AppHeader
│       │   ├── WorldModeToggle
│       │   └── SideMessenger
│       ├── FriendsPage
│       ├── SearchPage
│       ├── IntegrationsPage
│       ├── Matches
│       ├── Chat
│       └── Dashboard
└── Toaster (Notifications)
```

---

## Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| Framework | React | 18.x | UI framework |
| Build Tool | Craco | 7.x | Create React App configuration |
| Routing | React Router | 6.x | Client-side routing |
| HTTP Client | Axios | Latest | API requests |
| State Management | React Context | Built-in | Global state |
| UI Components | Shadcn UI | Latest | Component library |
| Styling | Tailwind CSS | 3.x | Utility-first CSS |
| Notifications | Sonner | Latest | Toast notifications |
| Icons | Lucide React | Latest | Icon library |

---

## Installation & Setup

### Prerequisites
- Node.js 18+
- Yarn package manager
- Backend API running

### Installation Steps

```bash
# Navigate to frontend directory
cd /app/frontend

# Install dependencies
yarn install

# Configure environment variables
# Edit .env file

# Start development server (via supervisor)
sudo supervisorctl restart frontend

# Or start manually
yarn start
```

### Dependencies

**package.json key dependencies:**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.x",
    "axios": "^1.x",
    "@radix-ui/react-*": "Latest",
    "tailwindcss": "^3.x",
    "lucide-react": "Latest",
    "sonner": "Latest"
  }
}
```

---

## Project Structure

```
/app/frontend/
├── public/                          # Static assets
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── App.js                       # Root component & routing
│   ├── App.css                      # Global styles
│   ├── index.js                     # Entry point
│   ├── index.css                    # Tailwind imports & global CSS
│   ├── components/                  # Reusable components
│   │   ├── ui/                      # Shadcn UI components
│   │   │   ├── button.jsx
│   │   │   ├── card.jsx
│   │   │   ├── dialog.jsx
│   │   │   ├── input.jsx
│   │   │   ├── avatar.jsx
│   │   │   ├── badge.jsx
│   │   │   └── tabs.jsx
│   │   ├── AppHeader.jsx            # Shared header with navigation
│   │   ├── WorldModeToggle.jsx      # World mode switcher
│   │   └── SideMessenger.jsx        # Floating chat widget
│   ├── contexts/                    # React contexts
│   │   └── WorldModeContext.jsx     # World mode state management
│   ├── hooks/                       # Custom hooks
│   │   └── use-toast.js             # Toast notification hook
│   └── pages/                       # Page components
│       ├── LandingPage.jsx          # Landing/login page
│       ├── FacebookStyleHome.jsx    # Main social feed
│       ├── ProfilePageFull.jsx      # User profile page
│       ├── FriendsPage.jsx          # Friends list
│       ├── SearchPage.jsx           # User search
│       ├── IntegrationsPage.jsx     # Platform integrations
│       ├── Matches.jsx              # Matches page
│       ├── Chat.jsx                 # Full-page chat (legacy)
│       ├── AvatarChat.jsx           # Avatar chat page
│       ├── Dashboard.jsx            # User dashboard
│       ├── OnboardingChat.jsx       # Onboarding flow
│       └── Profile.jsx              # Profile settings
├── .env                             # Environment variables
├── package.json                     # Dependencies
├── tailwind.config.js               # Tailwind configuration
├── postcss.config.js                # PostCSS configuration
└── craco.config.js                  # Craco configuration
```

---

## Core Concepts

### 1. Dual World System

The app operates in two parallel modes that users can toggle between:

#### Sense (Real World)
- **Purpose:** Traditional dating with authentic profiles
- **Visual:** Clean, bright design with standard UI
- **Data:** Real names, photos, bios, interests
- **Chat:** Person-to-person messaging (future feature)

#### Maya (Avatar World)
- **Purpose:** AI-powered avatars with distinct personas
- **Visual:** Stylized, Avatar-movie inspired aesthetics
- **Data:** Avatar names, generated photos, AI-crafted bios
- **Chat:** AI-powered responses using Graph RAG

### 2. World Mode Context

Global state management for world mode switching.

**Location:** `/src/contexts/WorldModeContext.jsx`

```javascript
const { worldMode, setWorldMode, toggleWorldMode } = useWorldMode();

// worldMode values: 'real' | 'avatar'
```

**Usage:**
```javascript
import { useWorldMode } from '@/contexts/WorldModeContext';

function MyComponent() {
  const { worldMode, toggleWorldMode } = useWorldMode();
  
  const displayName = worldMode === 'avatar' 
    ? user.avatar_name 
    : user.name;
    
  return (
    <div>
      <h1>{displayName}</h1>
      <button onClick={toggleWorldMode}>Switch World</button>
    </div>
  );
}
```

### 3. Authentication Flow

```
1. User lands on LandingPage
   ↓
2. Clicks "Sign In" → Redirects to Emergent OAuth
   ↓
3. OAuth returns with session_id in URL hash
   ↓
4. App.js extracts session_id and calls backend
   ↓
5. Backend validates and returns session_token
   ↓
6. Token stored in cookie automatically
   ↓
7. User redirected to /home (FacebookStyleHome)
```

**Implementation in App.js:**
```javascript
const handleAuthCallback = async () => {
  const hash = window.location.hash;
  if (hash && hash.includes("session_id=")) {
    const sessionId = hash.split("session_id=")[1].split("&")[0];
    
    const response = await axios.get(`${API}/auth/session-data`, {
      headers: { "X-Session-ID": sessionId },
      withCredentials: true,
    });

    document.cookie = `session_token=${response.data.session_token}; path=/; secure; samesite=none; max-age=604800`;
    
    await checkAuth();
  }
};
```

---

## Pages & Components

### Landing Page

**File:** `/src/pages/LandingPage.jsx`

**Purpose:** Marketing page with sign-in

**Key Features:**
- Hero section with value proposition
- Feature highlights
- Sign-in button redirects to Emergent OAuth

**Code Example:**
```javascript
const handleSignIn = () => {
  window.location.href = "https://demobackend.emergentagent.com/auth/v1/env/oauth/google";
};
```

---

### Facebook Style Home

**File:** `/src/pages/FacebookStyleHome.jsx`

**Purpose:** Main social feed with posts, friends, and navigation

**Key Features:**
- Post creation and viewing
- Friends sidebar with quick message
- World mode toggle
- Navigation header
- Feed of friend posts
- Avatar conversation stats (in Maya mode)

**World Mode Behavior:**
```javascript
// Display avatar or real identity based on worldMode
const displayName = worldMode === 'avatar' 
  ? (friend.avatar_name || friend.name)
  : friend.name;

const displayPicture = worldMode === 'avatar' 
  ? (friend.avatar_picture || friend.picture)
  : friend.picture;
```

**Friends Sidebar with Messenger:**
```javascript
<div 
  className="flex items-center justify-between"
  onMouseEnter={() => setHoveredFriend(friend.id)}
>
  <div onClick={() => navigate(`/profile/${friend.id}`)}>
    <Avatar>
      <AvatarImage src={displayPicture} />
    </Avatar>
    <span>{displayName}</span>
  </div>
  
  {hoveredFriend === friend.id && (
    <Button
      onClick={() => {
        setSelectedFriend(friend);
        setShowMessenger(true);
      }}
    >
      <MessageCircle />
    </Button>
  )}
</div>
```

---

### Profile Page Full

**File:** `/src/pages/ProfilePageFull.jsx`

**Purpose:** Comprehensive user profile with posts, friends, and editing

**Key Features:**
- View own or other user's profile
- Separate tabs for Sense and Maya profiles
- Post creation and management
- Friend list display
- Profile editing
- Message button integration
- Side-by-side view for own profile

**Profile Display Logic:**
```javascript
const viewUserId = userId || currentUser?.id;
const isOwnProfile = !userId || userId === currentUser?.id;

// Fetch profile based on world mode
const response = await axios.get(
  `${API}/users/${viewUserId}?world_mode=${worldMode}`,
  { withCredentials: true }
);
```

**World-Specific Content:**
```javascript
// In Sense mode
<div>
  <h1>{profileUser.name}</h1>
  <p>{profileUser.bio}</p>
  <div>Interests: {profileUser.interests.join(', ')}</div>
  <PostsList posts={profileUser.posts} />
</div>

// In Maya mode
<div>
  <h1>{profileUser.avatar_name}</h1>
  <p>{profileUser.avatar_bio}</p>
  <div>Interests: {profileUser.avatar_interests.join(', ')}</div>
  <PostsList posts={profileUser.avatar_posts} />
</div>
```

**Message Button:**
```javascript
<Button 
  onClick={() => setShowMessenger(true)}
  className="bg-blue-500"
>
  <MessageCircle className="w-4 h-4 mr-2" />
  Message
</Button>

{showMessenger && (
  <SideMessenger
    user={currentUser}
    otherUserId={profileUser.id}
    otherUserData={profileUser}
    onClose={() => setShowMessenger(false)}
  />
)}
```

---

### Side Messenger

**File:** `/src/components/SideMessenger.jsx`

**Purpose:** Floating chat widget for AI avatar conversations

**Key Features:**
- Bottom-right floating position
- Minimizable/maximizable
- AI-powered responses in Maya mode
- Person-to-person chat in Sense mode
- Message history
- Typing indicators
- Conversation starters

**Component Structure:**
```javascript
const SideMessenger = ({ user, otherUserId, otherUserData, onClose }) => {
  const { worldMode } = useWorldMode();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const sendMessage = async () => {
    // Add user message
    setMessages(prev => [...prev, userMessage]);
    
    if (worldMode === 'avatar') {
      // Get AI response
      const response = await axios.post(`${API}/avatar/chat-response`, {
        other_user_id: otherUserId,
        conversation_history: messages,
        last_message: input
      });
      
      setMessages(prev => [...prev, aiMessage]);
    } else {
      // Real mode: person-to-person (placeholder)
      setMessages(prev => [...prev, autoReply]);
    }
  };

  return (
    <Card className="fixed bottom-4 right-4 w-80 h-[500px]">
      {/* Header with minimize/close */}
      {/* Messages area */}
      {/* Input area */}
    </Card>
  );
};
```

**World Mode Display:**
```javascript
const displayName = worldMode === 'avatar' 
  ? (otherUser.avatar_name || otherUser.name) 
  : otherUser.name;

const displayPicture = worldMode === 'avatar' 
  ? (otherUser.avatar_picture || otherUser.picture) 
  : otherUser.picture;
```

**Message Display:**
```javascript
{messages.map((msg, idx) => (
  <div className={msg.sender_id === user.id ? "justify-end" : "justify-start"}>
    <Avatar src={
      msg.sender_id === user.id 
        ? (worldMode === 'avatar' ? user.avatar_picture : user.picture)
        : displayPicture
    } />
    <div className="message-bubble">
      {msg.is_ai && <Badge>AI Response</Badge>}
      <p>{msg.content}</p>
      <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
    </div>
  </div>
))}
```

---

### Friends Page

**File:** `/src/pages/FriendsPage.jsx`

**Purpose:** Display and manage friend connections

**Key Features:**
- Grid layout of friends
- World mode-aware display
- Quick actions (message, view profile)
- Friend request management

---

### Search Page

**File:** `/src/pages/SearchPage.jsx`

**Purpose:** Search and discover new users

**Key Features:**
- Search by name or interests
- Filter options
- World mode-aware results
- Quick connect actions

---

### Integrations Page

**File:** `/src/pages/IntegrationsPage.jsx`

**Purpose:** Connect external platforms to enrich avatar intelligence

**Supported Platforms:**
- Spotify (music preferences)
- YouTube (video interests)
- Instagram (photos & interests)
- Facebook (social connections)
- Amazon (shopping preferences)
- Netflix (entertainment)
- Goodreads (reading)
- Strava (fitness)

**Features:**
- Platform cards with connection status
- Connect/disconnect functionality
- Data sync capabilities
- Graph RAG enrichment explanation

**Code Example:**
```javascript
const connectPlatform = async (platformName) => {
  await axios.post(`${API}/integrations/connect`, 
    { platform_name: platformName },
    { withCredentials: true }
  );
  toast.success(`${platformName} connected!`);
};

const syncPlatform = async (platformName) => {
  const response = await axios.post(`${API}/integrations/sync`, 
    { platform_name: platformName },
    { withCredentials: true }
  );
  toast.success(response.data.message);
};
```

---

### Matches Page

**File:** `/src/pages/Matches.jsx`

**Purpose:** View and interact with matches

**Key Features:**
- Match cards with compatibility scores
- AI-generated match explanations
- Quick chat access
- Accept/decline actions

---

### Dashboard

**File:** `/src/pages/Dashboard.jsx`

**Purpose:** User overview and quick actions

**Key Features:**
- Activity summary
- Recent matches
- Profile completion status
- Quick navigation

---

## State Management

### World Mode Context

**File:** `/src/contexts/WorldModeContext.jsx`

**Purpose:** Global state for Sense/Maya world mode

```javascript
// Context Provider
export const WorldModeProvider = ({ children }) => {
  const [worldMode, setWorldMode] = useState(() => {
    return localStorage.getItem('worldMode') || 'real';
  });

  const toggleWorldMode = () => {
    const newMode = worldMode === 'real' ? 'avatar' : 'real';
    setWorldMode(newMode);
    localStorage.setItem('worldMode', newMode);
  };

  return (
    <WorldModeContext.Provider value={{ worldMode, setWorldMode, toggleWorldMode }}>
      {children}
    </WorldModeContext.Provider>
  );
};

// Hook Usage
const { worldMode, toggleWorldMode } = useWorldMode();
```

**Persistence:**
- Stored in localStorage
- Persists across page reloads
- Syncs with CSS class on body

**CSS Integration:**
```javascript
useEffect(() => {
  if (worldMode === 'avatar') {
    document.body.classList.add('avatar-world');
  } else {
    document.body.classList.remove('avatar-world');
  }
}, [worldMode]);
```

---

### Local Component State

**Common Patterns:**

```javascript
// User authentication
const [user, setUser] = useState(null);
const [loading, setLoading] = useState(true);

// Form inputs
const [input, setInput] = useState('');
const [postText, setPostText] = useState('');

// UI state
const [showMessenger, setShowMessenger] = useState(false);
const [isMinimized, setIsMinimized] = useState(false);
const [selectedFriend, setSelectedFriend] = useState(null);

// Data fetching
const [friends, setFriends] = useState([]);
const [posts, setPosts] = useState([]);
const [matches, setMatches] = useState([]);
```

---

## Routing

### Route Configuration

**File:** `/src/App.js`

```javascript
<Routes>
  {/* Public Routes */}
  <Route path="/" element={
    user ? <Navigate to="/home" /> : <LandingPage setUser={setUser} />
  } />

  {/* Protected Routes */}
  <Route path="/home" element={
    user ? <FacebookStyleHome user={user} setUser={setUser} /> : <Navigate to="/" />
  } />
  
  <Route path="/profile/:userId" element={
    user ? <ProfilePageFull user={user} /> : <Navigate to="/" />
  } />
  
  <Route path="/myprofile" element={
    user ? <ProfilePageFull user={user} /> : <Navigate to="/" />
  } />
  
  <Route path="/friends" element={
    user ? <FriendsPage user={user} /> : <Navigate to="/" />
  } />
  
  <Route path="/search" element={
    user ? <SearchPage user={user} /> : <Navigate to="/" />
  } />
  
  <Route path="/integrations" element={
    user ? <IntegrationsPage user={user} /> : <Navigate to="/" />
  } />
  
  <Route path="/matches" element={
    user ? <Matches user={user} /> : <Navigate to="/" />
  } />
  
  <Route path="/chat/:matchId" element={
    user ? <Chat user={user} /> : <Navigate to="/" />
  } />
  
  <Route path="/avatar-chat/:userId" element={
    user ? <AvatarChat user={user} /> : <Navigate to="/" />
  } />
  
  <Route path="/dashboard" element={
    user ? <Dashboard user={user} setUser={setUser} /> : <Navigate to="/" />
  } />
  
  <Route path="/onboarding" element={
    user ? <OnboardingChat user={user} /> : <Navigate to="/" />
  } />
</Routes>
```

### Navigation Patterns

```javascript
// Programmatic navigation
const navigate = useNavigate();

// Navigate to profile
navigate(`/profile/${userId}`);

// Navigate to home
navigate('/home');

// Navigate back
navigate(-1);

// Navigate with state
navigate('/profile', { state: { from: '/search' } });
```

---

## API Integration

### Base Configuration

**Environment Variable:** `.env`
```
REACT_APP_BACKEND_URL=https://sense-maya.preview.emergentagent.com
```

**API Setup:**
```javascript
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
```

### Common API Patterns

#### 1. Authenticated GET Request

```javascript
const fetchUserProfile = async (userId) => {
  try {
    const response = await axios.get(
      `${API}/users/${userId}?world_mode=${worldMode}`,
      { withCredentials: true }
    );
    setProfileUser(response.data);
  } catch (error) {
    console.error("Error fetching profile:", error);
    toast.error("Failed to load profile");
  }
};
```

#### 2. POST Request with Body

```javascript
const createPost = async (postData) => {
  try {
    const response = await axios.post(
      `${API}/profile/posts`,
      {
        text: postData.text,
        post_type: worldMode === 'avatar' ? 'avatar' : 'real'
      },
      { withCredentials: true }
    );
    setPosts(prev => [response.data, ...prev]);
    toast.success("Post created!");
  } catch (error) {
    console.error("Error creating post:", error);
    toast.error("Failed to create post");
  }
};
```

#### 3. Avatar AI Requests

```javascript
// Generate avatar chat response
const getAvatarResponse = async (message) => {
  try {
    const response = await axios.post(
      `${API}/avatar/chat-response`,
      {
        other_user_id: otherUserId,
        conversation_history: messages,
        last_message: message
      },
      { withCredentials: true }
    );
    return response.data.content;
  } catch (error) {
    console.error("Avatar response error:", error);
    throw error;
  }
};

// Generate avatar post
const generateAvatarPost = async (type = "general") => {
  try {
    const response = await axios.post(
      `${API}/avatar/generate-post?post_type=${type}`,
      {},
      { withCredentials: true }
    );
    return response.data.content;
  } catch (error) {
    console.error("Post generation error:", error);
    throw error;
  }
};
```

#### 4. Graph RAG Requests

```javascript
// Build graph from profile
const buildGraph = async () => {
  try {
    const response = await axios.post(
      `${API}/graph/build-from-profile`,
      {},
      { withCredentials: true }
    );
    toast.success(`Graph built: ${response.data.nodes_created} nodes`);
  } catch (error) {
    console.error("Graph build error:", error);
  }
};

// Get compatibility
const getCompatibility = async (otherUserId) => {
  try {
    const response = await axios.get(
      `${API}/graph/compatibility/${otherUserId}`,
      { withCredentials: true }
    );
    return response.data;
  } catch (error) {
    console.error("Compatibility error:", error);
    return null;
  }
};
```

### Error Handling

**Standard Pattern:**
```javascript
try {
  const response = await axios.get(`${API}/endpoint`, { withCredentials: true });
  // Success handling
} catch (error) {
  console.error("Error:", error);
  
  if (error.response?.status === 401) {
    toast.error("Please log in");
    navigate('/');
  } else if (error.response?.status === 404) {
    toast.error("Not found");
  } else {
    toast.error(error.response?.data?.detail || "Something went wrong");
  }
}
```

---

## Styling & UI

### Tailwind CSS

**Configuration:** `tailwind.config.js`

```javascript
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Custom color palette
      },
      animation: {
        // Custom animations
      }
    }
  },
  plugins: []
}
```

**Global Styles:** `src/index.css`

```css
/* Tailwind imports */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Global styles */
@layer base {
  body {
    @apply bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50;
  }
}

/* Avatar World styles */
body.avatar-world {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
}

body.avatar-world * {
  color: #e0e7ff;
}

/* Animations */
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-in {
  animation: fade-in 0.3s ease-out;
}
```

### Common Class Patterns

```javascript
// Card styling
className="glass-morphism p-6 rounded-2xl shadow-lg"

// Button styling
className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-3 rounded-full hover:shadow-lg transition-all"

// Avatar World card
className={worldMode === 'avatar' ? 'card-avatar bg-slate-900 border-blue-500' : 'bg-white'}

// Hover effects
className="hover:bg-purple-50 transition-colors cursor-pointer"

// Flex layouts
className="flex items-center justify-between space-x-4"

// Grid layouts
className="grid md:grid-cols-2 lg:grid-cols-3 gap-6"
```

### Shadcn UI Components

**Usage Example:**
```javascript
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog";

<Card className="p-6">
  <Avatar>
    <AvatarImage src={user.picture} />
    <AvatarFallback>{user.name[0]}</AvatarFallback>
  </Avatar>
  
  <Button variant="outline">Click Me</Button>
  
  <Dialog>
    <DialogContent>
      <DialogHeader>Title</DialogHeader>
      <p>Content</p>
    </DialogContent>
  </Dialog>
</Card>
```

### World Mode Styling

**Conditional Classes:**
```javascript
// Background
className={worldMode === 'avatar' ? 'bg-slate-900' : 'bg-white'}

// Text
className={worldMode === 'avatar' ? 'text-blue-100' : 'text-gray-800'}

// Border
className={worldMode === 'avatar' ? 'border-blue-500' : 'border-purple-300'}

// Hover
className={worldMode === 'avatar' ? 'hover:bg-slate-800/50' : 'hover:bg-gray-50'}
```

### Responsive Design

```javascript
// Mobile-first approach
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"

// Hide on mobile
className="hidden md:block"

// Show only on mobile
className="block md:hidden"

// Responsive padding
className="p-4 md:p-6 lg:p-8"

// Responsive text
className="text-sm md:text-base lg:text-lg"
```

---

## Testing

### Manual Testing Checklist

#### Authentication
- [ ] Sign in redirects to OAuth
- [ ] OAuth callback creates session
- [ ] Session persists on reload
- [ ] Logout clears session

#### World Mode
- [ ] Toggle switches between Sense/Maya
- [ ] Correct data displays in each mode
- [ ] Avatar pictures show in Maya mode
- [ ] Real pictures show in Sense mode
- [ ] Mode persists on reload

#### Side Messenger
- [ ] Opens from Message button
- [ ] Displays correct avatar/real picture
- [ ] AI responds in Maya mode
- [ ] Messages display correctly
- [ ] Minimize/maximize works
- [ ] Close button works

#### Profile Page
- [ ] Own profile shows edit options
- [ ] Other profiles show message button
- [ ] Posts display correctly by world mode
- [ ] Friends show correct pictures
- [ ] Profile updates save

#### Navigation
- [ ] All routes work
- [ ] Protected routes redirect if not logged in
- [ ] Back button works
- [ ] Direct URL access works

### Browser Console Testing

```javascript
// Check authentication
localStorage.getItem('session_token')

// Check world mode
localStorage.getItem('worldMode')

// Test API directly
fetch('https://sense-maya.preview.emergentagent.com/api/auth/me', {
  credentials: 'include'
}).then(r => r.json()).then(console.log)
```

### Performance Testing

```javascript
// Measure component render time
console.time('ProfilePage');
// ... component renders
console.timeEnd('ProfilePage');

// Check bundle size
yarn build
// Check build/static/js/*.js file sizes

// Lighthouse audit
// Run in Chrome DevTools
```

---

## Deployment

### Production Build

```bash
# Build for production
yarn build

# Output: /build directory
# Contains optimized static files
```

### Environment Configuration

**Production .env:**
```bash
REACT_APP_BACKEND_URL=https://your-production-api.com
WDS_SOCKET_PORT=443
REACT_APP_ENABLE_VISUAL_EDITS=false
ENABLE_HEALTH_CHECK=false
```

### Deployment Checklist

- [ ] Update REACT_APP_BACKEND_URL to production API
- [ ] Build production bundle: `yarn build`
- [ ] Test build locally: `serve -s build`
- [ ] Configure CORS on backend for production domain
- [ ] Set up HTTPS
- [ ] Configure CDN (optional)
- [ ] Enable gzip compression
- [ ] Set up error tracking (Sentry, etc.)
- [ ] Configure analytics
- [ ] Test all features in production

### Service Management

```bash
# Restart frontend
sudo supervisorctl restart frontend

# Check status
sudo supervisorctl status frontend

# View logs
tail -f /var/log/supervisor/frontend.out.log
```

---

## Troubleshooting

### Common Issues

#### Issue: "Failed to send message"
**Cause:** Authentication or API connectivity
**Solution:**
1. Check browser console for errors
2. Verify you're logged in
3. Check network tab for failed requests
4. Ensure worldMode is correct ('avatar' not 'Maya')

#### Issue: World mode not switching
**Cause:** State not updating
**Solution:**
1. Check WorldModeContext is properly wrapped
2. Verify localStorage is accessible
3. Clear browser cache

#### Issue: Images not loading
**Cause:** CORS or URL issues
**Solution:**
1. Check image URLs in network tab
2. Verify CORS headers from backend
3. Use valid dicebear URLs for avatars

#### Issue: White screen on load
**Cause:** JavaScript error
**Solution:**
1. Check browser console
2. Look for missing imports
3. Verify all environment variables

#### Issue: Routes not working
**Cause:** Router configuration
**Solution:**
1. Verify BrowserRouter wrapper
2. Check route paths
3. Ensure authentication checks

---

## Best Practices

### Component Design

```javascript
// Good: Small, focused components
const UserCard = ({ user, worldMode, onClick }) => {
  const displayName = worldMode === 'avatar' ? user.avatar_name : user.name;
  return <Card onClick={onClick}>{displayName}</Card>;
};

// Bad: Large, multi-purpose components
const MegaComponent = () => {
  // 500 lines of code...
};
```

### State Management

```javascript
// Good: Specific state variables
const [isLoading, setIsLoading] = useState(false);
const [error, setError] = useState(null);
const [data, setData] = useState([]);

// Bad: Generic state
const [state, setState] = useState({ loading: false, error: null, data: [] });
```

### API Calls

```javascript
// Good: Separate API functions
const fetchUserProfile = async (userId) => {
  const response = await axios.get(`${API}/users/${userId}`);
  return response.data;
};

useEffect(() => {
  fetchUserProfile(userId).then(setProfile);
}, [userId]);

// Bad: Inline API calls
useEffect(() => {
  axios.get(`${API}/users/${userId}`).then(r => setProfile(r.data));
}, [userId]);
```

### Error Handling

```javascript
// Good: Specific error handling
try {
  await createPost(data);
  toast.success("Post created!");
} catch (error) {
  if (error.response?.status === 401) {
    navigate('/login');
  } else {
    toast.error(error.response?.data?.detail || "Failed to create post");
  }
}

// Bad: Generic error handling
try {
  await createPost(data);
} catch (error) {
  console.log(error);
}
```

---

## Performance Optimization

### Code Splitting

```javascript
// Lazy load pages
const ProfilePage = lazy(() => import('./pages/ProfilePageFull'));

<Suspense fallback={<LoadingSpinner />}>
  <ProfilePage />
</Suspense>
```

### Memoization

```javascript
// Memoize expensive computations
const compatibilityScore = useMemo(() => {
  return calculateCompatibility(user1, user2);
}, [user1, user2]);

// Memoize callbacks
const handleClick = useCallback(() => {
  navigate(`/profile/${userId}`);
}, [userId, navigate]);
```

### Image Optimization

```javascript
// Use appropriate image sizes
<Avatar className="w-8 h-8">  // Small thumbnails
<Avatar className="w-20 h-20"> // Profile pictures
<Avatar className="w-32 h-32"> // Large displays
```

---

## Security Considerations

### Authentication
- Session tokens stored in HTTP-only cookies
- No sensitive data in localStorage
- Protected routes require authentication
- Auto-redirect to login when unauthorized

### XSS Protection
- React escapes content by default
- Use `dangerouslySetInnerHTML` sparingly
- Validate user input before display

### HTTPS
- Always use HTTPS in production
- Secure cookies with `secure` flag
- Use `samesite` cookie attribute

---

## Appendix

### Keyboard Shortcuts

- `Enter` - Send message in chat
- `Esc` - Close modals/dialogs
- `/` - Focus search (when implemented)

### Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Accessibility

- Semantic HTML elements
- ARIA labels where needed
- Keyboard navigation support
- Color contrast compliance

---

**Version:** 1.0  
**Last Updated:** January 30, 2025  
**Maintained by:** Sense-Maya Development Team
