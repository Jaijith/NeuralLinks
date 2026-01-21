import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { 
  Home, Users, Heart, Search, Settings as SettingsIcon, 
  Image, LogOut, Rocket
} from "lucide-react";
import { useWorldMode } from "@/contexts/WorldModeContext";
import WorldModeToggle from "./WorldModeToggle";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AppHeader = ({ user, setUser, currentPage = 'home' }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const [pendingRequestsCount, setPendingRequestsCount] = useState(0);

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

  return (
    <header className={`shadow-sm sticky top-0 z-50 border-b ${
      worldMode === 'avatar' 
        ? 'bg-slate-900/90 backdrop-blur-md border-blue-500/30' 
        : 'bg-white border-gray-200'
    }`}>
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          {/* Left - Logo & Search */}
          <div className="flex items-center space-x-2 flex-1">
            <div 
              className="w-10 h-10 rounded-full flex items-center justify-center cursor-pointer overflow-hidden bg-transparent"
              onClick={() => navigate('/home')}
            >
              <img 
                src="/logo.png" 
                alt="Logo" 
                className="w-full h-full object-contain"
                onError={(e) => {
                  // Fallback to Heart icon if image not found
                  e.target.style.display = 'none';
                  const fallback = e.target.nextElementSibling;
                  if (fallback) fallback.style.display = 'flex';
                }}
              />
              <div 
                className={`w-full h-full rounded-full flex items-center justify-center hidden ${
                  worldMode === 'avatar' 
                    ? 'bg-gradient-to-br from-blue-500 to-purple-600 avatar-glow' 
                    : 'bg-blue-500'
                }`}
              >
                <Heart className="w-6 h-6 text-white fill-white" />
              </div>
            </div>
            <div className="relative hidden md:block">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search"
                onClick={() => navigate('/search')}
                readOnly
                className={`pl-10 rounded-full w-60 cursor-pointer border-none ${
                  worldMode === 'avatar'
                    ? 'bg-slate-800 text-blue-100 placeholder:text-blue-300/50'
                    : 'bg-gray-100'
                }`}
              />
            </div>
          </div>

          {/* Center - Navigation */}
          <div className="flex items-center space-x-1">
            <Button
              variant="ghost"
              onClick={() => {
                if (currentPage === 'missions') {
                  window.location.href = '/home';
                } else {
                  navigate('/home');
                }
              }}
              className={`px-8 py-2 rounded-lg ${
                currentPage === 'home' 
                  ? worldMode === 'avatar'
                    ? 'border-b-4 border-blue-400'
                    : 'border-b-4 border-blue-500'
                  : ''
              }`}
            >
              <Home className={`w-6 h-6 ${worldMode === 'avatar' ? 'text-blue-300' : 'text-gray-600'}`} />
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                if (currentPage === 'missions') {
                  window.location.href = '/friends';
                } else {
                  navigate('/friends');
                }
              }}
              className={`px-8 py-2 rounded-lg relative ${
                currentPage === 'friends'
                  ? worldMode === 'avatar'
                    ? 'border-b-4 border-blue-400'
                    : 'border-b-4 border-blue-500'
                  : ''
              }`}
            >
              <Users className={`w-6 h-6 ${worldMode === 'avatar' ? 'text-blue-300' : 'text-gray-600'}`} />
              {pendingRequestsCount > 0 && (
                <span className={`absolute top-1 right-1 flex items-center justify-center min-w-[20px] h-5 px-1.5 text-xs font-bold text-white rounded-full ${
                  worldMode === 'avatar' 
                    ? 'bg-blue-500 border-2 border-slate-900' 
                    : 'bg-red-500 border-2 border-white'
                }`}>
                  {pendingRequestsCount > 99 ? '99+' : pendingRequestsCount}
                </span>
              )}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                if (currentPage === 'missions') {
                  window.location.href = '/missions';
                } else {
                  navigate('/missions');
                }
              }}
              className={`px-8 py-2 rounded-lg ${
                currentPage === 'missions'
                  ? worldMode === 'avatar'
                    ? 'border-b-4 border-blue-400'
                    : 'border-b-4 border-blue-500'
                  : ''
              }`}
            >
              <Rocket className={`w-6 h-6 ${worldMode === 'avatar' ? 'text-blue-300' : 'text-gray-600'}`} />
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                if (currentPage === 'missions') {
                  window.location.href = '/gallery';
                } else {
                  navigate('/gallery');
                }
              }}
              className={`px-8 py-2 rounded-lg ${
                currentPage === 'gallery'
                  ? worldMode === 'avatar'
                    ? 'border-b-4 border-blue-400'
                    : 'border-b-4 border-blue-500'
                  : ''
              }`}
            >
              <Image className={`w-6 h-6 ${worldMode === 'avatar' ? 'text-blue-300' : 'text-gray-600'}`} />
            </Button>
          </div>

          {/* Right - World Toggle & Profile */}
          <div className="flex items-center space-x-3 flex-1 justify-end">
            {/* Global World Mode Toggle */}
            <WorldModeToggle />

            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/settings')}
              className="rounded-full p-2"
            >
              <SettingsIcon className={`w-5 h-5 ${worldMode === 'avatar' ? 'text-blue-300' : ''}`} />
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="rounded-full p-2"
            >
              <LogOut className={`w-5 h-5 ${worldMode === 'avatar' ? 'text-blue-300' : 'text-gray-600'}`} />
            </Button>

            <Avatar 
              className={`w-8 h-8 cursor-pointer ${
                worldMode === 'avatar' 
                  ? 'border-2 border-blue-400 avatar-glow' 
                  : 'border-2 border-blue-500'
              }`}
              onClick={() => navigate('/myprofile')}
            >
              <AvatarImage src={user?.picture} />
              <AvatarFallback className={worldMode === 'avatar' ? 'bg-blue-600 text-white text-sm' : 'bg-blue-500 text-white text-sm'}>
                {user?.name?.charAt(0)}
              </AvatarFallback>
            </Avatar>
          </div>
        </div>
      </div>
    </header>
  );
};

export default AppHeader;
