import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Sparkles, TrendingUp, MessageCircle, Heart, Users } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import AppHeader from "@/components/AppHeader";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);

  useEffect(() => {
    if (!user.profile_completed) {
      navigate("/onboarding");
      return;
    }
    fetchMatches();
  }, [user]);

  const fetchMatches = async () => {
    try {
      const response = await axios.get(`${API}/matches`, {
        withCredentials: true,
      });
      setMatches(response.data);
    } catch (error) {
      console.error("Error fetching matches:", error);
    } finally {
      setLoading(false);
    }
  };

  const discoverMatches = async () => {
    setDiscovering(true);
    try {
      const response = await axios.post(`${API}/matches/discover`, {}, {
        withCredentials: true,
      });
      toast.success(`Found ${response.data.length} new matches!`);
      fetchMatches();
    } catch (error) {
      console.error("Error discovering matches:", error);
      toast.error("Failed to discover matches");
    } finally {
      setDiscovering(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50">
      <AppHeader user={user} setUser={setUser} currentPage="home" />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Welcome Section */}
        <div className="mb-12 fade-in" data-testid="dashboard-welcome">
          <div className="flex items-center space-x-4 mb-4">
            <Avatar className="w-16 h-16 border-4 border-white shadow-lg">
              <AvatarImage src={user.picture} />
              <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-xl">
                {user.name?.charAt(0)}
              </AvatarFallback>
            </Avatar>
            <div>
              <h2 className="text-3xl font-bold text-gray-800">Welcome back, {user.name}!</h2>
              <p className="text-gray-600">Your AI agent is actively finding matches for you</p>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <Card className="glass-morphism p-6 card-hover" data-testid="stat-card-matches">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total Matches</p>
                <p className="text-3xl font-bold gradient-text">{matches.length}</p>
              </div>
              <div className="w-12 h-12 bg-gradient-to-br from-pink-400 to-pink-600 rounded-xl flex items-center justify-center">
                <Heart className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>

          <Card className="glass-morphism p-6 card-hover" data-testid="stat-card-score">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Avg Compatibility</p>
                <p className="text-3xl font-bold gradient-text">
                  {matches.length > 0
                    ? Math.round(
                        matches.reduce((acc, m) => acc + m.compatibility_score, 0) / matches.length
                      )
                    : 0}
                  %
                </p>
              </div>
              <div className="w-12 h-12 bg-gradient-to-br from-purple-400 to-purple-600 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>

          <Card className="glass-morphism p-6 card-hover" data-testid="stat-card-conversations">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Active Chats</p>
                <p className="text-3xl font-bold gradient-text">
                  {matches.filter((m) => m.status === "accepted").length}
                </p>
              </div>
              <div className="w-12 h-12 bg-gradient-to-br from-indigo-400 to-indigo-600 rounded-xl flex items-center justify-center">
                <MessageCircle className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>
        </div>

        {/* Discover Section */}
        <div className="bg-gradient-to-r from-pink-500 to-purple-600 rounded-3xl p-8 mb-12 text-white" data-testid="discover-section">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <div className="mb-6 md:mb-0">
              <h3 className="text-2xl font-bold mb-2 flex items-center">
                <Sparkles className="w-6 h-6 mr-2" />
                Discover New Matches
              </h3>
              <p className="text-pink-100">
                Let your AI agent find compatible matches while you relax
              </p>
            </div>
            <Button
              onClick={discoverMatches}
              disabled={discovering}
              data-testid="discover-matches-btn"
              className="bg-white text-purple-600 hover:bg-purple-50 px-8 py-6 rounded-full font-semibold shadow-lg disabled:opacity-50"
            >
              {discovering ? (
                <>
                  <div className="w-5 h-5 border-2 border-purple-600 border-t-transparent rounded-full animate-spin mr-2"></div>
                  Discovering...
                </>
              ) : (
                <>
                  <Users className="w-5 h-5 mr-2" />
                  Start Discovery
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Recent Matches */}
        <div>
          <h3 className="text-2xl font-bold text-gray-800 mb-6">Recent Matches</h3>
          {loading ? (
            <div className="text-center py-12">
              <div className="w-12 h-12 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-gray-600">Loading matches...</p>
            </div>
          ) : matches.length === 0 ? (
            <Card className="glass-morphism p-12 text-center" data-testid="no-matches-card">
              <div className="w-20 h-20 bg-gradient-to-br from-purple-200 to-purple-300 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="w-10 h-10 text-purple-600" />
              </div>
              <h4 className="text-xl font-bold text-gray-800 mb-2">No matches yet</h4>
              <p className="text-gray-600 mb-6">Start discovering to find your AI-validated matches</p>
              <Button
                onClick={discoverMatches}
                data-testid="no-matches-discover-btn"
                className="btn-primary text-white px-6 py-3 rounded-full"
              >
                <Sparkles className="w-5 h-5 mr-2" />
                Discover Now
              </Button>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {matches.slice(0, 6).map((match, idx) => (
                <Card
                  key={match.id}
                  className="glass-morphism p-6 card-hover cursor-pointer"
                  onClick={() => navigate(`/chat/${match.id}`)}
                  data-testid={`match-card-${idx}`}
                >
                  <div className="flex items-start space-x-4 mb-4">
                    <Avatar className="w-14 h-14 border-2 border-white shadow-md">
                      <AvatarImage src={match.matched_user?.picture} />
                      <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white">
                        {match.matched_user?.name?.charAt(0) || "?"}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <h4 className="font-bold text-gray-800">{match.matched_user?.name}</h4>
                      <p className="text-sm text-gray-600">
                        {match.matched_user?.age} • {match.matched_user?.bio?.slice(0, 30)}...
                      </p>
                    </div>
                  </div>

                  <div className="mb-4">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">Compatibility</span>
                      <span className="font-semibold gradient-text">{Math.round(match.compatibility_score)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-pink-500 to-purple-600 h-2 rounded-full"
                        style={{ width: `${match.compatibility_score}%` }}
                      ></div>
                    </div>
                  </div>

                  {match.shared_interests?.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {match.shared_interests.slice(0, 3).map((interest, i) => (
                        <span
                          key={i}
                          className="bg-purple-100 text-purple-700 text-xs px-3 py-1 rounded-full"
                        >
                          {interest}
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}

          {matches.length > 6 && (
            <div className="text-center mt-8">
              <Button
                onClick={() => navigate("/matches")}
                data-testid="view-all-matches-btn"
                variant="outline"
                className="border-2 border-purple-300 text-purple-700 hover:bg-purple-50 px-6 py-3 rounded-full"
              >
                View All Matches
              </Button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
