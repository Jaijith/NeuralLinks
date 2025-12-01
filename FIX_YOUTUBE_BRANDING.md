# Fix "YouTube Data Access" Branding Issue

## The Problem
The login client ID (`549441919787-rtfahh87v2uqsmm42b3v876lan3rf69k`) was originally created for YouTube integration, so Google's OAuth consent screen shows "YouTube Data Access" even when used for authentication.

## Solution: Update OAuth Consent Screen

The OAuth consent screen is **project-wide**, not per-client. You need to update it in Google Cloud Console:

### Step 1: Update OAuth Consent Screen

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to: **APIs & Services** → **OAuth consent screen**

### Step 2: Edit App Information

1. Click **EDIT APP**
2. **App name**: Change from "YouTube Data Access" to:
   - "Geneses" 
   - OR "NeuralLinks"
   - OR "Maya - The Realm of Avatars"
3. **User support email**: Your email
4. **App logo**: Upload your app logo (optional but recommended)
5. **App domain**: Leave blank for localhost, or add your domain for production
6. **Developer contact information**: Your email
7. Click **SAVE AND CONTINUE**

### Step 3: Update Scopes

1. In the **Scopes** section, you should see scopes for both:
   - Authentication (userinfo.email, userinfo.profile)
   - YouTube (if you have YouTube integration)
2. Make sure the scopes are correct
3. Click **SAVE AND CONTINUE**

### Step 4: Test Users (if app is in Testing mode)

1. Add your email addresses as test users
2. Click **SAVE AND CONTINUE**

### Step 5: Review and Submit

1. Review all settings
2. Click **BACK TO DASHBOARD**

## Important Notes

- The OAuth consent screen name is **shared across all OAuth clients** in the same project
- If you want completely separate branding, you'd need to create a **new Google Cloud Project** for authentication
- For most cases, just updating the app name in the consent screen is sufficient

## Alternative: Create New Project (If You Want Complete Separation)

If you want completely separate branding:

1. Create a new Google Cloud Project (e.g., "Geneses Authentication")
2. Create a new OAuth client ID in that project
3. Configure the consent screen with your app name
4. Use that client ID for authentication
5. Keep the YouTube client in the original project

## After Making Changes

1. **Wait 5-10 minutes** for Google to propagate the changes
2. Clear your browser cache/cookies
3. Try logging in again
4. You should now see your app name instead of "YouTube Data Access"

## Quick Test

After updating, the login flow should show:
- "to continue to **Geneses**" (or whatever you named it)
- Instead of "to continue to **YouTube Data Access**"

