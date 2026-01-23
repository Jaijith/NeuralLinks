/**
 * Service Worker Registration
 * 
 * This module handles service worker registration and update detection.
 * Only registers in production builds to avoid issues during development.
 */

// Check if service workers are supported
const isLocalhost = Boolean(
  window.location.hostname === 'localhost' ||
  window.location.hostname === '[::1]' ||
  window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/)
);

/**
 * Register the service worker
 * @param {Object} config - Configuration options
 * @param {Function} config.onSuccess - Called when SW is successfully installed
 * @param {Function} config.onUpdate - Called when a new SW update is available
 */
export function register(config = {}) {
  // Only register in production
  if (process.env.NODE_ENV !== 'production') {
    console.log('[SW Registration] Skipping in development mode');
    return;
  }

  if (!('serviceWorker' in navigator)) {
    console.log('[SW Registration] Service workers not supported');
    return;
  }

  // Wait for page load
  window.addEventListener('load', () => {
    const swUrl = '/sw.js';

    if (isLocalhost) {
      // Running on localhost - check if SW exists
      checkValidServiceWorker(swUrl, config);
      navigator.serviceWorker.ready.then(() => {
        console.log('[SW Registration] Running on localhost with service worker');
      });
    } else {
      // Not localhost - register SW
      registerValidSW(swUrl, config);
    }
  });
}

/**
 * Register a valid service worker
 */
function registerValidSW(swUrl, config) {
  navigator.serviceWorker
    .register(swUrl)
    .then((registration) => {
      console.log('[SW Registration] Registered successfully');

      // Check for updates periodically (every 60 seconds)
      setInterval(() => {
        registration.update();
      }, 60000);

      registration.onupdatefound = () => {
        const installingWorker = registration.installing;
        if (installingWorker == null) {
          return;
        }

        installingWorker.onstatechange = () => {
          if (installingWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              // New content is available; notify user
              console.log('[SW Registration] New content available');
              
              if (config && config.onUpdate) {
                config.onUpdate(registration);
              }
            } else {
              // Content is cached for offline use
              console.log('[SW Registration] Content cached for offline use');
              
              if (config && config.onSuccess) {
                config.onSuccess(registration);
              }
            }
          }
        };
      };
    })
    .catch((error) => {
      console.error('[SW Registration] Error:', error);
    });
}

/**
 * Check if service worker is valid (for localhost)
 */
function checkValidServiceWorker(swUrl, config) {
  fetch(swUrl, {
    headers: { 'Service-Worker': 'script' },
  })
    .then((response) => {
      const contentType = response.headers.get('content-type');
      if (
        response.status === 404 ||
        (contentType != null && contentType.indexOf('javascript') === -1)
      ) {
        // No service worker found - reload page
        navigator.serviceWorker.ready.then((registration) => {
          registration.unregister().then(() => {
            window.location.reload();
          });
        });
      } else {
        // Service worker found - proceed
        registerValidSW(swUrl, config);
      }
    })
    .catch(() => {
      console.log('[SW Registration] No internet connection - app running offline');
    });
}

/**
 * Unregister the service worker
 */
export function unregister() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.unregister();
      })
      .catch((error) => {
        console.error('[SW Registration] Unregister error:', error);
      });
  }
}

/**
 * Skip waiting and activate new service worker immediately
 * Call this when user confirms they want to update
 */
export function skipWaiting(registration) {
  if (registration && registration.waiting) {
    registration.waiting.postMessage({ type: 'SKIP_WAITING' });
  }
}

/**
 * Listen for controller change (new SW activated)
 * This will reload the page when a new SW takes control
 */
export function listenForControllerChange() {
  if ('serviceWorker' in navigator) {
    let refreshing = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!refreshing) {
        refreshing = true;
        window.location.reload();
      }
    });
  }
}
