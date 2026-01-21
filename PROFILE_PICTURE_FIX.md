# Profile Picture Preservation Fix

## 🐛 Bug Description

**Issue:** User profile pictures disappear after logout/login in Sense World, but avatar pictures remain intact.

**Root Cause:** The authentication code was only checking for `/uploads/` in the picture URL to determine if it's a custom uploaded picture. However, when using S3 storage, uploaded pictures have URLs like:
```
https://neurallinks-files.s3.us-west-1.amazonaws.com/profile_pictures/abc.jpg
```

These S3 URLs don't contain `/uploads/`, so the code incorrectly thought they were Google pictures and overwrote them on login.

---

## ✅ Solution

Updated the picture detection logic in `backend/api/auth_routes.py` to recognize multiple types of custom pictures:

### Old Logic (Broken):
```python
has_custom_picture = current_picture and '/uploads/' in current_picture
```
**Problem:** Only detects local storage uploads, misses S3 uploads!

### New Logic (Fixed):
```python
# Check if it's a custom uploaded picture by looking for:
# - /uploads/ (local storage)
# - .s3. (S3 storage)
# - profile_pictures/ (uploaded file path)
# - Any non-Google picture URL
is_google_picture = current_picture and 'googleusercontent.com' in current_picture
has_custom_picture = current_picture and (
    '/uploads/' in current_picture or
    '.s3.' in current_picture or
    'profile_pictures/' in current_picture or
    (not is_google_picture and 'http' in current_picture)
)
```

---

## 🧪 Test Results

### ✅ Preserved (Custom Pictures):
- `https://neurallinks-files.s3.us-west-1.amazonaws.com/profile_pictures/abc.jpg` - **S3 upload**
- `http://localhost:8001/uploads/profile_pictures/xyz.jpg` - **Local upload**
- `https://api.2ness.com/uploads/profile_pictures/test.png` - **Production upload**
- `https://some-cdn.com/profile_pictures/user123.jpg` - **CDN upload**
- `https://api.dicebear.com/7.x/adventurer/svg?seed=123` - **Avatar generator**

### ✅ Allow Overwrite (Google Pictures):
- `https://lh3.googleusercontent.com/a/xyz` - **Google profile picture**
- Empty or no picture - **Allow setting Google picture**

---

## 📋 Real-World Scenarios

### Scenario 1: User uploads custom picture then logs out/in
```
Current Picture: https://neurallinks-files.s3.us-west-1.amazonaws.com/profile_pictures/user_123.jpg
Google Picture:  https://lh3.googleusercontent.com/a/default123

✅ RESULT: Keeps custom picture (doesn't overwrite)
```

### Scenario 2: New user with Google picture
```
Current Picture: https://lh3.googleusercontent.com/a/default123
Google Picture:  https://lh3.googleusercontent.com/a/newpic456

✅ RESULT: Updates to new Google picture
```

### Scenario 3: User has no picture
```
Current Picture: (none)
Google Picture:  https://lh3.googleusercontent.com/a/pic789

✅ RESULT: Sets Google picture
```

### Scenario 4: User uploaded via local storage
```
Current Picture: https://api.2ness.com/uploads/profile_pictures/custom.png
Google Picture:  https://lh3.googleusercontent.com/a/xyz

✅ RESULT: Keeps custom picture (doesn't overwrite)
```

---

## 🔍 Why Avatar Pictures Weren't Affected

Avatar pictures use a **separate database field** (`avatar_picture`) that is never touched by the Google OAuth login flow. Only the `picture` field (Sense World real profile) is potentially updated during login.

### Database Fields:
- `picture` - Sense World (real) profile picture ← **Fixed here**
- `avatar_picture` - Maya World (avatar) profile picture ← **Always preserved**

---

## 📦 Files Modified

1. **`backend/api/auth_routes.py`** (lines 114-129)
   - Updated picture detection logic in `create_or_get_user()` function
   - Now correctly identifies S3-hosted custom pictures

2. **`backend/scripts/test_profile_picture_preservation.py`** (new file)
   - Test suite to verify the fix
   - Covers all picture URL formats

---

## 🚀 Deployment

The fix is ready to deploy. After deployment:

1. ✅ Users who upload custom pictures will keep them after logout/login
2. ✅ S3-hosted pictures are correctly identified as custom
3. ✅ Local storage pictures continue to work
4. ✅ Google pictures can still be updated when user doesn't have a custom picture
5. ✅ Avatar pictures remain unaffected (separate field)

---

## 🎯 Summary

**Before:** Custom S3 pictures → Lost on login ❌  
**After:** Custom S3 pictures → Preserved on login ✅

The fix ensures that ANY uploaded picture (S3, local, CDN) is preserved during login, not just local storage uploads!
