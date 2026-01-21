# View Both Profiles - Post Sorting Fix

## 🐛 Bug Description

**Issue:** When clicking "View Both Profiles" in the profile page, old posts were being displayed instead of the latest posts under each profile section (Sense Posts and Maya Posts).

**Impact:** 
- ❌ Users saw outdated posts in the side-by-side view
- ✅ Home feed showed correct posts (sorted properly)
- ✅ Individual profile pages showed correct posts (sorted properly)
- ❌ Only "View Both Profiles" was affected

---

## 🔍 Root Cause

### The Problem:

In `frontend/src/pages/ProfilePageFull.jsx`, the "View Both Profiles" section was displaying posts without sorting:

**Before (Broken):**
```javascript
// Sense Posts
profileUser.posts.slice(0, 3).map((post) => ...)
// ↑ No sorting! Just takes first 3 items in array

// Maya Posts  
profileUser.avatar_posts.slice(0, 3).map((post) => ...)
// ↑ No sorting! Just takes first 3 items in array
```

The `profileUser.posts` and `profileUser.avatar_posts` arrays come from the backend without guaranteed sorting. They could be in any order, resulting in old posts being displayed first.

---

## ✅ The Fix

Added sorting by `created_at` in **descending order** (newest first) before slicing:

**After (Fixed):**
```javascript
// Sense Posts - NOW SORTED
profileUser.posts
  .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  .slice(0, 3)
  .map((post) => ...)
// ↑ Sorts newest to oldest, then takes top 3

// Maya Posts - NOW SORTED
profileUser.avatar_posts
  .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  .slice(0, 3)
  .map((post) => ...)
// ↑ Sorts newest to oldest, then takes top 3
```

---

## 📊 How Sorting Works

### Sort Logic:
```javascript
.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
```

**Explanation:**
- Compares post `b.created_at` with `a.created_at`
- If `b` is newer, returns positive (b comes first)
- Result: Newest posts at the beginning

**Example:**
```javascript
// Before sorting
posts = [
  { id: 1, created_at: "2025-01-15T10:00:00Z", text: "Old post" },
  { id: 2, created_at: "2025-01-20T15:00:00Z", text: "New post" },
  { id: 3, created_at: "2025-01-18T12:00:00Z", text: "Mid post" }
]

// After sorting
posts = [
  { id: 2, created_at: "2025-01-20T15:00:00Z", text: "New post" },    // ← Newest
  { id: 3, created_at: "2025-01-18T12:00:00Z", text: "Mid post" },
  { id: 1, created_at: "2025-01-15T10:00:00Z", text: "Old post" }
]

// After slice(0, 3)
// Shows: New post, Mid post, Old post (top 3 newest)
```

---

## 📁 Files Modified

### 1. `frontend/src/pages/ProfilePageFull.jsx`

**Lines 1487-1507** (Sense Posts):
```javascript
// Added .sort() before .slice()
profileUser.posts
  .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  .slice(0, 3)
```

**Lines 1707-1727** (Maya Posts):
```javascript
// Added .sort() before .slice()
profileUser.avatar_posts
  .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  .slice(0, 3)
```

---

## 🧪 Testing the Fix

### Before Fix:
```
View Both Profiles:
  Sense Posts:
    - "Post from 3 weeks ago"
    - "Post from 2 weeks ago"
    - "Post from 1 week ago"
  
  Maya Posts:
    - "Avatar post from 10 days ago"
    - "Avatar post from 5 days ago"
    - "Avatar post from yesterday"
```

### After Fix:
```
View Both Profiles:
  Sense Posts:
    - "Post from TODAY"        ← Latest
    - "Post from yesterday"
    - "Post from 2 days ago"
  
  Maya Posts:
    - "Avatar post from TODAY"  ← Latest
    - "Avatar post from yesterday"
    - "Avatar post from 2 days ago"
```

---

## ✅ Deployment Status

### Changes Deployed:
- ✅ Frontend code updated with sorting fix
- ✅ Built with correct API URL (`https://api.2ness.com`)
- ✅ Synced to S3 bucket
- ✅ CloudFront invalidation in progress
  - **Invalidation ID**: `IBG77Y71US3YE6YJ05DJEBQ6EW`
  - **ETA**: 2-5 minutes

---

## 🔍 Why Other Views Work Correctly

### Home Feed (`FacebookStyleHome.jsx`):
- Fetches posts via API endpoint: `/api/posts/feed`
- Backend already sorts by `created_at DESC`
- ✅ Always shows latest posts

### Individual Profile Page:
- Uses `fetchPosts()` function with pagination
- Backend API sorts by `created_at DESC`
- ✅ Always shows latest posts

### View Both Profiles:
- Uses embedded `profileUser.posts` array from user profile
- Backend doesn't guarantee sorting in user document
- ❌ Was showing unsorted posts → **NOW FIXED** ✅

---

## 📝 Summary

**Issue:** Old posts shown in "View Both Profiles"

**Cause:** No client-side sorting before displaying

**Fix:** Added `.sort()` before `.slice()` for both Sense and Maya posts

**Result:** Now shows the 3 most recent posts for each profile, sorted newest to oldest

**Deployment:** Live in ~2-5 minutes after CloudFront cache clears

---

## ✨ Additional Improvements Included

While fixing this, we also deployed:

1. ✅ **Profile Picture Preservation** - S3 uploads no longer overwritten by Gmail pic
2. ✅ **12 MCP Tool Toggles** - All tools now visible in Maya World UI
3. ✅ **Default Permissions** - All 11 tools enabled for new users (except share_posts)
4. ✅ **Correct API URL** - Frontend now points to `https://api.2ness.com`

---

**The fix is deployed and will be visible shortly!** 🎉
