import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, CheckCircle, XCircle, RefreshCw, Facebook, Instagram, Twitter, Linkedin, Mail, MessageSquare, ShoppingCart, Heart } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const platformIcons = {
  Facebook: Facebook,
  Instagram: Instagram,
  Twitter: Twitter,
  LinkedIn: Linkedin,
  TikTok: Heart,
  Snapchat: MessageSquare,
  Gmail: Mail,
  Outlook: Mail,
  'Yahoo Mail': Mail,
  ProtonMail: Mail,
  WhatsApp: MessageSquare,
  Telegram: MessageSquare,
  Signal: MessageSquare,
  Messenger: MessageSquare,
  Amazon: ShoppingCart,
  Etsy: ShoppingCart,
  eBay: ShoppingCart,
  Shopify: ShoppingCart,
  Tinder: Heart,
  Bumble: Heart,
  Hinge: Heart,
  OKCupid: Heart,
};

const platformColors = {
  Facebook: 'from-blue-500 to-blue-600',
  Instagram: 'from-pink-500 via-purple-500 to-orange-500',
  Twitter: 'from-blue-400 to-blue-500',
  LinkedIn: 'from-blue-600 to-blue-700',
  TikTok: 'from-black to-gray-800',
  Snapchat: 'from-yellow-400 to-yellow-500',
  Gmail: 'from-red-500 to-red-600',
  Outlook: 'from-blue-500 to-blue-600',
  'Yahoo Mail': 'from-purple-600 to-purple-700',
  ProtonMail: 'from-purple-700 to-purple-800',
  WhatsApp: 'from-green-500 to-green-600',
  Telegram: 'from-blue-400 to-blue-500',
  Signal: 'from-blue-600 to-blue-700',
  Messenger: 'from-blue-500 via-purple-500 to-pink-500',
  Amazon: 'from-orange-400 to-orange-500',
  Etsy: 'from-orange-500 to-orange-600',
  eBay: 'from-red-600 to-yellow-500',
  Shopify: 'from-green-600 to-green-700',
  Tinder: 'from-pink-500 to-red-500',
  Bumble: 'from-yellow-400 to-orange-500',
  Hinge: 'from-purple-500 to-purple-600',
  OKCupid: 'from-blue-500 to-teal-500',
};

const IntegrationsPage = ({ user }) => {
  const navigate = useNavigate();
  const [integrations, setIntegrations] = useState({
    social_media: [],
    ecommerce: [],
    email: [],
    messaging: [],
    dating: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const fetchIntegrations = async () => {
    try {
      const response = await axios.get(`${API}/integrations`, {
        withCredentials: true,
      });
      
      // Transform backend response to match UI structure
      const platformData = response.data.integrations || [];
      
      const categorized = {
        social_media: platformData.filter(p => ['spotify', 'youtube', 'instagram', 'facebook'].includes(p.platform_name)),
        ecommerce: platformData.filter(p => ['amazon'].includes(p.platform_name)),
        email: [],
        messaging: [],
        dating: platformData.filter(p => ['strava', 'netflix', 'goodreads'].includes(p.platform_name))
      };
      
      setIntegrations(categorized);
    } catch (error) {
      console.error("Error fetching integrations:", error);
      toast.error("Failed to load integrations");
    } finally {
      setLoading(false);
    }
  };

  const PlatformCard = ({ platform }) => {
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
    if (platforms.length === 0) return null;
    
    return (
      <div className="mb-12">
        <div className="flex items-center space-x-3 mb-6">
          <div className={`w-10 h-10 bg-gradient-to-br ${color} rounded-xl flex items-center justify-center`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-800">{title}</h2>
            <p className="text-sm text-gray-600">{platforms.length} connected</p>
          </div>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {platforms.map((platform, idx) => (
            <PlatformCard key={idx} platform={platform} />
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center space-x-4 mb-8">
          <Button
            variant="ghost"
            onClick={() => navigate("/dashboard")}
            data-testid="back-btn"
            className="hover:bg-purple-50"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-4xl font-bold gradient-text">Connected Platforms</h1>
            <p className="text-gray-600">Your AI agent learns from all your connected accounts</p>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600">Loading integrations...</p>
          </div>
        ) : (
          <div>
            <IntegrationSection
              title="Social Media"
              platforms={integrations.social_media}
              icon={Facebook}
              color="from-blue-500 to-purple-600"
            />
            <IntegrationSection
              title="E-commerce"
              platforms={integrations.ecommerce}
              icon={ShoppingCart}
              color="from-orange-500 to-red-600"
            />
            <IntegrationSection
              title="Email"
              platforms={integrations.email}
              icon={Mail}
              color="from-green-500 to-teal-600"
            />
            <IntegrationSection
              title="Messaging"
              platforms={integrations.messaging}
              icon={MessageSquare}
              color="from-purple-500 to-pink-600"
            />
            <IntegrationSection
              title="Dating Apps"
              platforms={integrations.dating}
              icon={Heart}
              color="from-pink-500 to-red-600"
            />

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
