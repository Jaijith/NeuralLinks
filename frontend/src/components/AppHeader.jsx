import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { 
  Home, Users, Heart, Search, Settings as SettingsIcon, 
  Image, LogOut, Rocket, Menu, X
} from "lucide-react";
import { useWorldMode } from "@/contexts/WorldModeContext";
import WorldModeToggle from "./WorldModeToggle";
import { ViewModeToggle } from "@/components/ambient";
import useViewMode from "@/hooks/useViewMode";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AppHeader = ({ user, setUser, currentPage = 'home' }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const { isImmersive, toggleViewMode } = useViewMode();
  const isAvatarWorld = worldMode === 'avatar';
  const [pendingRequestsCount, setPendingRequestsCount] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Fetch pending friend requests count
  useEffect(() => {
    const fetchPendingRequests = async () => {
      try {
        const response = await axios.get(`${API}/friends/requests`, {
          withCredentials: true,
        });
        // The API already filters for pending requests only
        const pendingCount = Array.isArray(response.data) ? response.data.length : 0;
        setPendingRequestsCount(pendingCount);
      } catch (error) {
        console.error('Error fetching friend requests:', error);
      }
    };

    // Fetch immediately
    fetchPendingRequests();

    // Poll every 30 seconds for new requests
    const interval = setInterval(fetchPendingRequests, 30000);

    return () => clearInterval(interval);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [currentPage]);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileMenuOpen]);

  const handleLogout = async () => {
    try {
      // Clear user state immediately
      if (setUser) setUser(null);
      
      // Clear localStorage
      localStorage.clear();
      
      // Call logout endpoint and WAIT for it to complete before redirecting
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
      
      // Use window.location for hard redirect to ensure it works from any page
      window.location.href = '/';
    } catch (error) {
      console.error("Logout error:", error);
      // Even if there's an error, still redirect (cookie might still be cleared)
      if (setUser) setUser(null);
      localStorage.clear();
      window.location.href = '/';
    }
  };

  const handleNavigation = (path) => {
    setMobileMenuOpen(false);
    
    // Map paths to page names for comparison
    const pathToPage = {
      '/home': 'home',
      '/friends': 'friends',
      '/missions': 'missions',
      '/gallery': 'gallery',
      '/settings': 'settings',
      '/myprofile': 'profile',
      '/search': 'search'
    };
    
    const targetPage = pathToPage[path];
    
    // If already on the same page, refresh instead of navigating
    if (targetPage === currentPage || (currentPage === 'profile' && path === '/myprofile')) {
      // Use window.location.reload for a full refresh
      window.location.reload();
      return;
    }
    
    if (currentPage === 'missions') {
      window.location.href = path;
    } else {
      navigate(path);
    }
  };

  // Navigation items configuration
  const navItems = [
    { icon: Home, label: 'Home', path: '/home', page: 'home' },
    { icon: Users, label: 'Friends', path: '/friends', page: 'friends', badge: pendingRequestsCount },
    { icon: Rocket, label: 'Missions', path: '/missions', page: 'missions' },
    { icon: Image, label: 'Gallery', path: '/gallery', page: 'gallery' },
  ];

  // Determine dark mode: only dark in avatar world AND immersive mode
  const isDarkMode = isAvatarWorld && isImmersive;

  return (
    <>
      <header className={`shadow-sm fixed top-0 left-0 right-0 z-50 border-b ${
        isDarkMode 
          ? 'border-blue-500/30' 
          : 'border-gray-200'
      }`}
      style={{ 
        paddingTop: 'env(safe-area-inset-top, 0px)',
        isolation: 'isolate',
        backgroundColor: isDarkMode 
          ? 'rgba(15, 23, 42, 0.90)' 
          : 'rgba(255, 255, 255, 0.90)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
      }}
      >
        <div className="max-w-7xl mx-auto px-3 sm:px-4">
          <div className="flex items-center justify-between h-14">
            {/* Left - Logo & Search */}
            <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
              {/* Logo */}
              <div 
                className="w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center cursor-pointer overflow-hidden bg-transparent flex-shrink-0"
                onClick={() => handleNavigation('/home')}
              >
                <img 
                  src="/logo.png" 
                  alt="Logo" 
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    e.target.style.display = 'none';
                    const fallback = e.target.nextElementSibling;
                    if (fallback) fallback.style.display = 'flex';
                  }}
                />
                <div 
                  className={`w-full h-full rounded-full flex items-center justify-center hidden ${
                    isDarkMode 
                      ? 'bg-gradient-to-br from-blue-500 to-purple-600 avatar-glow' 
                      : 'bg-blue-500'
                  }`}
                >
                  <Heart className="w-5 h-5 sm:w-6 sm:h-6 text-white fill-white" />
                </div>
              </div>
              
              {/* Search - hidden on mobile, shown on md+ */}
              <div className="relative hidden md:block">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Search"
                  onClick={() => handleNavigation('/search')}
                  readOnly
                  className={`pl-10 rounded-full w-40 lg:w-60 cursor-pointer border-none text-sm ${
                    isDarkMode
                      ? 'bg-slate-800 text-blue-100 placeholder:text-blue-300/50'
                      : 'bg-gray-100'
                  }`}
                />
              </div>
              
              {/* Mobile search icon */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleNavigation('/search')}
                className="md:hidden p-2 min-w-[44px] min-h-[44px]"
              >
                <Search className={`w-5 h-5 ${isDarkMode ? 'text-blue-300' : 'text-gray-600'}`} />
              </Button>
            </div>

            {/* Center - Desktop Navigation (hidden on mobile) */}
            <nav className="hidden sm:flex items-center gap-1">
              {navItems.map((item) => (
                <Button
                  key={item.page}
                  variant="ghost"
                  onClick={() => handleNavigation(item.path)}
                  className={`px-3 sm:px-4 md:px-6 lg:px-8 py-2 rounded-lg relative min-h-[44px] ${
                    currentPage === item.page 
                      ? isDarkMode
                        ? 'border-b-4 border-blue-400'
                        : 'border-b-4 border-blue-500'
                      : ''
                  }`}
                >
                  <item.icon className={`w-5 h-5 sm:w-6 sm:h-6 ${isDarkMode ? 'text-blue-300' : 'text-gray-600'}`} />
                  {item.badge > 0 && (
                    <span className={`absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white rounded-full ${
                      isDarkMode 
                        ? 'bg-blue-500 border border-slate-900' 
                        : 'bg-red-500 border border-white'
                    }`}>
                      {item.badge > 99 ? '99+' : item.badge}
                    </span>
                  )}
                </Button>
              ))}
            </nav>

            {/* Right - Actions & Profile - with high z-index to ensure buttons are clickable */}
            <div 
              className="flex items-center gap-1 sm:gap-2 flex-shrink-0"
              style={{
                position: 'relative',
                zIndex: 9999,
                isolation: 'isolate',
              }}
            >
              {/* View Mode Toggle (Immersive/Classic) - only in avatar world, always visible */}
              {isAvatarWorld && (
                <div className="block">
                  <ViewModeToggle 
                    isImmersive={isImmersive}
                    onToggle={toggleViewMode}
                    compact={true}
                  />
                </div>
              )}
              
              {/* World Mode Toggle - always visible on mobile */}
              <div className="block">
                <WorldModeToggle />
              </div>

              {/* Settings - hidden on mobile */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleNavigation('/settings')}
                className="hidden sm:flex rounded-full p-2 min-w-[44px] min-h-[44px] items-center justify-center"
              >
                <SettingsIcon className={`w-5 h-5 ${isDarkMode ? 'text-blue-300' : 'text-gray-600'}`} />
              </Button>

              {/* Logout - hidden on mobile */}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="hidden sm:flex rounded-full p-2 min-w-[44px] min-h-[44px] items-center justify-center"
              >
                <LogOut className={`w-5 h-5 ${isDarkMode ? 'text-blue-300' : 'text-gray-600'}`} />
              </Button>

              {/* Profile Avatar */}
              <Avatar 
                className={`w-8 h-8 cursor-pointer flex-shrink-0 ${
                  isDarkMode 
                    ? 'border-2 border-blue-400 avatar-glow' 
                    : 'border-2 border-blue-500'
                }`}
                onClick={() => handleNavigation('/myprofile')}
              >
                <AvatarImage src={user?.picture} />
                <AvatarFallback className={isDarkMode ? 'bg-blue-600 text-white text-sm' : 'bg-blue-500 text-white text-sm'}>
                  {user?.name?.charAt(0)}
                </AvatarFallback>
              </Avatar>

              {/* Mobile Menu Toggle */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="sm:hidden p-2 min-w-[44px] min-h-[44px]"
              >
                {mobileMenuOpen ? (
                  <X className={`w-5 h-5 ${isDarkMode ? 'text-blue-300' : 'text-gray-600'}`} />
                ) : (
                  <Menu className={`w-5 h-5 ${isDarkMode ? 'text-blue-300' : 'text-gray-600'}`} />
                )}
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Navigation Overlay */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 z-40 sm:hidden"
          onClick={() => setMobileMenuOpen(false)}
        >
          {/* Backdrop */}
          <div className={`absolute inset-0 ${
            isDarkMode ? 'bg-slate-900/80' : 'bg-black/50'
          } backdrop-blur-sm`} />
          
          {/* Menu Panel */}
          <div 
            className={`fixed left-0 right-0 ${
              isDarkMode 
                ? 'bg-slate-900 border-b border-blue-500/30' 
                : 'bg-white border-b border-gray-200'
            } shadow-lg`}
            style={{ 
              top: 'calc(56px + env(safe-area-inset-top, 0px))',
              paddingBottom: '1rem',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <nav className="py-2">
              {/* Main Navigation */}
              {navItems.map((item) => (
                <button
                  key={item.page}
                  onClick={() => handleNavigation(item.path)}
                  className={`w-full flex items-center gap-3 px-4 py-3 min-h-[48px] text-left transition-colors ${
                    currentPage === item.page 
                      ? isDarkMode
                        ? 'bg-blue-500/20 text-blue-300'
                        : 'bg-blue-50 text-blue-600'
                      : isDarkMode
                        ? 'text-blue-100 hover:bg-slate-800'
                        : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                  {item.badge > 0 && (
                    <span className={`ml-auto px-2 py-0.5 text-xs font-bold rounded-full ${
                      isDarkMode 
                        ? 'bg-blue-500 text-white' 
                        : 'bg-red-500 text-white'
                    }`}>
                      {item.badge}
                    </span>
                  )}
                </button>
              ))}
              
              {/* Divider */}
              <div className={`my-2 mx-4 h-px ${isDarkMode ? 'bg-blue-500/30' : 'bg-gray-200'}`} />
              
              {/* Secondary Navigation */}
              <button
                onClick={() => handleNavigation('/settings')}
                className={`w-full flex items-center gap-3 px-4 py-3 min-h-[48px] text-left transition-colors ${
                  currentPage === 'settings'
                    ? isDarkMode
                      ? 'bg-blue-500/20 text-blue-300'
                      : 'bg-blue-50 text-blue-600'
                    : isDarkMode
                      ? 'text-blue-100 hover:bg-slate-800'
                      : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <SettingsIcon className="w-5 h-5" />
                <span className="font-medium">Settings</span>
              </button>
              
{/* View Mode Toggle moved to header - always visible */}
              
{/* World Mode Toggle moved to header - always visible */}
              
              {/* Logout */}
              <button
                onClick={handleLogout}
                className={`w-full flex items-center gap-3 px-4 py-3 min-h-[48px] text-left transition-colors ${
                  isDarkMode
                    ? 'text-red-400 hover:bg-red-500/20'
                    : 'text-red-600 hover:bg-red-50'
                }`}
              >
                <LogOut className="w-5 h-5" />
                <span className="font-medium">Log Out</span>
              </button>
            </nav>
          </div>
        </div>
      )}

      {/* Mobile Bottom Navigation Bar (visible on mobile only) */}
      <nav 
        className={`mobile-bottom-nav fixed bottom-0 left-0 right-0 z-40 sm:hidden ${
          isDarkMode 
            ? 'bg-slate-900 border-t border-blue-500/30' 
            : 'bg-white border-t border-gray-200'
        }`}
        style={{ 
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        }}
      >
        <div className="flex items-center justify-around h-14">
          {navItems.map((item) => (
            <button
              key={item.page}
              onClick={(e) => {
                // Guard: don't navigate if any overlay is open (prevents ghost clicks on mobile)
                if (document.querySelector('[data-state="open"][role="dialog"]') || 
                    document.querySelector('[data-radix-dialog-overlay]') ||
                    document.querySelector('[data-radix-dropdown-menu-content]') ||
                    document.querySelector('[data-radix-popover-content]') ||
                    document.querySelector('[data-radix-select-content]') ||
                    document.querySelector('[data-story-popup="open"]')) {
                  e.preventDefault();
                  e.stopPropagation();
                  return;
                }
                handleNavigation(item.path);
              }}
              className={`flex flex-col items-center justify-center gap-0.5 px-3 py-2 min-w-[60px] min-h-[48px] relative ${
                currentPage === item.page 
                  ? isDarkMode
                    ? 'text-blue-400'
                    : 'text-blue-600'
                  : isDarkMode
                    ? 'text-blue-300/60'
                    : 'text-gray-500'
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{item.label}</span>
              {item.badge > 0 && (
                <span className={`absolute top-1 right-1 min-w-[16px] h-4 flex items-center justify-center px-1 text-[9px] font-bold text-white rounded-full ${
                  isDarkMode ? 'bg-blue-500' : 'bg-red-500'
                }`}>
                  {item.badge > 99 ? '99+' : item.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </nav>
    </>
  );
};

export default AppHeader;
