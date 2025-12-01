# Verify OAuth Setup - Fix "YouTube Data Access" Issue

## Current Status
✅ Credentials are now properly separated in `.env`:
- Login: `549441919787-rtfahh87v2uqsmm42b3v876lan3rf69k`
- YouTube: `549441919787-a6j1rapbh01ngaedl1k7ciii3goa1p4j`

## If You Still See "YouTube Data Access" During Login

This happens because the OAuth consent screen is configured incorrectly. Here's how to fix it:

### Step 1: Check OAuth Consent Screen

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to: **APIs & Services** → **OAuth consent screen**

### Step 2: Update App Information

1. **App name**: Change to "Geneses" or "NeuralLinks" (not YouTube-related)
2. **User support email**: Your email
3. **App logo**: Upload your app logo (optional)
4. **App domain**: Your domain (or leave blank for localhost)
5. Click **Save and Continue**

### Step 3: Check Scopes for Login Client

1. In **Scopes** section, make sure you only have:
   - `openid`
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`

2. **Remove any YouTube-related scopes** from the consent screen if they appear

3. Click **Save and Continue**

### Step 4: Verify Redirect URIs

For the **Login Client ID** (`549441919787-rtfahh87v2uqsmm42b3v876lan3rf69k`):

1. Go to: **APIs & Services** → **Credentials**
2. Click on the client ID: `549441919787-rtfahh87v2uqsmm42b3v876lan3rf69k`
3. Under **Authorized redirect URIs**, make sure you have:
   - `http://localhost:8001/api/auth/google/callback`
   - (For production: `https://yourdomain.com/api/auth/google/callback`)
4. Click **Save**

For the **YouTube Client ID** (`549441919787-a6j1rapbh01ngaedl1k7ciii3goa1p4j`):

1. Click on the client ID: `549441919787-a6j1rapbh01ngaedl1k7ciii3goa1p4j`
2. Under **Authorized redirect URIs**, make sure you have:
   - `http://localhost:8001/api/integrations/oauth/callback/youtube`
   - (For production: `https://yourdomain.com/api/integrations/oauth/callback/youtube`)
3. Click **Save**

### Step 5: Test Again

1. Restart your backend server
2. Clear browser cookies/cache
3. Try logging in again
4. You should see "Geneses" or your app name instead of "YouTube Data Access"

## Alternative: Create Brand New Login Client

If the issue persists, create a completely new OAuth client:

1. **APIs & Services** → **Credentials** → **+ CREATE CREDENTIALS** → **OAuth client ID**
2. Name: "Geneses Login" (make it clear it's for login only)
3. Application type: **Web application**
4. Redirect URI: `http://localhost:8001/api/auth/google/callback`
5. **Do NOT** enable any YouTube APIs for this client
6. Copy the new Client ID and Secret
7. Update `.env` with the new credentials

## Current Configuration Summary

```env
# Login/Authentication (should show your app name)
GOOGLE_CLIENT_ID=549441919787-rtfahh87v2uqsmm42b3v876lan3rf69k.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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

# YouTube Integration (separate, for YouTube features)
YOUTUBE_CLIENT_ID=549441919787-a6j1rapbh01ngaedl1k7ciii3goa1p4j.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=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
```

