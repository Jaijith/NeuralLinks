/**
 * 2ness Service Worker
 * 
 * Caching Strategy:
 * - Network-first for HTML/navigation (keeps app fresh)
 * - Cache-first for static assets (JS/CSS/images/fonts)
 * - No caching for API responses (avoid auth/private data issues)
 * 
 * Update CACHE_VERSION when releasing new versions.
 */

const CACHE_VERSION = 'v1.0.0';
const STATIC_CACHE = `2ness-static-${CACHE_VERSION}`;
const APP_SHELL_CACHE = `2ness-app-shell-${CACHE_VERSION}`;

// Static assets to pre-cache (app shell)
const APP_SHELL_FILES = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.webmanifest',
  '/logo.png',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
];

// Patterns for static assets (cache-first)
const STATIC_ASSET_PATTERNS = [
  /\.js$/,
  /\.css$/,
  /\.woff2?$/,
  /\.ttf$/,
  /\.eot$/,
  /\.png$/,
  /\.jpg$/,
  /\.jpeg$/,
  /\.gif$/,
  /\.svg$/,
  /\.webp$/,
  /\.ico$/
];

// Patterns to NEVER cache (API calls, auth endpoints)
const NEVER_CACHE_PATTERNS = [
  /\/api\//,
  /\/auth\//,
  /api\.2ness\.com/,
  /posthog\.com/,
  /cloudfront\.net.*rrweb/,
  /unpkg\.com/
];

// ============================================================================
// INSTALL - Pre-cache app shell
// ============================================================================
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker', CACHE_VERSION);
  
  event.waitUntil(
    caches.open(APP_SHELL_CACHE)
      .then((cache) => {
        console.log('[SW] Pre-caching app shell');
        return cache.addAll(APP_SHELL_FILES);
      })
      .then(() => {
        // Skip waiting to activate immediately
        return self.skipWaiting();
      })
      .catch((err) => {
        console.error('[SW] Pre-cache failed:', err);
      })
  );
});

// ============================================================================
// ACTIVATE - Clean up old caches
// ============================================================================
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker', CACHE_VERSION);
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              // Delete caches that don't match current version
              return name.startsWith('2ness-') && 
                     name !== STATIC_CACHE && 
                     name !== APP_SHELL_CACHE;
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        // Take control of all clients immediately
        return self.clients.claim();
      })
  );
});

// ============================================================================
// FETCH - Handle requests
// ============================================================================
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Only handle GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Check if this should never be cached
  if (shouldNeverCache(url)) {
    return; // Let the browser handle it normally
  }
  
  // Handle navigation requests (HTML) - Network first with offline fallback
  if (request.mode === 'navigate' || request.destination === 'document') {
    event.respondWith(networkFirstWithOfflineFallback(request));
    return;
  }
  
  // Handle static assets - Cache first
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirstWithNetwork(request));
    return;
  }
  
  // Default: Network first (no cache)
  event.respondWith(
    fetch(request).catch(() => {
      // If network fails and it's a navigation-like request, show offline page
      if (request.headers.get('accept')?.includes('text/html')) {
        return caches.match('/offline.html');
      }
      return new Response('Network error', { status: 503 });
    })
  );
});

// ============================================================================
// Caching Strategies
// ============================================================================

/**
 * Network first with offline fallback for navigation
 */
async function networkFirstWithOfflineFallback(request) {
  try {
    // Try network first
    const networkResponse = await fetch(request);
    
    // Cache successful response
    if (networkResponse.ok) {
      const cache = await caches.open(APP_SHELL_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    
    // Try cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Try index.html for SPA routes
    const indexResponse = await caches.match('/index.html');
    if (indexResponse) {
      return indexResponse;
    }
    
    // Last resort: offline page
    return caches.match('/offline.html');
  }
}

/**
 * Cache first with network fallback for static assets
 */
async function cacheFirstWithNetwork(request) {
  // Try cache first
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    // Fetch from network
    const networkResponse = await fetch(request);
    
    // Cache successful response
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Failed to fetch static asset:', request.url);
    // Return empty response for failed static assets
    return new Response('', { status: 503 });
  }
}

// ============================================================================
// Helpers
// ============================================================================

function shouldNeverCache(url) {
  return NEVER_CACHE_PATTERNS.some(pattern => pattern.test(url.href));
}

function isStaticAsset(url) {
  // Check if it's from the same origin
  if (url.origin !== self.location.origin) {
    return false;
  }
  
  // Check against static asset patterns
  return STATIC_ASSET_PATTERNS.some(pattern => pattern.test(url.pathname));
}

// ============================================================================
// MESSAGE HANDLING - For update notifications
// ============================================================================
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
