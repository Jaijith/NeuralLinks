# ProfilePageFull Refactoring Plan

## Current Status

**File**: `ProfilePageFull.jsx`
- **Current Size**: 1,932 lines
- **Target Size**: ~600-800 lines (estimated 60-70% reduction)
- **Status**: 🚧 Hooks and components created, main file refactoring pending

## ✅ Completed Infrastructure

### Hooks Created
1. **`useProfile.js`** - Profile data management
   - Fetches profile data
   - Manages friendship status
   - Handles loading/error states
   - **Note**: Needs update to handle current user case (when `userId === currentUser.id`)

2. **`useProfilePosts.js`** - Profile posts management
   - Fetches posts with pagination
   - Manages liked posts state
   - Handles load more functionality
   - **Status**: ✅ Ready to use

### Components Created
1. **`ProfileHeader.jsx`** - Cover photo, profile picture, basic info
   - Handles profile/cover photo uploads
   - Displays user info based on world mode
   - Friend request button
   - **Status**: ✅ Ready to use

2. **`ProfilePostsTab.jsx`** - Posts tab content
   - Uses `usePostInteractions` and `useCreatePost` hooks
   - Displays posts using `PostCard`
   - **Status**: ✅ Ready to use

3. **`AvatarActivityLog.jsx`** - Avatar activity display
   - **Status**: ✅ Ready to use

### Existing Components to Use
- `PostCard` from `@/features/posts/components`
- `CreatePostCard` from `@/features/posts/components`
- `CreatePostDialog` from `@/features/posts/components`
- `LikesDialog` from `@/features/posts/components`
- `PostsFeed` from `@/features/home/components`

## 🔧 Refactoring Steps

### Step 1: Update `useProfile` Hook
**File**: `src/features/profile/hooks/useProfile.js`

**Changes Needed**:
- Handle case where `userId === currentUser.id` (use currentUser data directly)
- Initialize edit profile data when loading own profile
- Return friends list for sidebar

### Step 2: Create Profile Upload Handlers Hook
**New File**: `src/features/profile/hooks/useProfileUploads.js`

**Purpose**: Centralize profile picture and cover photo upload logic

```javascript
const useProfileUploads = (worldMode, onUploadSuccess) => {
  const [uploadingProfilePicture, setUploadingProfilePicture] = useState(false);
  const [uploadingCoverPhoto, setUploadingCoverPhoto] = useState(false);
  
  const handleProfilePictureUpload = async (file) => {
    // Use userService.uploadProfilePicture
  };
  
  const handleCoverPhotoUpload = async (file) => {
    // Use userService.uploadCoverPhoto
  };
  
  return {
    uploadingProfilePicture,
    uploadingCoverPhoto,
    handleProfilePictureUpload,
    handleCoverPhotoUpload
  };
};
```

### Step 3: Refactor Main Component Structure

**Replace**:
- `fetchProfile` → `useProfile` hook
- `fetchPosts` → `useProfilePosts` hook
- `handleLikePost`, `showLikes`, `showComments`, `handleAddComment` → `usePostInteractions` hook
- `createPost`, `handleImageSelect` → `useCreatePost` hook
- Profile header JSX → `ProfileHeader` component
- Posts rendering → `PostCard` components
- Create post UI → `CreatePostCard` + `CreatePostDialog`

**Keep Inline** (too complex/specific):
- Profile editing dialogs (real + avatar)
- Dual profile view mode logic
- Avatar status component
- Complex tab navigation

### Step 4: Simplify State Management

**Remove**:
- `profileUser` state (use hook)
- `posts` state (use hook)
- `likedPosts` state (use hook)
- `loading` state (use hook)
- `friendshipStatus` state (use hook)

**Keep**:
- `viewMode` state (dual profile view)
- `showEditRealProfile`, `editRealProfileData` (editing dialogs)
- `showEditAvatarProfile`, `editAvatarProfileData` (editing dialogs)
- `showMessenger` state
- `friends` state (for sidebar)

### Step 5: Extract Friends Sidebar Component
**New File**: `src/features/profile/components/ProfileFriendsSidebar.jsx`

**Purpose**: Display friends list in profile sidebar

### Step 6: Extract About Section Component
**New File**: `src/features/profile/components/ProfileAboutSection.jsx`

**Purpose**: Display about information (job, location, interests)

## 📋 Implementation Checklist

- [ ] Update `useProfile` hook to handle current user case
- [ ] Create `useProfileUploads` hook
- [ ] Create `ProfileFriendsSidebar` component
- [ ] Create `ProfileAboutSection` component
- [ ] Refactor main component to use hooks
- [ ] Replace profile header with `ProfileHeader` component
- [ ] Replace posts rendering with `PostCard` components
- [ ] Replace create post UI with `CreatePostCard` + `CreatePostDialog`
- [ ] Test all functionality
- [ ] Verify world mode switching works
- [ ] Verify profile editing works
- [ ] Verify post creation/editing/deletion works
- [ ] Verify likes and comments work

## 🎯 Expected Outcome

**Before**: 1,932 lines
**After**: ~600-800 lines
**Reduction**: ~60-70%

**Benefits**:
- Much cleaner and more maintainable
- Reusable hooks and components
- Consistent with other refactored pages
- Easier to test and debug

## ⚠️ Notes

- Keep complex editing dialogs inline (they're very specific to this page)
- Dual profile view mode is unique to this page, keep it
- Avatar activity log and status are specific, can keep inline or extract later
- Profile editing is complex with many fields, keep dialogs inline for now

