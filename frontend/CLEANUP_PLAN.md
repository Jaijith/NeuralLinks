# Frontend Cleanup Plan

## ✅ Already Completed
- [x] Removed all .md documentation files (17 files)
- [x] Removed test scripts (e2e-test.js, test-build.js)
- [x] Removed test files (services.test.js, test-services.js)
- [x] Removed ServiceTest component
- [x] Removed frontend.log file
- [x] **Phase 1 Complete**: Removed 17 empty directories
- [x] **Phase 1 Complete**: Removed unused logo.mov asset
- [x] **Phase 1 Complete**: Updated package.json to remove test scripts

## 🔍 Remaining Cleanup Tasks

### 1. **Empty Directories** (15 directories)
Remove all empty directories that serve no purpose:
- `frontend/scripts/` (empty, scripts already deleted)
- `frontend/src/components/feed/` (empty)
- `frontend/src/components/widgets/` (empty)
- `frontend/src/features/auth/components/` (empty)
- `frontend/src/features/auth/hooks/` (empty)
- `frontend/src/features/auth/services/` (empty)
- `frontend/src/features/matches/components/` (empty)
- `frontend/src/features/matches/hooks/` (empty)
- `frontend/src/features/matches/services/` (empty)
- `frontend/src/features/messages/components/` (empty)
- `frontend/src/features/messages/hooks/` (empty)
- `frontend/src/features/messages/services/` (empty)
- `frontend/src/features/posts/hooks/` (empty)
- `frontend/src/features/posts/services/` (empty)
- `frontend/src/features/profile/services/` (empty)
- `frontend/src/features/friends/services/` (empty)
- `frontend/src/services/api/__tests__/` (empty)

### 2. **Console.log Statements** (41 files with console statements)
**Action**: Review and clean up console.log/debug statements. Keep console.error for legitimate error logging.

**Files to review**:
- `src/pages/LandingPage.jsx` - Remove debug logs (lines 19-20)
- `src/pages/AvatarVisualization.jsx` - Remove debug logs (lines 54, 81)
- `src/components/SignupForm.jsx` - Keep console.error (legitimate)
- `src/components/AppHeader.jsx` - Keep console.error (legitimate)
- `src/features/home/components/HomeRightSidebar.jsx` - Keep console.error (legitimate)
- `src/features/profile/components/*` - Keep console.error (legitimate)
- `src/features/home/hooks/*` - Review and remove debug logs
- `src/pages/ProfilePageFull.jsx` - Review console.error usage
- `src/pages/GalleryPage.jsx` - Review console usage
- `src/pages/Matches.jsx` - Review console usage
- And 30+ more files...

**Strategy**: 
- Remove all `console.log()` and `console.debug()` statements
- Keep `console.error()` for error handling (but consider using logger utility)
- Replace with proper error logging using `logger.js` utility where appropriate

### 3. **TODO Comments** (4 instances)
Review and either implement or remove:
- `src/components/common/ErrorBoundary.jsx:31` - TODO: Send to error tracking service
- `src/utils/errorHandler.js:58` - TODO: Integrate with error tracking service
- `src/pages/OnboardingChat.jsx:51` - TODO: Extract profile data from AI response
- `src/features/profile/components/AvatarActivityLog.jsx:17` - Note about endpoint

**Action**: Either implement these or remove the TODOs if not needed.

### 4. **Redundant Profile.jsx**
**Status**: `Profile.jsx` exists but `ProfilePageFull.jsx` is the main profile page used in routes.

**Check**: 
- Verify if `Profile.jsx` is still used anywhere
- If not used, remove it and update `App.js` to remove the import/route
- If used, document why both exist

**Current usage**: 
- `App.js` imports both Profile and ProfilePageFull
- Route `/profile` uses `Profile` component
- Routes `/profile/:userId` and `/myprofile` use `ProfilePageFull`

**Decision needed**: Should `/profile` route use `ProfilePageFull` instead?

### 5. **package.json Scripts**
**Issue**: Test scripts reference deleted files:
```json
"test:e2e": "node scripts/e2e-test.js",
"test:build": "node scripts/test-build.js",
"test:all": "npm run test:build && npm run test:e2e"
```

**Action**: Remove these scripts since the test files are deleted.

### 6. **Unused Assets**
- `public/logo.mov` - Check if this video file is used anywhere. If not, remove it.

### 7. **Unused Feature Directories**
**Decision needed**: These feature directories are empty:
- `features/auth/` - Is authentication handled elsewhere?
- `features/matches/` - Is matching handled in pages?
- `features/messages/` - Is messaging handled in pages?

**Action**: Either remove these empty directories or document why they exist for future use.

### 8. **Code Quality**
- Review unused imports (if any)
- Ensure all error handling uses the centralized error handler
- Ensure all logging uses the centralized logger utility

## 📋 Recommended Cleanup Order

1. **Phase 1: Safe Removals** (No code changes)
   - Remove empty directories
   - Remove unused assets (logo.mov if not used)
   - Update package.json scripts

2. **Phase 2: Code Cleanup** (Low risk)
   - Remove console.log/debug statements
   - Clean up TODO comments
   - Review Profile.jsx usage

3. **Phase 3: Architecture Review** (Requires decision)
   - Decide on Profile.jsx vs ProfilePageFull.jsx
   - Decide on empty feature directories (keep for future or remove)

## ⚠️ Notes
- Keep `console.error()` statements for now as they're used for error handling
- Consider migrating to the logger utility in the future
- Empty feature directories might be placeholders for future features - confirm before removing
- Profile.jsx might be a simpler profile editor - verify if it's still needed

