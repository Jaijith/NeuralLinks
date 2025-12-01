# Google OAuth Setup Guide

## Overview
This application now uses Google OAuth directly instead of Emergent services for authentication.

## Setup Steps

### 1. Install Dependencies
```bash
cd backend
source venv/bin/activate
pip install google-auth-oauthlib==1.2.1
```

### 2. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API (or Google Identity API)
4. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
5. Choose "Web application"
6. Add authorized redirect URIs:
   - For development: `http://localhost:8001/api/auth/google/callback`
   - For production: `https://yourdomain.com/api/auth/google/callback`
7. Copy the Client ID and Client Secret

### 3. Configure Environment Variables

Add these to your `backend/.env` file:

```env
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8001/api/auth/google/callback
```

For production, update `GOOGLE_REDIRECT_URI` to your production URL.

### 4. Update Frontend Environment

Make sure your frontend `.env` has the correct backend URL:

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

For production, update this to your production backend URL.

## How It Works

1. **User clicks "Log In"** → Redirects to `/api/auth/google/login`
2. **Backend redirects to Google** → User authenticates with Google
3. **Google redirects back** → `/api/auth/google/callback` with authorization code
4. **Backend exchanges code** → Gets user info from Google
5. **Backend creates/updates user** → Creates session and sets cookie
6. **User redirected to app** → Already authenticated with session cookie

## Testing

1. Start the backend: `cd backend && uvicorn app.main:app --reload --port 8001`
2. Start the frontend: `cd frontend && npm start`
3. Click "Log In" on the landing page
4. Complete Google OAuth flow
5. You should be redirected back and logged in

## Troubleshooting

### "Google OAuth not configured" error
- Make sure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`
- Restart the backend after adding environment variables

### Redirect URI mismatch
- Make sure the redirect URI in Google Cloud Console matches `GOOGLE_REDIRECT_URI` in your `.env`
- The URI must match exactly (including http/https and port)

### Cookie not being set
- Check browser console for errors
- Make sure cookies are enabled
- For production, ensure HTTPS is used (cookies require secure flag)

## Migration Notes

- Old Emergent authentication endpoints have been removed
- The `/api/auth/session-data` endpoint is no longer used
- All authentication now goes through Google OAuth directly
- Session management remains the same (using `user_sessions` collection)

