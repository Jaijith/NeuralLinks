# 2ness Progressive Web App (PWA)

This document describes the PWA implementation for 2ness.com.

## Overview

2ness is a Progressive Web App that can be installed on mobile devices (iOS/Android) and desktops, providing an app-like experience with offline support.

## Features

- **Installable**: Users can "Add to Home Screen" on any device
- **Offline-friendly**: App shell and static assets are cached for offline access
- **Auto-updates**: New versions are detected and users can update with one click
- **Responsive**: Works on all screen sizes and orientations

## Files

| File | Location | Purpose |
|------|----------|---------|
| `manifest.webmanifest` | `/public/manifest.webmanifest` | PWA manifest with app metadata |
| `sw.js` | `/public/sw.js` | Service worker with caching strategies |
| `offline.html` | `/public/offline.html` | Offline fallback page |
| `serviceWorkerRegistration.js` | `/src/serviceWorkerRegistration.js` | SW registration logic |
| `PWAUpdateNotification.jsx` | `/src/components/common/PWAUpdateNotification.jsx` | Update notification UI |
| `icons/` | `/public/icons/` | PWA icons (192x192, 512x512, maskable) |

## Testing

### 1. Test Installability (Chrome DevTools)

1. Open Chrome DevTools (F12)
2. Go to **Application** tab
3. Click **Manifest** in sidebar
4. Verify manifest loads correctly with no errors
5. Check "Installability" section - should show "✓ Page meets installability requirements"

### 2. Test Service Worker

1. Go to **Application** → **Service Workers**
2. Verify service worker is registered and activated
3. Check "Offline" checkbox to simulate offline mode
4. Reload the page - should show cached content or offline page

### 3. Test Offline Mode

1. Load the app with network enabled
2. Navigate to a few pages (caches them)
3. Turn off network (DevTools → Network → Offline, or airplane mode on mobile)
4. Refresh - app should work with cached content
5. Navigate to uncached page - should show offline.html

### 4. Test Update Flow

1. Deploy a new version (bump `CACHE_VERSION` in sw.js)
2. With app open, wait up to 60 seconds (or hard refresh)
3. Update notification banner should appear at bottom
4. Click "Update" to reload with new version

### 5. Lighthouse PWA Audit

1. Open Chrome DevTools
2. Go to **Lighthouse** tab
3. Select "Progressive Web App" category
4. Click "Analyze page load"
5. Should pass all PWA criteria

## Caching Strategy

### Network-First (HTML/Navigation)
- Tries network first for freshest content
- Falls back to cache if offline
- Falls back to `/offline.html` as last resort

### Cache-First (Static Assets)
- JS, CSS, images, fonts cached on first load
- Served from cache immediately
- Updated in background when online

### Never Cached
- API responses (`/api/*`, `api.2ness.com`)
- Authentication endpoints
- Analytics (PostHog, etc.)
- Third-party scripts

## Updating the App

### Bumping Cache Version

When releasing a new version:

1. Update `CACHE_VERSION` in `/public/sw.js`:
   ```javascript
   const CACHE_VERSION = 'v1.1.0'; // Increment this
   ```

2. Build and deploy:
   ```bash
   REACT_APP_BACKEND_URL=https://api.2ness.com npm run build
   aws s3 sync build/ s3://2n1-frontend-019396192218 --delete
   aws cloudfront create-invalidation --distribution-id E2RQY6UYI2IHAE --paths "/*"
   ```

3. Users will see update notification within 60 seconds

### Force Update (Cache Busting)

To force all users to update immediately:

1. Invalidate CloudFront cache for `/sw.js`:
   ```bash
   aws cloudfront create-invalidation --distribution-id E2RQY6UYI2IHAE --paths "/sw.js"
   ```

## Hosting Configuration

### AWS CloudFront (Current)

SPA routing is already configured via CloudFront error responses:
- 404 → `/index.html` (200)
- 403 → `/index.html` (200)

This allows client-side routing to work (e.g., `/matches` refreshes correctly).

### Alternative Deployments

<details>
<summary>Vercel (vercel.json)</summary>

```json
{
  "rewrites": [
    { "source": "/((?!api|_next|static|.*\\..*).*)", "destination": "/" }
  ]
}
```
</details>

<details>
<summary>Netlify (_redirects)</summary>

```
/*    /index.html   200
```
</details>

<details>
<summary>Nginx</summary>

```nginx
location / {
  try_files $uri $uri/ /index.html;
}
```
</details>

## Edge Cases & Pitfalls

### 1. Auth Pages
- Login/logout flows work normally since API calls are not cached
- Session cookies work as expected

### 2. Dynamic Content
- Feed posts, messages, etc. are always fetched fresh (not cached)
- Only static assets (JS/CSS/images) are cached

### 3. iOS Safari
- PWA must be added from Safari (not Chrome/Firefox)
- Some iOS versions have SW limitations - app will still work but may use more network

### 4. Development Mode
- Service worker is NOT registered in development (`npm start`)
- To test SW locally, run `npm run build` then `npx serve -s build`

### 5. Cache Corruption
If users experience issues, they can clear SW cache:
1. Chrome: DevTools → Application → Clear storage → Clear site data
2. Or uninstall and reinstall the PWA

## Troubleshooting

| Issue | Solution |
|-------|----------|
| SW not registering | Check console for errors, ensure HTTPS |
| Old content showing | Bump CACHE_VERSION and deploy |
| Offline page not showing | Ensure offline.html is pre-cached in APP_SHELL_FILES |
| Update notification not appearing | Check swUpdate event is being dispatched |
| PWA not installable | Run Lighthouse audit to identify missing criteria |

## Resources

- [Web.dev PWA Guide](https://web.dev/progressive-web-apps/)
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest)
