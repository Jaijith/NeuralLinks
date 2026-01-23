/**
 * PWA Update Notification
 * 
 * Shows a non-intrusive banner when a new version of the app is available.
 * Uses a simple design that matches the site's dark theme.
 */

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, X } from 'lucide-react';
import { skipWaiting, listenForControllerChange } from '@/serviceWorkerRegistration';

const PWAUpdateNotification = () => {
  const [showUpdate, setShowUpdate] = useState(false);
  const [registration, setRegistration] = useState(null);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    // Listen for SW updates
    const handleSWUpdate = (event) => {
      if (event.detail && event.detail.registration) {
        setRegistration(event.detail.registration);
        setShowUpdate(true);
      }
    };

    window.addEventListener('swUpdate', handleSWUpdate);
    
    // Listen for controller change to reload
    listenForControllerChange();

    return () => {
      window.removeEventListener('swUpdate', handleSWUpdate);
    };
  }, []);

  const handleUpdate = useCallback(() => {
    if (registration) {
      setIsUpdating(true);
      skipWaiting(registration);
      // Page will reload automatically via controllerchange listener
    }
  }, [registration]);

  const handleDismiss = useCallback(() => {
    setShowUpdate(false);
  }, []);

  return (
    <AnimatePresence>
      {showUpdate && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-auto md:max-w-sm z-[9999]"
        >
          <div 
            className="flex items-center gap-3 p-4 rounded-xl shadow-2xl"
            style={{
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.95), rgba(139, 92, 246, 0.95))',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.1)'
            }}
          >
            {/* Icon */}
            <div className="flex-shrink-0">
              <div 
                className="w-10 h-10 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(255, 255, 255, 0.2)' }}
              >
                <RefreshCw 
                  size={20} 
                  className={`text-white ${isUpdating ? 'animate-spin' : ''}`}
                />
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium text-sm">
                Update Available
              </p>
              <p className="text-white/80 text-xs mt-0.5">
                A new version of 2ness is ready
              </p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={handleUpdate}
                disabled={isUpdating}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                style={{
                  background: 'rgba(255, 255, 255, 0.9)',
                  color: '#6366f1'
                }}
              >
                {isUpdating ? 'Updating...' : 'Update'}
              </button>
              
              <button
                onClick={handleDismiss}
                className="p-1.5 rounded-lg transition-all hover:bg-white/10"
                aria-label="Dismiss"
              >
                <X size={18} className="text-white/70" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default PWAUpdateNotification;
