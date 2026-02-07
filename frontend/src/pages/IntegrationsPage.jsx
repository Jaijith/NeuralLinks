import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ArrowLeft, CheckCircle, XCircle, RefreshCw, Video, Book, Heart, ShoppingCart, X } from "lucide-react";
import { useWorldMode } from "@/contexts/WorldModeContext";
import useViewMode from "@/hooks/useViewMode";
import {
  FaInstagram,
  FaFacebook,
  FaTwitter,
  FaLinkedin,
  FaTiktok,
  FaSnapchat,
  FaPinterest,
  FaReddit,
  FaDiscord,
  FaWhatsapp,
  FaTelegram,
  FaSpotify,
  FaYoutube,
  FaTwitch,
  FaApple,
  FaSoundcloud,
  FaAmazon,
  FaGoodreads,
  FaMedium,
  FaAudible,
} from "react-icons/fa";
import {
  SiWalmart,
  SiNike,
  SiGarmin,
  SiCoursera,
  SiUdemy,
  SiNetflix,
} from "react-icons/si";
import axios from "axios";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Map platform names to their brand icons
const getPlatformIcon = (platformName) => {
  const iconMap = {
    instagram: FaInstagram,
    facebook: FaFacebook,
    twitter: FaTwitter,
    linkedin: FaLinkedin,
    tiktok: FaTiktok,
    snapchat: FaSnapchat,
    pinterest: FaPinterest,
    reddit: FaReddit,
    discord: FaDiscord,
    whatsapp: FaWhatsapp,
    telegram: FaTelegram,
    spotify: FaSpotify,
    youtube: FaYoutube,
    netflix: SiNetflix,
    twitch: FaTwitch,
    apple_music: FaApple,
    soundcloud: FaSoundcloud,
    hulu: FaYoutube, // Using YouTube icon as fallback for Hulu
    disney_plus: Video, // Using Video icon as fallback for Disney+
    prime_video: Video, // Using Video icon as fallback for Prime Video
    hbo_max: Video, // Using Video icon as fallback for HBO Max
    amazon: FaAmazon,
    walmart: SiWalmart,
    nike_run_club: SiNike,
    garmin: SiGarmin,
    goodreads: FaGoodreads,
    medium: FaMedium,
    kindle: Book, // Using Book icon from lucide-react for Kindle
    audible: FaAudible,
    coursera: SiCoursera,
    udemy: SiUdemy,
  };
  
  return iconMap[platformName?.toLowerCase()] || ShoppingCart;
};

// Get platform colors based on platform_name
const getPlatformColor = (platformName) => {
  const colorMap = {
    instagram: 'from-pink-500 via-purple-500 to-orange-500',
    facebook: 'from-blue-500 to-blue-600',
    twitter: 'from-blue-400 to-blue-500',
    linkedin: 'from-blue-600 to-blue-700',
    tiktok: 'from-black to-gray-800',
    snapchat: 'from-yellow-400 to-yellow-500',
    pinterest: 'from-red-500 to-red-600',
    reddit: 'from-orange-500 to-orange-600',
    discord: 'from-indigo-500 to-indigo-600',
    whatsapp: 'from-green-500 to-green-600',
    telegram: 'from-blue-400 to-blue-500',
    spotify: 'from-green-500 to-green-600',
    youtube: 'from-red-500 to-red-600',
    netflix: 'from-red-600 to-red-700',
    twitch: 'from-purple-500 to-purple-600',
    apple_music: 'from-pink-500 to-pink-600',
    soundcloud: 'from-orange-500 to-orange-600',
    hulu: 'from-green-500 to-green-600',
    disney_plus: 'from-blue-500 to-blue-600',
    prime_video: 'from-blue-600 to-blue-700',
    hbo_max: 'from-purple-600 to-purple-700',
    amazon: 'from-orange-400 to-orange-500',
    walmart: 'from-blue-500 to-blue-600',
    nike_run_club: 'from-black to-gray-800',
    garmin: 'from-teal-500 to-teal-600',
    goodreads: 'from-orange-500 to-orange-600',
    medium: 'from-black to-gray-800',
    kindle: 'from-orange-500 to-orange-600',
    audible: 'from-orange-500 to-orange-600',
    coursera: 'from-blue-500 to-blue-600',
    udemy: 'from-purple-500 to-purple-600',
  };
  
  return colorMap[platformName?.toLowerCase()] || 'from-gray-500 to-gray-600';
};

