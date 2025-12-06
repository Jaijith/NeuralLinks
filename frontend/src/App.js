import { useEffect, useState, lazy, Suspense } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { authService } from "@/services/api";
import { Toaster } from "./components/ui/sonner";
import { toast } from "sonner";
import { WorldModeProvider } from "./contexts/WorldModeContext";
import LazyPage from "./components/common/LazyPage";
import LoadingSpinner from "./components/common/LoadingSpinner";
import ErrorBoundary from "./components/common/ErrorBoundary";

// Lazy load all pages for code splitting
const LandingPage = lazy(() => import("./pages/LandingPage"));
const FacebookStyleHome = lazy(() => import("./pages/FacebookStyleHome"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const OnboardingChat = lazy(() => import("./pages/OnboardingChat"));
const Matches = lazy(() => import("./pages/Matches"));
const Chat = lazy(() => import("./pages/Chat"));
const AvatarChat = lazy(() => import("./pages/AvatarChat"));
const Profile = lazy(() => import("./pages/Profile"));
const ProfilePageFull = lazy(() => import("./pages/ProfilePageFull"));
const SearchPage = lazy(() => import("./pages/SearchPage"));
const FriendsPage = lazy(() => import("./pages/FriendsPage"));
const GalleryPage = lazy(() => import("./pages/GalleryPage"));
const IntegrationsPage = lazy(() => import("./pages/IntegrationsPage"));
const AvatarControl = lazy(() => import("./pages/AvatarControl"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const AvatarVisualization = lazy(() => import("./pages/AvatarVisualization"));

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    try {
      const userData = await authService.getCurrentUser();
      setUser(userData);
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
    return <LoadingSpinner size="lg" message="Loading..." fullScreen />;
  }

  return (
    <ErrorBoundary>
      <WorldModeProvider>
        <div className="App">
          <BrowserRouter>
            <Toaster position="top-right" />
            <Routes>
              <Route 
                path="/" 
                element={
                  user ? (
                    <Navigate to="/home" />
                  ) : (
                    <LazyPage>
                      <LandingPage setUser={setUser} />
                    </LazyPage>
                  )
                } 
              />
              <Route
                path="/onboarding"
                element={
                  user ? (
                    <LazyPage>
                      <OnboardingChat user={user} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/home"
                element={
                  user ? (
                    <LazyPage>
                      <FacebookStyleHome user={user} setUser={setUser} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/dashboard"
                element={
                  user ? (
                    <LazyPage>
                      <Dashboard user={user} setUser={setUser} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/search"
                element={
                  user ? (
                    <LazyPage>
                      <SearchPage user={user} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/friends"
                element={
                  user ? (
                    <LazyPage>
                      <FriendsPage user={user} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/gallery"
                element={
                  user ? (
                    <LazyPage>
                      <GalleryPage user={user} setUser={setUser} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/integrations"
                element={
                  user ? (
                    <LazyPage>
                      <IntegrationsPage user={user} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/settings"
                element={
                  user ? (
                    <LazyPage>
                      <SettingsPage user={user} setUser={setUser} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/avatar-visualization"
                element={
                  user ? (
                    <LazyPage>
                      <AvatarVisualization user={user} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/avatar-control"
                element={
                  user ? (
                    <LazyPage>
                      <AvatarControl user={user} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/matches"
                element={
                  user ? (
                    <LazyPage>
                      <Matches user={user} setUser={setUser} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/chat/:matchId"
                element={
                  user ? (
                    <LazyPage>
                      <Chat user={user} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/avatar-chat/:userId"
                element={
                  user ? (
                    <LazyPage>
                      <AvatarChat user={user} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/profile"
                element={
                  user ? (
                    <LazyPage>
                      <Profile user={user} setUser={setUser} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/profile/:userId"
                element={
                  user ? (
                    <LazyPage>
                      <ProfilePageFull user={user} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
              <Route
                path="/myprofile"
                element={
                  user ? (
                    <LazyPage>
                      <ProfilePageFull user={user} />
                    </LazyPage>
                  ) : (
                    <Navigate to="/" />
                  )
                }
              />
            </Routes>
          </BrowserRouter>
        </div>
      </WorldModeProvider>
    </ErrorBoundary>
  );
}

export default App;
