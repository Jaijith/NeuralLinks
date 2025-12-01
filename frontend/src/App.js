import { useEffect, useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import LandingPage from "./pages/LandingPage";
import FacebookStyleHome from "./pages/FacebookStyleHome";
import Dashboard from "./pages/Dashboard";
import OnboardingChat from "./pages/OnboardingChat";
import Matches from "./pages/Matches";
import Chat from "./pages/Chat";
import AvatarChat from "./pages/AvatarChat";
import Profile from "./pages/Profile";
import ProfilePageFull from "./pages/ProfilePageFull";
import SearchPage from "./pages/SearchPage";
import FriendsPage from "./pages/FriendsPage";
import GalleryPage from "./pages/GalleryPage";
import IntegrationsPage from "./pages/IntegrationsPage";
import AvatarControl from "./pages/AvatarControl";
import SettingsPage from "./pages/SettingsPage";
import AvatarVisualization from "./pages/AvatarVisualization";
import { Toaster } from "./components/ui/sonner";
import { toast } from "sonner";
import { WorldModeProvider } from "./contexts/WorldModeContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        withCredentials: true,
      });
      setUser(response.data);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const handleAuthCallback = async () => {
    // Check if we're returning from Google OAuth callback
    // The backend sets the cookie and redirects, so we just need to check auth
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    
    if (code) {
      // We're coming back from OAuth - backend has already set the cookie
      // Just wait a moment for the cookie to be set, then check auth
      setTimeout(async () => {
        await checkAuth();
        toast.success("Welcome to Geneses!");
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname);
      }, 100);
    } else {
      // Normal page load - just check if user is authenticated
      await checkAuth();
    }
  };

  useEffect(() => {
    handleAuthCallback();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <WorldModeProvider>
      <div className="App">
        <BrowserRouter>
          <Toaster position="top-right" />
          <Routes>
            <Route path="/" element={user ? <Navigate to="/home" /> : <LandingPage setUser={setUser} />} />
            <Route
              path="/onboarding"
              element={user ? <OnboardingChat user={user} /> : <Navigate to="/" />}
            />
            <Route
              path="/home"
              element={user ? <FacebookStyleHome user={user} setUser={setUser} /> : <Navigate to="/" />}
            />
            <Route
              path="/dashboard"
              element={user ? <Dashboard user={user} setUser={setUser} /> : <Navigate to="/" />}
            />
            <Route
              path="/search"
              element={user ? <SearchPage user={user} /> : <Navigate to="/" />}
            />
            <Route
              path="/friends"
              element={user ? <FriendsPage user={user} /> : <Navigate to="/" />}
            />
            <Route
              path="/gallery"
              element={user ? <GalleryPage user={user} setUser={setUser} /> : <Navigate to="/" />}
            />
            <Route
              path="/integrations"
              element={user ? <IntegrationsPage user={user} /> : <Navigate to="/" />}
            />
            <Route
              path="/settings"
              element={user ? <SettingsPage user={user} setUser={setUser} /> : <Navigate to="/" />}
            />
            <Route
              path="/avatar-visualization"
              element={user ? <AvatarVisualization user={user} /> : <Navigate to="/" />}
            />
            <Route
              path="/avatar-control"
              element={user ? <AvatarControl user={user} /> : <Navigate to="/" />}
            />
            <Route
              path="/matches"
              element={user ? <Matches user={user} setUser={setUser} /> : <Navigate to="/" />}
            />
            <Route
              path="/chat/:matchId"
              element={user ? <Chat user={user} /> : <Navigate to="/" />}
            />
            <Route
              path="/avatar-chat/:userId"
              element={user ? <AvatarChat user={user} /> : <Navigate to="/" />}
            />
            <Route
              path="/profile"
              element={user ? <Profile user={user} setUser={setUser} /> : <Navigate to="/" />}
            />
            <Route
              path="/profile/:userId"
              element={user ? <ProfilePageFull user={user} /> : <Navigate to="/" />}
            />
            <Route
              path="/myprofile"
              element={user ? <ProfilePageFull user={user} /> : <Navigate to="/" />}
            />
          </Routes>
        </BrowserRouter>
      </div>
    </WorldModeProvider>
  );
}

export default App;
