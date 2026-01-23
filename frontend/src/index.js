import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";
import * as serviceWorkerRegistration from "@/serviceWorkerRegistration";

// Suppress ResizeObserver errors (harmless UI library timing issue)
// These errors don't affect functionality, just browser dev tools noise
const suppressResizeObserverErrors = () => {
  const resizeObserverErr = window.ResizeObserver;
  window.ResizeObserver = class ResizeObserver extends resizeObserverErr {
    constructor(callback) {
      super((entries, observer) => {
        try {
          callback(entries, observer);
        } catch (e) {
          if (
            e.message.includes('ResizeObserver loop') ||
            e.message === 'ResizeObserver loop completed with undelivered notifications.'
          ) {
            // Suppress this specific error
            console.debug('ResizeObserver error suppressed:', e.message);
          } else {
            throw e;
          }
        }
      });
    }
  };
};

suppressResizeObserverErrors();

// Also catch any global errors
window.addEventListener('error', (e) => {
  if (
    e.message && (
      e.message.includes('ResizeObserver loop') ||
      e.message === 'ResizeObserver loop completed with undelivered notifications.'
    )
  ) {
    e.stopImmediatePropagation();
    e.preventDefault();
    return false;
  }
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// Register service worker for PWA support
// This will only activate in production builds
serviceWorkerRegistration.register({
  onSuccess: (registration) => {
    console.log('[App] Service worker registered successfully');
  },
  onUpdate: (registration) => {
    console.log('[App] New app version available');
    // Dispatch custom event that PWAUpdateNotification listens for
    window.dispatchEvent(new CustomEvent('swUpdate', { 
      detail: { registration } 
    }));
  }
});
