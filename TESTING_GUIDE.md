# AI Dating Match App - Testing Guide

## 🚀 Quick Start

**Live App URL:** https://avatar-dating-1.preview.emergentagent.com/

---

## 📋 Testing Steps

### 1. **Sign Up / Sign In**
- Go to https://avatar-dating-1.preview.emergentagent.com/
- Click "Get Started Free" or "Sign In" button
- You'll be redirected to Google OAuth
- Sign in with your Google account
- After authentication, you'll be redirected back to the app

### 2. **Complete Your Profile (Two Options)**

**Option A: AI-Powered Onboarding (Recommended)**
- You'll be taken to the onboarding chat page
- Chat with your AI assistant to build your profile
- Share information about yourself naturally in conversation
- The AI will extract details like age, location, interests, bio
- Click "Complete Profile" when done

**Option B: Skip and Add Manually**
- Click "Skip for now" on the onboarding page
- Go to Dashboard
- Click "Profile" in the navigation
- Click "Edit Profile"
- Fill in:
  - Age
  - Gender
  - Location
  - Bio
  - Interests (comma-separated)
- Click "Save"

### 3. **Discover Matches**
- From the Dashboard, click "Start Discovery" button
- The system will find other users with completed profiles
- AI agents will evaluate compatibility based on:
  - Shared interests
  - Personality traits
  - Conversation potential
- Matches will appear on your dashboard with compatibility scores

### 4. **View Match Details**
- Click "View All Matches" or go to "Matches" page
- Click on any match to see detailed compatibility breakdown:
  - Overall compatibility score
  - Personality match score
  - Conversation quality score
  - Shared interests
  - AI conversation summary

### 5. **Start Chatting**
- Click "Start Chatting" on a match
- Send messages to your match
- Real-time chat interface with message history

---

## 🧪 Testing with Pre-Created Users

I've created two test users for you to test the matching system:

### Test User 1: Alex
- **Email:** alex.techie@example.com
- **Age:** 28, Male
- **Location:** San Francisco, CA
- **Interests:** hiking, coffee, technology, startups, photography, travel
- **Bio:** Software engineer who loves hiking, coffee, and building cool tech projects

### Test User 2: Sarah
- **Email:** sarah.creative@example.com
- **Age:** 26, Female
- **Location:** San Francisco, CA
- **Interests:** photography, art, design, hiking, yoga, travel
- **Bio:** Creative designer passionate about art, photography, and outdoor adventures

**To test matching with these users:**
1. Sign in with your own Google account
2. Complete your profile with some shared interests (e.g., hiking, photography, travel)
3. Click "Start Discovery" - you should see Alex and Sarah as potential matches

---

## 🔍 Testing AI Agent Conversations

### Method 1: Via API (Advanced)

You can manually trigger AI agent conversations using the API:

```bash
# 1. Create a session for a test user
SESSION_TOKEN="your_session_token_here"
TARGET_USER_ID="test-sarah-1761802435434"  # Sarah's ID

# 2. Start AI agent conversation
curl -X POST "https://avatar-dating-1.preview.emergentagent.com/api/agent/start-conversation/$TARGET_USER_ID" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json"
```

### Method 2: Via UI (Recommended)

1. Sign in and complete your profile
2. Click "Start Discovery" on dashboard
3. The system automatically creates matches
4. Go to "Matches" page
5. Click on a match to see the AI conversation summary
6. The AI agents have already chatted and evaluated compatibility

---

## 🧪 Advanced Testing Scenarios

### Test AI Onboarding Chat
1. Create a new Google account (or use incognito mode)
2. Sign in to the app
3. On the onboarding page, chat naturally with the AI:
   - "I'm 25 years old and I live in New York"
   - "I love hiking, photography, and reading books"
   - "I'm looking for someone who shares my passion for outdoor adventures"
4. The AI should respond naturally and guide you through profile creation

### Test Match Discovery Algorithm
1. Create a profile with specific interests
2. Click "Start Discovery"
3. Check that matches have:
   - Compatibility scores calculated correctly
   - Shared interests highlighted
   - Different scores for personality, conversation quality, etc.

### Test Real-Time Chat
1. You'll need two accounts to test this properly
2. Create two browser sessions (one normal, one incognito)
3. Sign in with different Google accounts in each
4. Complete profiles for both
5. Discover matches and start chatting
6. Messages should appear in real-time

---

## 📊 What to Look For

### ✅ Success Indicators:
- Landing page loads with beautiful gradient design
- Google OAuth login works smoothly
- Dashboard shows your stats (matches, compatibility, chats)
- AI onboarding chat responds naturally
- Match discovery finds compatible users
- Compatibility scores are displayed (0-100%)
- Shared interests are highlighted
- Chat interface works smoothly
- Profile editing saves correctly

### 🐛 Potential Issues:
- If Azure OpenAI features don't work, check backend logs:
  ```bash
  tail -f /var/log/supervisor/backend.err.log
  ```
- If authentication fails, clear cookies and try again
- If matches don't appear, ensure both users have `profile_completed: true`

---

## 🔧 Quick Debugging Commands

### Check Backend Status
```bash
sudo supervisorctl status backend
```

### View Backend Logs
```bash
tail -n 100 /var/log/supervisor/backend.err.log
```

### Check Database
```bash
mongosh test_database --eval "db.users.find().pretty()"
mongosh test_database --eval "db.matches.find().pretty()"
```

### Test API Endpoint
```bash
curl https://avatar-dating-1.preview.emergentagent.com/api/auth/me
```

---

## 💡 Pro Tips

1. **Use Real Interests:** When creating your profile, use real interests to see how well the matching algorithm works
2. **Try Different Personalities:** Create profiles with very different interests to see low compatibility scores
3. **Create Similar Profiles:** Create profiles with many shared interests to see high compatibility scores
4. **Test Social Media Integration:** The infrastructure is ready for social media connections (future feature)
5. **Explore Graph RAG:** The system builds knowledge graphs from your interactions over time

---

## 📞 Need Help?

If you encounter any issues:
1. Check the browser console for errors (F12)
2. Check backend logs (commands above)
3. Verify Azure OpenAI credentials are set correctly in `/app/backend/.env`
4. Make sure MongoDB is running: `sudo supervisorctl status`

---

## 🎯 Test Checklist

- [ ] Landing page loads correctly
- [ ] Google OAuth sign-in works
- [ ] Onboarding AI chat responds
- [ ] Profile can be edited manually
- [ ] Match discovery finds users
- [ ] Compatibility scores display
- [ ] Match details page shows breakdown
- [ ] AI conversation summaries appear
- [ ] Real-time chat works
- [ ] Profile picture displays
- [ ] Logout works correctly

---

**Happy Testing! 🎉**
