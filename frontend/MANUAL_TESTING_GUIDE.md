# Manual End-to-End Testing Guide

## Prerequisites

1. **Backend must be running** on `http://localhost:8001`
2. **Frontend must be running** on `http://localhost:3000`
3. **Browser DevTools open** (F12) - Check Console and Network tabs

## Quick Start

```bash
# Terminal 1: Start backend
cd backend
python -m uvicorn app.main:app --reload --port 8001

# Terminal 2: Start frontend
cd frontend
npm start

# Terminal 3: Run automated tests
cd frontend
npm run test:all
```

## Testing Checklist

### ✅ Phase 1: Infrastructure Tests

#### Backend Health
- [ ] Open `http://localhost:8001/api/auth/me` in browser
- [ ] Should return JSON (may be 401 if not logged in, that's OK)
- [ ] Check Network tab - no CORS errors

#### Frontend Build
- [ ] Run `npm run build` - should complete without errors
- [ ] Check bundle size in output (should be ~113KB gzipped)
- [ ] Verify chunks are created (multiple .chunk.js files)

### ✅ Phase 2: Authentication Flow

#### Login
1. [ ] Navigate to `http://localhost:3000`
2. [ ] Click "Login with Google"
3. [ ] Complete Google OAuth flow
4. [ ] Should redirect to `/home`
5. [ ] Check console - no errors
6. [ ] Check Network tab - should see chunk files loading

#### Session Persistence
1. [ ] Refresh the page (F5)
2. [ ] Should stay logged in
3. [ ] Should not redirect to landing page
4. [ ] Check console - no auth errors

#### Logout
1. [ ] Click Sign Out button (top right)
2. [ ] Should redirect to landing page
3. [ ] Check console - no errors
4. [ ] Try navigating to `/home` - should redirect to `/`

### ✅ Phase 3: Home Page (`/home`)

#### Page Load
- [ ] Navigate to `/home`
- [ ] Check Network tab - should see lazy-loaded chunks
- [ ] Page should load within 3 seconds
- [ ] Check console - no errors
- [ ] Loading spinner should appear briefly

#### Posts Display
- [ ] Posts should display in feed
- [ ] Each post should show:
  - User avatar and name
  - Post text/content
  - Timestamp
  - Like count
  - Comment count
- [ ] Posts should be sorted by newest first

#### Create Post (Text)
1. [ ] Type text in "What's on your mind?" box
2. [ ] Click "Post"
3. [ ] Post should appear at top of feed
4. [ ] Check console - no errors

#### Create Post (Image)
1. [ ] Click "Photo" button in create post card
2. [ ] Select an image file
3. [ ] Image preview should appear
4. [ ] Type optional text
5. [ ] Click "Post"
6. [ ] Post with image should appear
7. [ ] Image should load with placeholder first
8. [ ] Click image - should open in new tab

#### Like Post
1. [ ] Click "Like" button on a post
2. [ ] Button should turn blue
3. [ ] Like count should increment
4. [ ] Click again - should unlike
5. [ ] Check console - no errors

#### View Likes
1. [ ] Click on the likes count/icon
2. [ ] Dialog should show list of users who liked
3. [ ] Should display user names and avatars
4. [ ] Check console - no errors

#### Comment on Post
1. [ ] Click "Comment" button
2. [ ] Comment section should expand
3. [ ] Type a comment
4. [ ] Press Enter or click Send
5. [ ] Comment should appear
6. [ ] Comment count should increment
7. [ ] Check console - no errors

#### Load More Posts
1. [ ] Scroll to bottom of feed
2. [ ] Click "Load More Posts" button
3. [ ] More posts should load
4. [ ] Button should show loading state
5. [ ] Check Network tab - should see API call
6. [ ] Check console - no errors

#### Suggested Users
- [ ] "Suggested for you" section should appear in sidebar
- [ ] Should show user avatars and names
- [ ] Should show mutual connections count
- [ ] Click "Add" button
- [ ] Friend request should be sent
- [ ] User should disappear from suggestions
- [ ] Toast notification should appear
- [ ] Check console - no errors

#### Navigation
- [ ] Click on a user's name/avatar
- [ ] Should navigate to their profile
- [ ] Check Network tab - profile page chunk should load
- [ ] Check console - no errors

### ✅ Phase 4: Profile Page (`/profile/:userId`)

#### Page Load
- [ ] Navigate to a profile (click user from home page)
- [ ] Profile should load
- [ ] Check Network tab - chunk should load
- [ ] Check console - no errors

#### Profile Display
- [ ] Cover photo should display
- [ ] Profile picture should display
- [ ] User name should display
- [ ] Bio/description should display (if available)
- [ ] Posts should display below

#### Upload Profile Picture
1. [ ] Click "Edit Profile Picture" button
2. [ ] Select an image file
3. [ ] Image should upload
4. [ ] Profile picture should update
5. [ ] Check console - no errors
6. [ ] Test in both Sense and Maya worlds

#### Upload Cover Photo
1. [ ] Click "Edit Cover Photo" button
2. [ ] Select an image file
3. [ ] Image should upload
4. [ ] Cover photo should update
5. [ ] Check console - no errors
6. [ ] Test in both Sense and Maya worlds

#### Friend Request
- [ ] If not a friend, "Add Friend" button should appear
- [ ] Click "Add Friend"
- [ ] Friend request should be sent
- [ ] Button should change to "Request Sent"
- [ ] Check console - no errors

#### Posts on Profile
- [ ] Posts should display
- [ ] Should show user's posts only
- [ ] Click "Load More Posts" if available
- [ ] Posts should load correctly

### ✅ Phase 5: Navigation & Routes

Test each route:
- [ ] `/` - Landing page
- [ ] `/home` - Home feed
- [ ] `/profile/:userId` - User profile
- [ ] `/settings` - Settings page
- [ ] `/gallery` - Gallery page
- [ ] `/friends` - Friends page
- [ ] `/matches` - Matches page
- [ ] `/search` - Search page
- [ ] `/integrations` - Integrations page
- [ ] `/avatar-visualization` - Avatar visualization
- [ ] `/avatar-control` - Avatar control

For each route:
- [ ] Page should load
- [ ] No white screen
- [ ] No console errors
- [ ] Check Network tab - chunks should load
- [ ] Navigation should be smooth

### ✅ Phase 6: Components

#### PostCard Component
- [ ] Posts use PostCard structure
- [ ] All sections render correctly:
  - Header (user info, timestamp)
  - Content (text, image)
  - Engagement (likes, comments)
  - Actions (Like, Comment, Share)
  - Comments section (when expanded)

#### UserAvatar Component
- [ ] Avatars display correctly
- [ ] Fallback shows initials when no image
- [ ] Clicking avatar navigates to profile
- [ ] Works in both Sense and Maya worlds

#### LoadingSpinner Component
- [ ] Shows during page loads
- [ ] Shows during lazy loading
- [ ] Shows during API calls (if implemented)

#### OptimizedImage Component
- [ ] Images load with placeholder
- [ ] Smooth fade-in transition
- [ ] Error handling works (test with broken image URL)
- [ ] Click to open in new tab works

#### ErrorBoundary
- [ ] Wraps all routes
- [ ] Should catch React errors gracefully
- [ ] Should show error UI instead of white screen

### ✅ Phase 7: Performance

#### Initial Load
- [ ] Open DevTools Performance tab
- [ ] Record page load
- [ ] Initial load should be < 3s
- [ ] Time to Interactive should be < 5s

#### Lazy Loading
- [ ] Open DevTools Network tab
- [ ] Navigate to different routes
- [ ] Should see chunk files loading on-demand
- [ ] Each route should load its own chunk

#### Image Loading
- [ ] Images should lazy load
- [ ] Placeholders should show first
- [ ] Images should fade in smoothly
- [ ] No layout shift

#### Bundle Size
- [ ] Run `npm run build`
- [ ] Check main bundle size
- [ ] Should be ~113KB gzipped
- [ ] Chunks should be 3-6KB each

### ✅ Phase 8: Error Handling

#### Network Errors
- [ ] Stop backend server
- [ ] Try to create a post
- [ ] Should show error message
- [ ] Should not crash the app

#### Invalid Routes
- [ ] Navigate to `/invalid-route`
- [ ] Should show 404 or redirect
- [ ] Should not crash

#### Invalid Data
- [ ] Try to upload invalid file type
- [ ] Should show error message
- [ ] Should not crash

## Common Issues to Watch For

1. **CORS Errors**: Check Network tab for CORS issues
2. **404 Errors**: Check if chunks are loading correctly
3. **White Screens**: Check console for React errors
4. **Slow Loading**: Check Network tab for slow API calls
5. **Memory Leaks**: Check DevTools Memory tab during navigation

## Reporting Issues

If you find issues:

1. **Note the page/route** where it occurred
2. **Check console** for errors
3. **Check Network tab** for failed requests
4. **Take screenshot** if visual issue
5. **Note steps to reproduce**

## Success Criteria

✅ All automated tests pass (`npm run test:all`)  
✅ All manual tests pass (checklist above)  
✅ No console errors  
✅ No white screens  
✅ All routes load correctly  
✅ All features work as expected  
✅ Performance is acceptable (< 3s initial load)

## Next Steps After Testing

1. ✅ Fix any critical issues found
2. ✅ Document any known issues
3. ✅ Proceed with Phase 3: Full migration to new services/components
4. ✅ Continue with remaining optimizations