const IntegrationsPage = ({ user, hideHeader = false }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const { isImmersive } = useViewMode();
  const isAvatarWorld = worldMode === 'avatar';
  const [integrations, setIntegrations] = useState({
    social_media: [],
    media_entertainment: [],
    ecommerce: [],
    fitness_health: [],
    reading_learning: []
  });
  const [loading, setLoading] = useState(true);
  const [showLinkedInDialog, setShowLinkedInDialog] = useState(false);
  const [showYouTubeDialog, setShowYouTubeDialog] = useState(false);
  const [linkedInCredentials, setLinkedInCredentials] = useState({
    client_id: "",
    client_secret: ""
  });
  const [youtubeCredentials, setYoutubeCredentials] = useState({
    client_id: "",
    client_secret: ""
  });

  // Apply avatar-world class to body when in avatar mode
  useEffect(() => {
    if (isAvatarWorld) {
      document.body.classList.add('avatar-world');
    } else {
      document.body.classList.remove('avatar-world');
    }
    return () => {
      document.body.classList.remove('avatar-world');
    };
  }, [isAvatarWorld]);

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const fetchIntegrations = async () => {
    try {
      const response = await axios.get(`${API}/integrations`, {
        withCredentials: true,
      });
      
      // Transform backend response to match UI structure
      // Handle both response formats for compatibility
      let platformData = [];
      if (response.data.integrations) {
        platformData = response.data.integrations;
      } else if (Array.isArray(response.data)) {
        platformData = response.data;
      } else if (response.data.social_media || response.data.media_entertainment) {
        // Old format - flatten all categories
        platformData = [
          ...(response.data.social_media || []),
          ...(response.data.media_entertainment || []),
          ...(response.data.ecommerce || []),
          ...(response.data.fitness_health || []),
          ...(response.data.reading_learning || [])
        ];
      }
      
      console.log("Platform data received:", platformData);
      console.log("Number of platforms:", platformData.length);
      
      // Debug: Log all platform names
      if (platformData.length > 0) {
        console.log("All platform names:", platformData.map(p => p.platform_name || p.name));
      } else {
        console.warn("No platforms received from backend!");
      }
      
      const categorized = {
        social_media: platformData.filter(p => 
          ['instagram', 'facebook', 'twitter', 'linkedin', 'tiktok', 'snapchat', 'pinterest', 'reddit', 'discord', 'whatsapp', 'telegram'].includes(p.platform_name)
        ),
        media_entertainment: platformData.filter(p => 
          ['spotify', 'youtube', 'twitch', 'apple_music', 'soundcloud', 'hulu', 'disney_plus', 'prime_video', 'hbo_max'].includes(p.platform_name)
        ),
        ecommerce: platformData.filter(p => 
          ['amazon', 'walmart'].includes(p.platform_name)
        ),
        fitness_health: platformData.filter(p => 
          ['nike_run_club', 'garmin'].includes(p.platform_name)
        ),
        reading_learning: platformData.filter(p => 
          ['goodreads', 'medium', 'kindle', 'audible', 'coursera', 'udemy'].includes(p.platform_name)
        )
      };
      
      console.log("Categorized platforms:", {
        social_media: categorized.social_media.length,
        media_entertainment: categorized.media_entertainment.length,
        ecommerce: categorized.ecommerce.length,
        fitness_health: categorized.fitness_health.length,
        reading_learning: categorized.reading_learning.length,
        total: platformData.length
      });
      
      setIntegrations(categorized);
    } catch (error) {
      console.error("Error fetching integrations:", error);
      toast.error("Failed to load integrations");
    } finally {
      setLoading(false);
    }
  };

  const connectPlatform = async (platformName, credentials = null) => {
    // For LinkedIn, show dialog immediately if no credentials provided
    if (platformName === "linkedin" && !credentials) {
      setShowLinkedInDialog(true);
      return;
    }
    
    // For YouTube, show dialog immediately if no credentials provided
    if (platformName === "youtube" && !credentials) {
      setShowYouTubeDialog(true);
      return;
    }
    
    try {
      const requestData = { platform_name: platformName };
      
      // For LinkedIn, include credentials if provided
      if (platformName === "linkedin" && credentials) {
        requestData.client_id = credentials.client_id;
        requestData.client_secret = credentials.client_secret;
        console.log("Sending LinkedIn credentials:", {
          has_client_id: !!requestData.client_id,
          has_client_secret: !!requestData.client_secret,
          client_id_length: requestData.client_id?.length || 0
        });
      }
      
      // For YouTube, include credentials if provided
      if (platformName === "youtube" && credentials) {
        requestData.client_id = credentials.client_id;
        requestData.client_secret = credentials.client_secret;
        console.log("Sending YouTube credentials:", {
          has_client_id: !!requestData.client_id,
          has_client_secret: !!requestData.client_secret,
          client_id_length: requestData.client_id?.length || 0
        });
      }
      
      console.log("Connecting platform:", platformName, "with data keys:", Object.keys(requestData));
      
      const response = await axios.post(`${API}/integrations/connect`, 
        requestData,
        { 
          withCredentials: true,
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      
      // Check if OAuth flow is required
      if (response.data.auth_url) {
        console.log("OAuth URL received:", response.data.auth_url);
        // Open OAuth URL in same window (will redirect back after auth)
        window.location.href = response.data.auth_url;
        toast.info(`Redirecting to ${platformName} for authorization...`);
        return;
      }
      
      // Regular connection (no OAuth)
      console.log("No auth_url in response, treating as regular connection:", response.data);
      toast.success(`${platformName} connected!`);
      fetchIntegrations();
    } catch (error) {
      console.error("Error connecting platform:", error);
      const errorMessage = error.response?.data?.detail || "Failed to connect platform";
      
      // Show dialog for LinkedIn if credentials were provided but still failed
      if (platformName === "linkedin" && credentials) {
        toast.error(errorMessage, { duration: 5000 });
        setShowLinkedInDialog(true);
      } else if (platformName === "youtube" && credentials) {
        toast.error(errorMessage, { duration: 5000 });
        setShowYouTubeDialog(true);
      } else {
        toast.error(errorMessage, { duration: 5000 });
      }
    }
  };

  const handleLinkedInSubmit = () => {
    const { client_id: clientId, client_secret: clientSecret } = linkedInCredentials;
    if (!clientId || !clientSecret) {
      toast.error("Please enter both Client ID and Client Secret");
      return;
    }
    setShowLinkedInDialog(false);
    connectPlatform("linkedin", {
      client_id: clientId,
      client_secret: clientSecret
    });
  };

  const handleYouTubeSubmit = () => {
    const { client_id: clientId, client_secret: clientSecret } = youtubeCredentials;
    if (!clientId || !clientSecret) {
      toast.error("Please enter both Client ID and Client Secret");
      return;
    }
    setShowYouTubeDialog(false);
    connectPlatform("youtube", {
      client_id: clientId,
      client_secret: clientSecret
    });
  };

  const disconnectPlatform = async (platformName) => {
    if (!window.confirm(`Are you sure you want to disconnect ${platformName}? You'll need to reconnect to sync data again.`)) {
      return;
    }
    
    try {
      toast.loading(`Disconnecting ${platformName}...`, { id: "disconnect" });
      await axios.post(`${API}/integrations/disconnect`, 
        { platform_name: platformName },
        { withCredentials: true }
      );
      
      toast.success(`${platformName} disconnected successfully`, { id: "disconnect" });
      fetchIntegrations();
    } catch (error) {
      console.error("Error disconnecting platform:", error);
      const errorMessage = error.response?.data?.detail || "Failed to disconnect platform";
      toast.error(errorMessage, { id: "disconnect" });
    }
  };

  const syncPlatform = async (platformName) => {
    try {
      // For LinkedIn, check if OAuth is completed
      if (platformName === "linkedin") {
        const linkedinPlatform = integrations.social_media?.find(p => p.platform_name === "linkedin");
        if (linkedinPlatform && !linkedinPlatform.access_token) {
          toast.error("Please complete LinkedIn OAuth first", { id: "sync" });
          return;
        }
      }
      
      toast.loading(`Syncing ${platformName}...`, { id: "sync" });
      const response = await axios.post(`${API}/integrations/sync`, 
        { platform_name: platformName },
        { withCredentials: true }
      );
      
      toast.success(
        `Synced! Added ${response.data.nodes_added || 0} nodes to your graph. ${
          response.data.profile_updated ? "Profile updated!" : ""
        }`,
        { id: "sync" }
      );
      
      // Dispatch event to notify AvatarVisualization to refresh
      if (platformName === "youtube") {
        window.dispatchEvent(new CustomEvent('youtube-sync-complete', { 
          detail: { nodes_added: response.data.nodes_added } 
        }));
      } else if (platformName === "linkedin") {
        window.dispatchEvent(new CustomEvent('linkedin-sync-complete', { 
          detail: { nodes_added: response.data.nodes_added } 
        }));
      }
      
      // Refresh user data if profile was updated
      if (response.data.profile_updated) {
        // Trigger a page refresh or update user context
        window.location.reload();
      }
      
      fetchIntegrations();
    } catch (error) {
      console.error("Error syncing platform:", error);
      const errorMessage = error.response?.data?.detail || "Failed to sync platform";
      toast.error(errorMessage, { id: "sync" });
      
      // If LinkedIn OAuth not completed, suggest completing it
      if (platformName === "linkedin" && errorMessage.includes("OAuth not completed")) {
        toast.info("Click 'Connect LinkedIn' to complete OAuth", { id: "sync-hint" });
      }
    }
  };


  const PlatformCard = ({ platform }) => {
    // Handle both name and platform_name for compatibility
    const platformName = platform.name || platform.platform_name || 'Unknown';
    const platformId = platform.platform_name || platform.name || '';
    const IconComponent = getPlatformIcon(platformId);
    const gradient = getPlatformColor(platformId);
    
    return (
      <Card className={`${isAvatarWorld ? 'card-avatar' : 'glass-morphism'} p-6 card-hover`} data-testid={`platform-${platformId}`}>
        <div className="flex items-start justify-between mb-4">
          <div className={`w-12 h-12 bg-gradient-to-br ${gradient} rounded-xl flex items-center justify-center shadow-lg`}>
            <IconComponent className="w-6 h-6 text-white" />
          </div>
          {platform.connected ? (
            <Badge className={isAvatarWorld ? 'bg-yellow-400 text-slate-900 font-bold' : 'bg-green-100 text-green-700'}>
              <CheckCircle className="w-3 h-3 mr-1" />
              Connected
            </Badge>
          ) : (
            <Badge className={isAvatarWorld ? 'bg-yellow-400/50 text-slate-800 font-semibold' : 'bg-gray-100 text-gray-700'}>
              <XCircle className="w-3 h-3 mr-1" />
              Available
            </Badge>
          )}
        </div>
        <h3 className={`text-lg font-bold mb-2 ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>
          {platformName}
        </h3>
        <p className={`text-sm mb-4 ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-600'}`}>
          {platform.description || 'Connect to sync your data'}
        </p>
        
        {platform.connected ? (
          <div className="space-y-2">
            <div className="flex gap-2">
              <Button
                onClick={() => syncPlatform(platformId)}
                variant="outline"
                className={isAvatarWorld ? 'flex-1 border-2 border-yellow-400 text-yellow-700 hover:bg-yellow-500/20 rounded-full font-semibold' : 'flex-1 border-2 border-purple-300 text-purple-700 hover:bg-purple-50 rounded-full'}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Sync Data
              </Button>
              <Button
                onClick={() => disconnectPlatform(platformId)}
                variant="ghost"
                className={isAvatarWorld ? 'text-red-600 hover:text-red-700 hover:bg-red-50/50 rounded-full border border-red-400 font-semibold' : 'text-red-600 hover:text-red-700 hover:bg-red-50 rounded-full border border-red-200'}
                size="default"
              >
                <X className="w-4 h-4 mr-1" />
                Disconnect
              </Button>
            </div>
            {platformId === "youtube" && (
              <p className={`text-xs text-center mt-1 ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-500'}`}>
                Sync will analyze your watch history and update your character
              </p>
            )}
          </div>
        ) : (
          <Button
            onClick={() => connectPlatform(platformId)}
            className={`w-full rounded-full hover:shadow-lg ${
              isAvatarWorld 
                ? 'bg-yellow-500 hover:bg-yellow-600 text-slate-900 font-bold' 
                : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white'
            }`}
          >
            Connect {platformName}
          </Button>
        )}
      </Card>
    );
  };

  const PlatformCard_old = ({ platform }) => {
    const Icon = platformIcons[platform.platform_name] || ShoppingCart;
    const gradient = platformColors[platform.platform_name] || 'from-gray-500 to-gray-600';
    
    return (
      <Card className="glass-morphism p-6 card-hover" data-testid={`platform-${platform.platform_name}`}>
        <div className="flex items-start justify-between mb-4">
          <div className={`w-12 h-12 bg-gradient-to-br ${gradient} rounded-xl flex items-center justify-center`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          {platform.connected ? (
            <Badge className="bg-green-100 text-green-700">
              <CheckCircle className="w-3 h-3 mr-1" />
              Connected
            </Badge>
          ) : (
            <Badge className="bg-gray-100 text-gray-700">
              <XCircle className="w-3 h-3 mr-1" />
              Disconnected
            </Badge>
          )}
        </div>
        <h3 className="text-lg font-bold text-gray-800 mb-2">{platform.platform_name}</h3>
        <div className="space-y-2 text-sm text-gray-600">
          <p>Connected: {new Date(platform.connected_at).toLocaleDateString()}</p>
          <p>Last sync: {new Date(platform.last_sync).toLocaleDateString()}</p>
          <p>Data collected: {platform.data_collected} items</p>
        </div>
        <Button
          variant="outline"
          className="w-full mt-4 border-2 border-purple-300 text-purple-700 hover:bg-purple-50 rounded-full"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Sync Now
        </Button>
      </Card>
    );
  };

  const IntegrationSection = ({ title, platforms, icon: Icon, color }) => {
    // Always show the section, even if empty (so user knows what's available)
    return (
      <div className="mb-12">
        <div className="flex items-center space-x-3 mb-6">
          <div className={`w-10 h-10 bg-gradient-to-br ${color} rounded-xl flex items-center justify-center`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className={`text-2xl font-bold ${isAvatarWorld ? 'text-yellow-200' : 'text-gray-800'}`}>
              {title}
            </h2>
            <p className={`text-sm ${isAvatarWorld ? 'text-blue-100 font-semibold' : 'text-gray-600'}`}>
              {platforms.length} {platforms.length === 1 ? 'platform' : 'platforms'} available
            </p>
          </div>
        </div>
        {platforms.length > 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {platforms.map((platform, idx) => (
              <PlatformCard key={idx} platform={platform} />
            ))}
          </div>
        ) : (
          <Card className={isAvatarWorld ? 'card-avatar p-6' : 'glass-morphism p-6'}>
            <p className={`text-center ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-500'}`}>
              No platforms in this category yet
            </p>
          </Card>
        )}
      </div>
    );
  };

  return (
    <div className={hideHeader ? "" : `min-h-screen ${isAvatarWorld ? 'bg-gradient-to-br from-pink-500 via-purple-600 to-indigo-700' : 'bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50'}`}>
      <div className={hideHeader ? "" : "max-w-7xl mx-auto px-6 py-8"}>
        {/* Header */}
        {!hideHeader && (
          <div className="flex items-center space-x-4 mb-8">
            <Button
              variant="ghost"
              onClick={() => navigate("/dashboard")}
              data-testid="back-btn"
              className={isAvatarWorld ? 'hover:bg-yellow-500/20 text-yellow-200' : 'hover:bg-purple-50'}
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className={`text-4xl font-bold ${isAvatarWorld ? 'text-yellow-200' : 'gradient-text'}`}>
                Connected Platforms
              </h1>
              <p className={isAvatarWorld ? 'text-blue-100 font-semibold' : 'text-gray-600'}>
                Your AI agent learns from all your connected accounts
              </p>
            </div>
          </div>
        )}

        {loading ? (
          <div className="text-center py-20">
            <div className={`w-16 h-16 border-4 ${isAvatarWorld ? 'border-yellow-400' : 'border-purple-400'} border-t-transparent rounded-full animate-spin mx-auto mb-4`}></div>
            <p className={isAvatarWorld ? 'text-blue-100 font-semibold' : 'text-gray-600'}>
              Loading integrations...
            </p>
          </div>
        ) : (
          <div>
            <IntegrationSection
              title="Social Media"
              platforms={integrations.social_media}
              icon={FaFacebook}
              color="from-blue-500 to-purple-600"
            />
            <IntegrationSection
              title="Media & Entertainment"
              platforms={integrations.media_entertainment}
              icon={Video}
              color="from-red-500 to-pink-600"
            />
            <IntegrationSection
              title="E-commerce"
              platforms={integrations.ecommerce}
              icon={ShoppingCart}
              color="from-orange-500 to-red-600"
            />
            <IntegrationSection
              title="Fitness & Health"
              platforms={integrations.fitness_health}
              icon={Heart}
              color="from-green-500 to-teal-600"
            />
            <IntegrationSection
              title="Reading & Learning"
              platforms={integrations.reading_learning}
              icon={Book}
              color="from-purple-500 to-indigo-600"
            />

            {/* LinkedIn OAuth Credentials Dialog */}
            <Dialog open={showLinkedInDialog} onOpenChange={setShowLinkedInDialog}>
              <DialogContent 
                className="rounded-2xl border"
                style={{ 
                  backgroundColor: isImmersive ? 'rgba(10, 15, 30, 0.98)' : '#ffffff',
                  borderColor: isImmersive ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0',
                }}
              >
                <DialogHeader>
                  <DialogTitle>LinkedIn OAuth Setup</DialogTitle>
                  <DialogDescription>
                    Enter your LinkedIn app credentials to connect your profile.
                    <br />
                    <a 
                      href="https://www.linkedin.com/developers/apps" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-purple-600 hover:underline mt-2 inline-block"
                    >
                      Create a LinkedIn app here →
                    </a>
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Client ID
                    </label>
                    <Input
                      type="text"
                      placeholder="Enter your LinkedIn Client ID"
                      value={linkedInCredentials.client_id}
                      onChange={(e) => setLinkedInCredentials({ ...linkedInCredentials, client_id: e.target.value })}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Client Secret
                    </label>
                    <Input
                      type="password"
                      placeholder="Enter your LinkedIn Client Secret"
                      value={linkedInCredentials.client_secret}
                      onChange={(e) => setLinkedInCredentials({ ...linkedInCredentials, client_secret: e.target.value })}
                      className="w-full"
                    />
                  </div>
                  <div className="text-xs text-gray-500 bg-yellow-50 p-3 rounded border border-yellow-200">
                    <p className="mb-2 font-semibold text-yellow-800">⚠️ Important: Add this exact Redirect URI in your LinkedIn app:</p>
                    <code className="bg-white px-3 py-2 rounded text-xs block border border-yellow-300 font-mono break-all">
                      http://localhost:8001/api/integrations/oauth/callback/linkedin
                    </code>
                    <p className="mt-2 text-yellow-700">
                      Go to your LinkedIn app → Auth tab → Add this exact URL (case-sensitive, no trailing slash)
                    </p>
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setShowLinkedInDialog(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleLinkedInSubmit}
                    className="bg-gradient-to-r from-purple-500 to-pink-500"
                  >
                    Connect
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {/* YouTube OAuth Credentials Dialog */}
            <Dialog open={showYouTubeDialog} onOpenChange={setShowYouTubeDialog}>
              <DialogContent 
                className="rounded-2xl border"
                style={{ 
                  backgroundColor: isImmersive ? 'rgba(10, 15, 30, 0.98)' : '#ffffff',
                  borderColor: isImmersive ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0',
                }}
              >
                <DialogHeader>
                  <DialogTitle>YouTube OAuth Setup</DialogTitle>
                  <DialogDescription>
                    Enter your Google OAuth credentials to connect your YouTube account.
                    <br />
                    <a 
                      href="https://console.cloud.google.com/apis/credentials" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-purple-600 hover:underline mt-2 inline-block"
                    >
                      Create OAuth credentials here →
                    </a>
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Client ID
                    </label>
                    <Input
                      type="text"
                      placeholder="Enter your Google OAuth Client ID"
                      value={youtubeCredentials.client_id}
                      onChange={(e) => setYoutubeCredentials({ ...youtubeCredentials, client_id: e.target.value })}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Client Secret
                    </label>
                    <Input
                      type="password"
                      placeholder="Enter your Google OAuth Client Secret"
                      value={youtubeCredentials.client_secret}
                      onChange={(e) => setYoutubeCredentials({ ...youtubeCredentials, client_secret: e.target.value })}
                      className="w-full"
                    />
                  </div>
                  <div className="text-xs text-gray-500 bg-yellow-50 p-3 rounded border border-yellow-200">
                    <p className="mb-2 font-semibold text-yellow-800">⚠️ Important: Add this exact Redirect URI in your Google OAuth app:</p>
                    <code className="bg-white px-3 py-2 rounded text-xs block border border-yellow-300 font-mono break-all">
                      http://localhost:8001/api/integrations/oauth/callback/youtube
                    </code>
                    <p className="mt-2 text-yellow-700">
                      Go to Google Cloud Console → APIs & Services → Credentials → Your OAuth 2.0 Client → Authorized redirect URIs → Add this exact URL
                    </p>
                    <p className="mt-2 text-yellow-700">
                      Also enable "YouTube Data API v3" in the API Library.
                    </p>
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setShowYouTubeDialog(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleYouTubeSubmit}
                    className="bg-gradient-to-r from-purple-500 to-pink-500"
                  >
                    Connect
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {/* Info Card */}
            <Card className="glass-morphism p-8" data-testid="info-card">
              <h3 className="text-xl font-bold text-gray-800 mb-3">How It Works</h3>
              <ul className="space-y-2 text-gray-600">
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span>Your AI agent collects data from connected platforms to understand you better</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span>All data is stored in your personal knowledge graph (Graph RAG)</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span>The more platforms you connect, the smarter your AI agent becomes</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span>Your agent uses this data to have meaningful conversations with potential matches</span>
                </li>
              </ul>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default IntegrationsPage;
