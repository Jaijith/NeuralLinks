import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Sparkles, TrendingUp, Heart, Brain, Star, 
  Music, Camera, Code, Book, Gamepad2,
  RefreshCw, Eye, BarChart3
} from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

const interestIcons = {
  music: Music,
  photography: Camera,
  coding: Code,
  reading: Book,
  gaming: Gamepad2,
  default: Star
};

const AvatarVisualization = ({ user, hideHeader = false }) => {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    fetchGraphData();
  }, []);

  // Listen for sync completion events to refresh data
  useEffect(() => {
    const handleSyncComplete = () => {
      console.log("Sync completed, refreshing graph data...");
      fetchGraphData();
    };

    // Listen for custom event from IntegrationsPage after sync
    window.addEventListener('youtube-sync-complete', handleSyncComplete);
    window.addEventListener('linkedin-sync-complete', handleSyncComplete);
    
    // Also listen for storage events (if sync updates localStorage)
    window.addEventListener('storage', (e) => {
      if (e.key === 'sync-complete') {
        fetchGraphData();
      }
    });

    return () => {
      window.removeEventListener('youtube-sync-complete', handleSyncComplete);
      window.removeEventListener('linkedin-sync-complete', handleSyncComplete);
    };
  }, []);

  const fetchGraphData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/graph/visualization`, {
        withCredentials: true,
      });
      console.log("Graph data received:", response.data);
      setGraphData(response.data);
    } catch (error) {
      console.error("Error fetching graph data:", error);
      toast.error(`Failed to load avatar visualization: ${error.response?.data?.detail || error.message}`);
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  };

  const getInterestIcon = (interest) => {
    const label = interest.label?.toLowerCase() || "";
    if (label.includes("music")) return Music;
    if (label.includes("photo") || label.includes("art")) return Camera;
    if (label.includes("code") || label.includes("programming")) return Code;
    if (label.includes("read") || label.includes("book")) return Book;
    if (label.includes("game")) return Gamepad2;
    return Star;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading avatar visualization...</p>
        </div>
      </div>
    );
  }

  if (!graphData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50">
        <Card className="p-8 text-center">
          <p className="text-gray-600 mb-4">No graph data available</p>
          <Button onClick={fetchGraphData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </Card>
      </div>
    );
  }

  const { avatar_info, graph_stats, top_interests, top_traits, top_values, sources } = graphData;

  return (
    <div className={hideHeader ? "" : "min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50 p-6"}>
      <div className={hideHeader ? "" : "max-w-7xl mx-auto"}>
        {/* Header */}
        {!hideHeader && (
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold gradient-text mb-2">Avatar Visualization</h1>
              <p className="text-gray-600">See how your knowledge graph shapes your avatar's personality</p>
            </div>
            <Button 
              onClick={fetchGraphData} 
              variant="outline"
              className="border-2 border-purple-300 text-purple-700 hover:bg-purple-50"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        )}
        
        {/* Refresh button for when header is hidden */}
        {hideHeader && (
          <div className="mb-4 flex justify-end">
            <Button 
              onClick={fetchGraphData} 
              variant="outline"
              size="sm"
              className="border-2 border-purple-300 text-purple-700 hover:bg-purple-50"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh Data
            </Button>
          </div>
        )}

        {/* Avatar Card */}
        <Card className="glass-morphism p-8 mb-6">
          <div className="flex items-center space-x-6">
            <Avatar className="w-24 h-24 border-4 border-purple-300">
              <AvatarImage src={avatar_info.picture} alt={avatar_info.name} />
              <AvatarFallback>{avatar_info.name[0]}</AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <h2 className="text-3xl font-bold text-gray-800 mb-2">{avatar_info.name}</h2>
              <p className="text-gray-600 mb-4">{avatar_info.bio || "Your digital persona"}</p>
              <div className="flex items-center space-x-4">
                <Badge className="bg-purple-100 text-purple-700">
                  <Brain className="w-3 h-3 mr-1" />
                  {graph_stats.total_nodes} Graph Nodes
                </Badge>
                <Badge className="bg-blue-100 text-blue-700">
                  <Sparkles className="w-3 h-3 mr-1" />
                  {avatar_info.archetype.replace("_", " ")}
                </Badge>
              </div>
            </div>
            <Button onClick={fetchGraphData} variant="outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </Card>

        {/* Tabs */}
        <div className="flex space-x-2 mb-6">
          {[
            { id: "overview", label: "Overview", icon: Eye },
            { id: "interests", label: "Interests", icon: Star },
            { id: "personality", label: "Personality", icon: Brain },
            { id: "sources", label: "Data Sources", icon: BarChart3 }
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <Button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                variant={activeTab === tab.id ? "default" : "outline"}
                className={activeTab === tab.id ? "bg-purple-500" : ""}
              >
                <Icon className="w-4 h-4 mr-2" />
                {tab.label}
              </Button>
            );
          })}
        </div>

        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="grid md:grid-cols-3 gap-6">
            <Card className="glass-morphism p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-gray-800">Interests</h3>
                <Star className="w-5 h-5 text-yellow-500" />
              </div>
              <div className="text-4xl font-bold text-purple-600 mb-2">
                {graph_stats.interests_count}
              </div>
              <p className="text-sm text-gray-600">Unique interests discovered</p>
            </Card>

            <Card className="glass-morphism p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-gray-800">Traits</h3>
                <Heart className="w-5 h-5 text-pink-500" />
              </div>
              <div className="text-4xl font-bold text-purple-600 mb-2">
                {graph_stats.traits_count}
              </div>
              <p className="text-sm text-gray-600">Personality traits identified</p>
            </Card>

            <Card className="glass-morphism p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-gray-800">Values</h3>
                <Sparkles className="w-5 h-5 text-blue-500" />
              </div>
              <div className="text-4xl font-bold text-purple-600 mb-2">
                {graph_stats.values_count}
              </div>
              <p className="text-sm text-gray-600">Core values extracted</p>
            </Card>

            <Card className="glass-morphism p-6 md:col-span-3">
              <h3 className="text-lg font-bold text-gray-800 mb-4">Personality Profile</h3>
              <div className="bg-white/50 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap">
                {graphData.personality_profile}
              </div>
            </Card>
          </div>
        )}

        {/* Interests Tab */}
        {activeTab === "interests" && (
          <Card className="glass-morphism p-6">
            <h3 className="text-xl font-bold text-gray-800 mb-4">Top Interests</h3>
            <div className="grid md:grid-cols-3 gap-4">
              {top_interests.map((interest, idx) => {
                const Icon = getInterestIcon(interest);
                const strength = interest.strength || 1.0;
                const strengthPercent = Math.min((strength / 10) * 100, 100);
                
                return (
                  <div
                    key={idx}
                    className="bg-white/50 rounded-lg p-4 border-2 border-purple-200"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <Icon className="w-5 h-5 text-purple-600" />
                        <span className="font-semibold text-gray-800 capitalize">
                          {interest.label}
                        </span>
                      </div>
                      <Badge className="bg-purple-100 text-purple-700">
                        {strength.toFixed(1)}
                      </Badge>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full"
                        style={{ width: `${strengthPercent}%` }}
                      ></div>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      Source: {interest.properties?.source || "profile"}
                      {interest.properties?.service && ` • ${interest.properties.service.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`}
                    </p>
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {/* Personality Tab */}
        {activeTab === "personality" && (
          <div className="grid md:grid-cols-2 gap-6">
            <Card className="glass-morphism p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
                <Heart className="w-5 h-5 mr-2 text-pink-500" />
                Personality Traits
              </h3>
              <div className="space-y-3">
                {top_traits.map((trait, idx) => (
                  <div key={idx} className="flex items-center justify-between bg-white/50 rounded-lg p-3">
                    <span className="font-medium text-gray-800 capitalize">{trait.label}</span>
                    <Badge className="bg-pink-100 text-pink-700">
                      {trait.strength?.toFixed(1) || "1.0"}
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="glass-morphism p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
                <Sparkles className="w-5 h-5 mr-2 text-blue-500" />
                Core Values
              </h3>
              <div className="space-y-3">
                {top_values.map((value, idx) => (
                  <div key={idx} className="flex items-center justify-between bg-white/50 rounded-lg p-3">
                    <span className="font-medium text-gray-800 capitalize">{value.label}</span>
                    <Badge className="bg-blue-100 text-blue-700">
                      {value.strength?.toFixed(1) || "1.0"}
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        {/* Sources Tab */}
        {activeTab === "sources" && (
          <Card className="glass-morphism p-6">
            <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
              <BarChart3 className="w-5 h-5 mr-2 text-green-500" />
              Data Sources
            </h3>
            <p className="text-gray-600 mb-4">
              Your knowledge graph is built from multiple sources. The more sources you connect, the richer your avatar becomes.
            </p>
            <div className="grid md:grid-cols-3 gap-4">
              {Object.entries(sources).map(([source, count]) => (
                <div
                  key={source}
                  className="bg-white/50 rounded-lg p-4 border-2 border-green-200"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-800 capitalize">
                      {source === "explicit" ? "Profile" : source}
                    </span>
                    <Badge className="bg-green-100 text-green-700">{count}</Badge>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">nodes</p>
                </div>
              ))}
            </div>
            {Object.keys(sources).length === 0 && (
              <p className="text-gray-500 text-center py-8">
                No data sources yet. Connect social media accounts to start building your graph!
              </p>
            )}
          </Card>
        )}
      </div>
    </div>
  );
};

export default AvatarVisualization;

