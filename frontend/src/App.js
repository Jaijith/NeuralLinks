import { useEffect, useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import LandingPage from "./pages/LandingPage";
import Dashboard from "./pages/Dashboard";
import OnboardingChat from "./pages/OnboardingChat";
import Matches from "./pages/Matches";
import Chat from "./pages/Chat";
import Profile from "./pages/Profile";
import ProfilePageFull from "./pages/ProfilePageFull";
import SearchPage from "./pages/SearchPage";
import FriendsPage from "./pages/FriendsPage";
import IntegrationsPage from "./pages/IntegrationsPage";
import { Toaster } from "./components/ui/sonner";
import { toast } from "sonner";

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
    const hash = window.location.hash;
    if (hash && hash.includes("session_id=")) {
      const sessionId = hash.split("session_id=")[1].split("&")[0];
      
      try {
        const response = await axios.get(`${API}/auth/session-data`, {
          headers: { "X-Session-ID": sessionId },
          withCredentials: true,
        });

        document.cookie = `session_token=${response.data.session_token}; path=/; secure; samesite=none; max-age=604800`;

        // Clear the hash from URL
        window.history.replaceState({}, document.title, window.location.pathname);

        // Fetch user data
        await checkAuth();
        
        toast.success("Welcome to AI Dating Match!");
      } catch (error) {
        console.error("Auth error:", error);
        toast.error("Authentication failed. Please try again.");
        setLoading(false);
      }
    } else {
      checkAuth();
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
    <div className="App">
      <BrowserRouter>
        <Toaster position="top-right" />
        <Routes>
          <Route path="/" element={user ? <Navigate to="/dashboard" /> : <LandingPage setUser={setUser} />} />
          <Route
            path="/onboarding"
            element={user ? <OnboardingChat user={user} /> : <Navigate to="/" />}
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
            path="/integrations"
            element={user ? <IntegrationsPage user={user} /> : <Navigate to="/" />}
          />
          <Route
            path="/matches"
            element={user ? <Matches user={user} /> : <Navigate to="/" />}
          />
          <Route
            path="/chat/:matchId"
            element={user ? <Chat user={user} /> : <Navigate to="/" />}
          />
          <Route
            path="/profile"
            element={user ? <Profile user={user} setUser={setUser} /> : <Navigate to="/" />}
          />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
