# OAuth Client Setup - Separate Authentication Client

## Problem
The current OAuth client ID is configured for YouTube Data API access, which causes Google to show "to continue to YouTube Data Access" when users try to log in.

## Solution
Create a **separate OAuth 2.0 Client ID** specifically for user authentication, separate from the YouTube integration client.

## Steps to Create New Authentication Client

### 1. Go to Google Cloud Console
- Visit: https://console.cloud.google.com/
- Select your project (or create a new one)

### 2. Create New OAuth 2.0 Client ID
1. Navigate to: **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. If prompted, configure the OAuth consent screen first:
   - User Type: **External** (for testing) or **Internal** (for Google Workspace)
   - App name: **Geneses** or **NeuralLinks**
   - User support email: Your email
   - Developer contact: Your email
   - Click **Save and Continue**
   - Scopes: Add `.../auth/userinfo.email` and `.../auth/userinfo.profile`
   - Click **Save and Continue**
   - Test users: Add your email (for external apps in testing)
   - Click **Save and Continue**

### 3. Configure OAuth Client
1. Application type: **Web application**
2. Name: **Geneses Authentication** (or similar)
3. **Authorized redirect URIs**:
   - Development: `http://localhost:8001/api/auth/google/callback`
   - Production: `https://yourdomain.com/api/auth/google/callback`
4. Click **CREATE**

### 4. Copy Credentials
- Copy the **Client ID** and **Client Secret**
- These are different from your YouTube integration credentials

### 5. Update .env File
Replace the current credentials in `backend/.env`:

```env
# Google OAuth Configuration (for authentication only)
GOOGLE_CLIENT_ID=your_new_authentication_client_id
GOOGLE_CLIENT_SECRET=your_new_authentication_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8001/api/auth/google/callback

# YouTube OAuth Configuration (for YouTube integration - keep separate)
YOUTUBE_CLIENT_ID=549441919787-rtfahh87v2uqsmm42b3v876lan3rf69k.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=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
YOUTUBE_REDIRECT_URI=http://localhost:8001/api/integrations/oauth/callback/youtube
```

## Why Separate Clients?

1. **Different Purposes**: 
   - Authentication client: Only for user login (email, profile)
   - YouTube client: For YouTube Data API access (videos, subscriptions, etc.)

2. **Different Scopes**:
   - Authentication: `openid`, `userinfo.email`, `userinfo.profile`
   - YouTube: `youtube.readonly`, `youtube.force-ssl`

3. **Better Security**: Separate credentials limit access if one is compromised

4. **Better UX**: Authentication won't show "YouTube Data Access" branding

## Alternative: Use Existing Client (Quick Fix)

If you want to use the existing client temporarily, you can:
1. Keep the current credentials
2. The login will work but will show YouTube branding
3. Users can still authenticate successfully

However, **creating a separate client is recommended** for production.

