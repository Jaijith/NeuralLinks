import React from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Home, Users, Search, Heart, User, Bot } from "lucide-react";
import WorldModeToggle from "./WorldModeToggle";

const Navigation = ({ user }) => {
  const navigate = useNavigate();

  return (
    <nav className="bg-white shadow-md border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          {/* Left - Logo & Home */}
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/home')}
              className="flex items-center space-x-2 hover:opacity-80 transition"
            >
              <div className="text-2xl font-bold bg-gradient-to-r from-pink-500 to-purple-600 bg-clip-text text-transparent">
                AI Dating
              </div>
            </button>
          </div>

          {/* Center - Navigation Links */}
          <div className="flex items-center space-x-2">
            <Button
              onClick={() => navigate('/home')}
              variant="ghost"
              className="flex items-center space-x-2 text-gray-700 hover:bg-purple-50"
            >
              <Home className="w-5 h-5" />
              <span className="hidden md:inline">Home</span>
            </Button>
            
            <Button
              onClick={() => navigate('/friends')}
              variant="ghost"
              className="flex items-center space-x-2 text-gray-700 hover:bg-purple-50"
            >
              <Users className="w-5 h-5" />
              <span className="hidden md:inline">Friends</span>
            </Button>
            
            <Button
              onClick={() => navigate('/search')}
              variant="ghost"
              className="flex items-center space-x-2 text-gray-700 hover:bg-purple-50"
            >
              <Search className="w-5 h-5" />
              <span className="hidden md:inline">Search</span>
            </Button>
            
            <Button
              onClick={() => navigate('/matches')}
              variant="ghost"
              className="flex items-center space-x-2 text-gray-700 hover:bg-purple-50"
            >
              <Heart className="w-5 h-5" />
              <span className="hidden md:inline">Matches</span>
            </Button>
            
            <Button
              onClick={() => navigate('/avatar-control')}
              variant="ghost"
              className="flex items-center space-x-2 text-gray-700 hover:bg-purple-50"
            >
              <Bot className="w-5 h-5" />
              <span className="hidden md:inline">Avatar</span>
            </Button>
          </div>

          {/* Right - World Toggle & Profile */}
          <div className="flex items-center space-x-3">
            <WorldModeToggle />
            
            <Button
              onClick={() => navigate('/myprofile')}
              variant="ghost"
              className="flex items-center space-x-2 text-gray-700 hover:bg-purple-50"
            >
              <User className="w-5 h-5" />
              <span className="hidden md:inline">Profile</span>
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
