import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  Sparkles, TrendingUp, Heart, Brain, Star, 
  Music, Camera, Code, Book, Gamepad2,
  RefreshCw, Eye, BarChart3, Users, Pencil, Trash2, Plus, X, Check
} from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useWorldMode } from "@/contexts/WorldModeContext";
import MemoryOrb from "@/components/MemoryOrb";

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

// Relationship type options
const RELATIONSHIP_TYPES = [
  "friend", "daughter", "son", "wife", "husband", "mother", "father",
  "brother", "sister", "cousin", "nephew", "niece", "colleague", "boss",
  "mentor", "partner", "other"
];

const AvatarVisualization = ({ user, hideHeader = false }) => {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const { worldMode } = useWorldMode();
  const isAvatarWorld = worldMode === 'avatar';
  
  // Edit states
  const [editingItem, setEditingItem] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [editRelationship, setEditRelationship] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [newItemName, setNewItemName] = useState("");
  const [newItemRelationship, setNewItemRelationship] = useState("friend");
  const [newItemStrength, setNewItemStrength] = useState(0.7);

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
    fetchGraphData();
  }, []);

  // Listen for sync completion events to refresh data
  useEffect(() => {
    const handleSyncComplete = () => {
      console.log("Sync completed, refreshing graph data...");
      fetchGraphData();
    };

    window.addEventListener('youtube-sync-complete', handleSyncComplete);
    window.addEventListener('linkedin-sync-complete', handleSyncComplete);
    
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

  // ===========================================
  // CRUD OPERATIONS
  // ===========================================

  const handleAddItem = async (type) => {
    if (!newItemName.trim()) {
      toast.error("Please enter a name");
      return;
    }

    try {
      const endpoint = type === "connections" ? "/graph/connections" : 
                       type === "interests" ? "/graph/interests" : "/graph/traits";
      
      const payload = type === "connections" 
        ? { name: newItemName, relationship: newItemRelationship }
        : { label: newItemName, strength: newItemStrength };

      await axios.post(`${API}${endpoint}`, payload, { withCredentials: true });
      toast.success(`${type.slice(0, -1)} added successfully`);
      setShowAddForm(false);
      setNewItemName("");
      setNewItemRelationship("friend");
      setNewItemStrength(0.7);
      fetchGraphData();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to add ${type.slice(0, -1)}`);
    }
  };

  const handleEditItem = async (type, item) => {
    try {
      const endpoint = type === "connections" ? `/graph/connections/${item.id}` :
                       type === "interests" ? `/graph/interests/${item.id}` : `/graph/traits/${item.id}`;
      
      const payload = type === "connections"
        ? { name: editValue, relationship: editRelationship }
        : { label: editValue };

      await axios.put(`${API}${endpoint}`, payload, { withCredentials: true });
      toast.success(`${type.slice(0, -1)} updated successfully`);
      setEditingItem(null);
      setEditValue("");
      setEditRelationship("");
      fetchGraphData();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to update ${type.slice(0, -1)}`);
    }
  };

  const handleDeleteItem = async (type, item) => {
    if (!window.confirm(`Are you sure you want to delete "${item.name || item.label}"?`)) {
      return;
    }

    try {
      const endpoint = type === "connections" ? `/graph/connections/${item.id}` :
                       type === "interests" ? `/graph/interests/${item.id}` : `/graph/traits/${item.id}`;

      await axios.delete(`${API}${endpoint}`, { withCredentials: true });
      toast.success(`${type.slice(0, -1)} deleted successfully`);
      fetchGraphData();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to delete ${type.slice(0, -1)}`);
    }
  };

  const startEdit = (item, type) => {
    setEditingItem({ ...item, type });
    setEditValue(item.name || item.label);
    setEditRelationship(item.relationship || "friend");
  };

  const cancelEdit = () => {
    setEditingItem(null);
    setEditValue("");
    setEditRelationship("");
  };

  // ===========================================
  // RENDER HELPERS
  // ===========================================

  const renderAddForm = (type) => {
    if (!showAddForm) return null;

    return (
      <div className={`${isAvatarWorld ? 'bg-yellow-100' : 'bg-white'} rounded-lg p-4 mb-4 border-2 ${isAvatarWorld ? 'border-yellow-400' : 'border-purple-200'}`}>
        <div className="flex flex-col gap-3">
          <Input
            placeholder={type === "connections" ? "Person's name" : `${type.slice(0, -1)} name`}
            value={newItemName}
            onChange={(e) => setNewItemName(e.target.value)}
            className={isAvatarWorld ? 'border-yellow-400' : ''}
          />
          
          {type === "connections" && (
            <select
              value={newItemRelationship}
              onChange={(e) => setNewItemRelationship(e.target.value)}
              className={`w-full p-2 rounded-md border ${isAvatarWorld ? 'border-yellow-400 bg-yellow-50' : 'border-gray-300'}`}
            >
              {RELATIONSHIP_TYPES.map(rel => (
                <option key={rel} value={rel}>{rel.charAt(0).toUpperCase() + rel.slice(1)}</option>
              ))}
            </select>
          )}
          
          {type !== "connections" && (
            <div className="flex items-center gap-2">
              <span className="text-sm">Strength:</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={newItemStrength}
                onChange={(e) => setNewItemStrength(parseFloat(e.target.value))}
                className="flex-1"
              />
              <span className="text-sm w-8">{newItemStrength.toFixed(1)}</span>
            </div>
          )}
          
          <div className="flex gap-2">
            <Button
              onClick={() => handleAddItem(type)}
              className={isAvatarWorld ? 'bg-yellow-500 hover:bg-yellow-600 text-slate-900' : 'bg-purple-500 hover:bg-purple-600'}
            >
              <Check className="w-4 h-4 mr-1" /> Add
            </Button>
            <Button
              variant="outline"
              onClick={() => { setShowAddForm(false); setNewItemName(""); }}
              className={isAvatarWorld ? 'border-yellow-400' : ''}
            >
              <X className="w-4 h-4 mr-1" /> Cancel
            </Button>
          </div>
        </div>
      </div>
    );
  };

  const renderEditableItem = (item, type, icon = null) => {
    const isEditing = editingItem?.id === item.id && editingItem?.type === type;
    const Icon = icon || Star;
    const isEditable = item.editable !== false;

    if (isEditing) {
      return (
        <div className={`${isAvatarWorld ? 'bg-yellow-100' : 'bg-white'} rounded-lg p-4 border-2 ${isAvatarWorld ? 'border-yellow-500' : 'border-purple-400'}`}>
          <div className="flex flex-col gap-2">
            <Input
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className={isAvatarWorld ? 'border-yellow-400' : ''}
            />
            {type === "connections" && (
              <select
                value={editRelationship}
                onChange={(e) => setEditRelationship(e.target.value)}
                className={`w-full p-2 rounded-md border ${isAvatarWorld ? 'border-yellow-400 bg-yellow-50' : 'border-gray-300'}`}
              >
                {RELATIONSHIP_TYPES.map(rel => (
                  <option key={rel} value={rel}>{rel.charAt(0).toUpperCase() + rel.slice(1)}</option>
                ))}
              </select>
            )}
            <div className="flex gap-2">
              <Button size="sm" onClick={() => handleEditItem(type, item)} className={isAvatarWorld ? 'bg-yellow-500 text-slate-900' : 'bg-purple-500'}>
                <Check className="w-3 h-3" />
              </Button>
              <Button size="sm" variant="outline" onClick={cancelEdit}>
                <X className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className={`${isAvatarWorld ? 'bg-yellow-50' : 'bg-white/50'} rounded-lg p-4 ${isAvatarWorld ? 'border-2 border-yellow-400' : 'border-2 border-purple-200'} group`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2 flex-1 min-w-0">
            <Icon className={`w-5 h-5 flex-shrink-0 ${isAvatarWorld ? 'text-yellow-600' : 'text-purple-600'}`} />
            <span className={`font-semibold capitalize truncate ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>
              {item.name || item.label}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {type === "connections" && item.relationship && (
              <Badge className={`text-xs ${isAvatarWorld ? 'bg-yellow-400 text-slate-900' : 'bg-purple-100 text-purple-700'}`}>
                {item.relationship}
              </Badge>
            )}
            {(item.strength !== undefined || item.mentioned_count) && (
              <Badge className={`text-xs ${isAvatarWorld ? 'bg-yellow-400 text-slate-900' : 'bg-purple-100 text-purple-700'}`}>
                {item.strength?.toFixed(1) || item.mentioned_count || "1"}
              </Badge>
            )}
            {isEditable && (
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button size="sm" variant="ghost" onClick={() => startEdit(item, type)} className="h-6 w-6 p-0">
                  <Pencil className="w-3 h-3" />
                </Button>
                <Button size="sm" variant="ghost" onClick={() => handleDeleteItem(type, item)} className="h-6 w-6 p-0 text-red-500 hover:text-red-700">
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            )}
          </div>
        </div>
        {type !== "connections" && item.strength !== undefined && (
          <div className={`w-full ${isAvatarWorld ? 'bg-yellow-100' : 'bg-gray-200'} rounded-full h-2`}>
            <div
              className={`${isAvatarWorld ? 'bg-gradient-to-r from-yellow-500 to-yellow-600' : 'bg-gradient-to-r from-purple-500 to-pink-500'} h-2 rounded-full`}
              style={{ width: `${Math.min((item.strength / 10) * 100, 100)}%` }}
            ></div>
          </div>
        )}
        <p className={`text-xs mt-2 ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-500'}`}>
          Source: {item.source || item.properties?.source || "profile"}
          {item.properties?.service && ` • ${item.properties.service.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`}
        </p>
      </div>
    );
  };

  if (loading) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${isAvatarWorld ? 'bg-gradient-to-br from-pink-500 via-purple-600 to-indigo-700' : 'bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50'}`}>
        <div className="text-center">
          <div className={`w-16 h-16 border-4 ${isAvatarWorld ? 'border-yellow-400' : 'border-purple-400'} border-t-transparent rounded-full animate-spin mx-auto mb-4`}></div>
          <p className={isAvatarWorld ? 'text-blue-100 font-semibold' : 'text-gray-600'}>Loading avatar visualization...</p>
        </div>
      </div>
    );
  }

  if (!graphData) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${isAvatarWorld ? 'bg-gradient-to-br from-pink-500 via-purple-600 to-indigo-700' : 'bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50'}`}>
        <Card className={`${isAvatarWorld ? 'card-avatar' : ''} p-8 text-center`}>
          <p className={isAvatarWorld ? 'text-slate-800 font-semibold mb-4' : 'text-gray-600 mb-4'}>No graph data available</p>
          <Button onClick={fetchGraphData} className={isAvatarWorld ? 'bg-yellow-500 hover:bg-yellow-600 text-slate-900 font-bold' : ''}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </Card>
      </div>
    );
  }

  // Safely destructure with defaults to prevent undefined errors
  const { 
    avatar_info = { name: "Avatar", picture: null, bio: "", archetype: "casual_observer" },
    graph_stats = { total_nodes: 0 },
    top_interests = [],
    top_connections = [],
    top_traits = [],
    top_values = [],
    sources = {}
  } = graphData || {};

  return (
    <div className={hideHeader ? "" : `min-h-screen ${isAvatarWorld ? 'bg-gradient-to-br from-pink-500 via-purple-600 to-indigo-700' : 'bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50'} p-6`}>
      <div className={hideHeader ? "" : "max-w-7xl mx-auto"}>
        {/* Header */}
        {!hideHeader && (
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className={`text-4xl font-bold mb-2 ${isAvatarWorld ? 'text-yellow-200' : 'gradient-text'}`}>
                Avatar Visualization
              </h1>
              <p className={isAvatarWorld ? 'text-blue-100 font-semibold' : 'text-gray-600'}>
                See how your knowledge graph shapes your avatar's personality
              </p>
            </div>
            <Button 
              onClick={fetchGraphData} 
              variant="outline"
              className={isAvatarWorld ? 'border-2 border-yellow-400 text-yellow-200 hover:bg-yellow-500/20 font-semibold' : 'border-2 border-purple-300 text-purple-700 hover:bg-purple-50'}
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
              className={isAvatarWorld ? 'border-2 border-yellow-400 text-yellow-200 hover:bg-yellow-500/20 font-semibold' : 'border-2 border-purple-300 text-purple-700 hover:bg-purple-50'}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh Data
            </Button>
          </div>
        )}

        {/* Avatar Card - responsive layout */}
        <Card className={`${isAvatarWorld ? 'card-avatar' : 'glass-morphism'} p-4 sm:p-6 lg:p-8 mb-4 sm:mb-6 overflow-hidden`}>
          <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4 sm:gap-6">
            <Avatar className={`w-16 h-16 sm:w-20 sm:h-20 lg:w-24 lg:h-24 border-4 flex-shrink-0 ${isAvatarWorld ? 'border-yellow-400 avatar-glow' : 'border-purple-300'}`}>
              <AvatarImage src={avatar_info?.picture || null} alt={avatar_info?.name || "Avatar"} />
              <AvatarFallback className={isAvatarWorld ? 'bg-yellow-500 text-slate-900 font-bold' : ''}>
                {(avatar_info?.name || "Avatar")[0]}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0 text-center sm:text-left">
              <h2 className={`text-xl sm:text-2xl lg:text-3xl font-bold mb-1 sm:mb-2 truncate ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>
                {avatar_info?.name || "Avatar"}
              </h2>
              <p className={`text-sm sm:text-base mb-3 sm:mb-4 line-clamp-2 ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-600'}`}>
                {avatar_info?.bio || "Your digital persona"}
              </p>
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                <Badge className={`text-xs sm:text-sm ${isAvatarWorld ? 'bg-yellow-400 text-slate-900 font-bold' : 'bg-purple-100 text-purple-700'}`}>
                  <Brain className="w-3 h-3 mr-1" />
                  {graph_stats.total_nodes} Nodes
                </Badge>
                <Badge className={`text-xs sm:text-sm ${isAvatarWorld ? 'bg-yellow-400 text-slate-900 font-bold' : 'bg-blue-100 text-blue-700'}`}>
                  <Sparkles className="w-3 h-3 mr-1" />
                  {(avatar_info?.archetype || "casual_observer").replace("_", " ")}
                </Badge>
              </div>
            </div>
          </div>
        </Card>

        {/* Tabs - horizontally scrollable on mobile */}
        <div className="flex gap-2 mb-4 sm:mb-6 overflow-x-auto pb-2 -mx-3 px-3 sm:mx-0 sm:px-0 hide-scrollbar-mobile">
          {[
            { id: "overview", label: "Overview", icon: Eye },
            { id: "interests", label: "Interests", icon: Star },
            { id: "connections", label: "Connections", icon: Users },
            { id: "personality", label: "Personality", icon: Brain },
            { id: "sources", label: "Sources", icon: BarChart3 }
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <Button
                key={tab.id}
                onClick={() => { setActiveTab(tab.id); setShowAddForm(false); setEditingItem(null); }}
                variant={activeTab === tab.id ? "default" : "outline"}
                className={`flex-shrink-0 text-xs sm:text-sm min-h-[44px] px-3 sm:px-4 ${
                  isAvatarWorld
                    ? activeTab === tab.id
                      ? "bg-yellow-500 hover:bg-yellow-600 text-slate-900 font-bold"
                      : "border-2 border-yellow-400 text-yellow-200 hover:bg-yellow-500/20 font-semibold"
                    : activeTab === tab.id
                    ? "bg-purple-500"
                    : ""
                }`}
              >
                <Icon className="w-4 h-4 mr-1 sm:mr-2" />
                {tab.label}
              </Button>
            );
          })}
        </div>

        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Memory Orb */}
            {user && (
              <div className="flex justify-center items-center w-full">
                <div className="w-full max-w-4xl">
                  <MemoryOrb user={user} hideHeader={true} />
                </div>
              </div>
            )}
            
            {/* Stats Cards */}
            <div className="grid md:grid-cols-4 gap-6">
              <Card className={isAvatarWorld ? 'card-avatar p-6' : 'glass-morphism p-6'}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className={`text-lg font-bold ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>Interests</h3>
                  <Star className={`w-5 h-5 ${isAvatarWorld ? 'text-yellow-600' : 'text-yellow-500'}`} />
                </div>
                <div className={`text-4xl font-bold mb-2 ${isAvatarWorld ? 'text-yellow-600' : 'text-purple-600'}`}>
                  {graph_stats.interests_count}
                </div>
                <p className={`text-sm ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-600'}`}>
                  Unique interests discovered
                </p>
              </Card>

              <Card className={isAvatarWorld ? 'card-avatar p-6' : 'glass-morphism p-6'}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className={`text-lg font-bold ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>Connections</h3>
                  <Users className={`w-5 h-5 ${isAvatarWorld ? 'text-green-600' : 'text-green-500'}`} />
                </div>
                <div className={`text-4xl font-bold mb-2 ${isAvatarWorld ? 'text-yellow-600' : 'text-purple-600'}`}>
                  {graph_stats.connections_count || top_connections.length}
                </div>
                <p className={`text-sm ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-600'}`}>
                  People in your network
                </p>
              </Card>

              <Card className={isAvatarWorld ? 'card-avatar p-6' : 'glass-morphism p-6'}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className={`text-lg font-bold ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>Traits</h3>
                  <Heart className={`w-5 h-5 ${isAvatarWorld ? 'text-pink-600' : 'text-pink-500'}`} />
                </div>
                <div className={`text-4xl font-bold mb-2 ${isAvatarWorld ? 'text-yellow-600' : 'text-purple-600'}`}>
                  {graph_stats.traits_count}
                </div>
                <p className={`text-sm ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-600'}`}>
                  Personality traits identified
                </p>
              </Card>

              <Card className={isAvatarWorld ? 'card-avatar p-6' : 'glass-morphism p-6'}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className={`text-lg font-bold ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>Values</h3>
                  <Sparkles className={`w-5 h-5 ${isAvatarWorld ? 'text-blue-600' : 'text-blue-500'}`} />
                </div>
                <div className={`text-4xl font-bold mb-2 ${isAvatarWorld ? 'text-yellow-600' : 'text-purple-600'}`}>
                  {graph_stats.values_count}
                </div>
                <p className={`text-sm ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-600'}`}>
                  Core values extracted
                </p>
              </Card>
            </div>

            {/* Personality Profile Card */}
            <Card className={`${isAvatarWorld ? 'card-avatar' : 'glass-morphism'} p-6`}>
              <h3 className={`text-lg font-bold mb-4 ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>
                Personality Profile
              </h3>
              <div className={`${isAvatarWorld ? 'bg-yellow-50' : 'bg-white/50'} rounded-lg p-4 text-sm ${isAvatarWorld ? 'text-slate-800 font-semibold' : 'text-gray-700'} whitespace-pre-wrap`}>
                {graphData.personality_profile}
              </div>
            </Card>
          </div>
        )}

        {/* Interests Tab */}
        {activeTab === "interests" && (
          <Card className={isAvatarWorld ? 'card-avatar p-6' : 'glass-morphism p-6'}>
            <div className="flex items-center justify-between mb-4">
              <h3 className={`text-xl font-bold ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>
                Your Interests
              </h3>
              <Button
                onClick={() => setShowAddForm(!showAddForm)}
                className={isAvatarWorld ? 'bg-yellow-500 hover:bg-yellow-600 text-slate-900' : 'bg-purple-500 hover:bg-purple-600'}
              >
                <Plus className="w-4 h-4 mr-1" /> Add Interest
              </Button>
            </div>
            
            {renderAddForm("interests")}
            
            <div className="grid md:grid-cols-3 gap-4">
              {top_interests.map((interest, idx) => {
                const Icon = getInterestIcon(interest);
                return (
                  <div key={interest.id || idx}>
                    {renderEditableItem({ ...interest, id: interest.id || `interest_${idx}` }, "interests", Icon)}
                  </div>
                );
              })}
            </div>
            
            {top_interests.length === 0 && (
              <p className={`text-center py-8 ${isAvatarWorld ? 'text-slate-700' : 'text-gray-500'}`}>
                No interests yet. Add some or have a conversation to discover them!
              </p>
            )}
          </Card>
        )}

        {/* Connections Tab */}
        {activeTab === "connections" && (
          <Card className={isAvatarWorld ? 'card-avatar p-6' : 'glass-morphism p-6'}>
            <div className="flex items-center justify-between mb-4">
              <h3 className={`text-xl font-bold ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>
                Your Connections
              </h3>
              <Button
                onClick={() => setShowAddForm(!showAddForm)}
                className={isAvatarWorld ? 'bg-yellow-500 hover:bg-yellow-600 text-slate-900' : 'bg-purple-500 hover:bg-purple-600'}
              >
                <Plus className="w-4 h-4 mr-1" /> Add Connection
              </Button>
            </div>
            
            {renderAddForm("connections")}
            
            <div className="grid md:grid-cols-3 gap-4">
              {top_connections.map((connection, idx) => (
                <div key={connection.id || idx}>
                  {renderEditableItem(connection, "connections", Users)}
                </div>
              ))}
            </div>
            
            {top_connections.length === 0 && (
              <p className={`text-center py-8 ${isAvatarWorld ? 'text-slate-700' : 'text-gray-500'}`}>
                No connections yet. Add friends, mention family in conversations, or connect social accounts!
              </p>
            )}
            
            {/* Legend */}
            <div className={`mt-6 p-4 rounded-lg ${isAvatarWorld ? 'bg-yellow-50' : 'bg-gray-50'}`}>
              <h4 className={`text-sm font-semibold mb-2 ${isAvatarWorld ? 'text-slate-700' : 'text-gray-700'}`}>Source Legend:</h4>
              <div className="flex flex-wrap gap-3 text-xs">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500"></span> Voice Conversation</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span> App Friend</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500"></span> From Posts</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500"></span> Manually Added</span>
              </div>
            </div>
          </Card>
        )}

        {/* Personality Tab */}
        {activeTab === "personality" && (
          <div className="grid md:grid-cols-2 gap-6">
            <Card className={isAvatarWorld ? 'card-avatar p-6' : 'glass-morphism p-6'}>
              <div className="flex items-center justify-between mb-4">
                <h3 className={`text-xl font-bold flex items-center ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>
                  <Heart className={`w-5 h-5 mr-2 ${isAvatarWorld ? 'text-pink-600' : 'text-pink-500'}`} />
                  Personality Traits
                </h3>
                <Button
                  size="sm"
                  onClick={() => setShowAddForm(!showAddForm)}
                  className={isAvatarWorld ? 'bg-yellow-500 hover:bg-yellow-600 text-slate-900' : 'bg-purple-500'}
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              
              {showAddForm && activeTab === "personality" && renderAddForm("traits")}
              
              <div className="space-y-3">
                {top_traits.map((trait, idx) => (
                  <div key={trait.id || idx}>
                    {renderEditableItem({ ...trait, id: trait.id || `trait_${idx}` }, "traits", Heart)}
                  </div>
                ))}
              </div>
            </Card>

            <Card className={isAvatarWorld ? 'card-avatar p-6' : 'glass-morphism p-6'}>
              <h3 className={`text-xl font-bold mb-4 flex items-center ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>
                <Sparkles className={`w-5 h-5 mr-2 ${isAvatarWorld ? 'text-blue-600' : 'text-blue-500'}`} />
                Core Values
              </h3>
              <div className="space-y-3">
                {top_values.map((value, idx) => (
                  <div key={idx} className={`flex items-center justify-between ${isAvatarWorld ? 'bg-yellow-50' : 'bg-white/50'} rounded-lg p-3`}>
                    <span className={`font-medium capitalize ${isAvatarWorld ? 'text-slate-800 font-semibold' : 'text-gray-800'}`}>
                      {value.label}
                    </span>
                    <Badge className={isAvatarWorld ? 'bg-yellow-400 text-slate-900 font-bold' : 'bg-blue-100 text-blue-700'}>
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
          <Card className={isAvatarWorld ? 'card-avatar p-6' : 'glass-morphism p-6'}>
            <h3 className={`text-xl font-bold mb-4 flex items-center ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>
              <BarChart3 className={`w-5 h-5 mr-2 ${isAvatarWorld ? 'text-green-600' : 'text-green-500'}`} />
              Data Sources
            </h3>
            <p className={`mb-4 ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-600'}`}>
              Your knowledge graph is built from multiple sources. The more sources you connect, the richer your avatar becomes.
            </p>
            <div className="grid md:grid-cols-3 gap-4">
              {Object.entries(sources).map(([source, count]) => (
                <div
                  key={source}
                  className={`${isAvatarWorld ? 'bg-yellow-50' : 'bg-white/50'} rounded-lg p-4 ${isAvatarWorld ? 'border-2 border-yellow-400' : 'border-2 border-green-200'}`}
                >
                  <div className="flex items-center justify-between">
                    <span className={`font-semibold capitalize ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>
                      {source === "explicit" ? "Profile" : source}
                    </span>
                    <Badge className={isAvatarWorld ? 'bg-yellow-400 text-slate-900 font-bold' : 'bg-green-100 text-green-700'}>
                      {count}
                    </Badge>
                  </div>
                  <p className={`text-xs mt-2 ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-500'}`}>
                    nodes
                  </p>
                </div>
              ))}
            </div>
            {Object.keys(sources).length === 0 && (
              <p className={`text-center py-8 ${isAvatarWorld ? 'text-slate-700 font-semibold' : 'text-gray-500'}`}>
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
