import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Heart, MessageCircle, ArrowLeft, Sparkles, TrendingUp, Brain } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Matches = ({ user }) => {
  const navigate = useNavigate();
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [agentConversation, setAgentConversation] = useState(null);

  useEffect(() => {
    fetchMatches();
  }, []);

  const fetchMatches = async () => {
    try {
      const response = await axios.get(`${API}/matches`, {
        withCredentials: true,
      });
      setMatches(response.data);
    } catch (error) {
      console.error("Error fetching matches:", error);
      toast.error("Failed to load matches");
    } finally {
      setLoading(false);
    }
  };

  const viewMatchDetails = async (match) => {
    setSelectedMatch(match);
    try {
      const response = await axios.get(`${API}/matches/${match.id}/conversation`, {
        withCredentials: true,
      });
      setAgentConversation(response.data);
    } catch (error) {
      console.error("Error fetching conversation:", error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50">
      {/* Header */}
      <header className="bg-white/70 backdrop-blur-md border-b border-purple-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center space-x-4">
          <Button
            variant="ghost"
            onClick={() => navigate("/dashboard")}
            data-testid="back-to-dashboard-btn"
            className="hover:bg-purple-50"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <h1 className="text-2xl font-bold gradient-text">Your Matches</h1>
          <Badge className="bg-gradient-to-r from-pink-500 to-purple-600 text-white">
            {matches.length} Matches
          </Badge>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12">
        {loading ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600">Loading your matches...</p>
          </div>
        ) : matches.length === 0 ? (
          <Card className="glass-morphism p-12 text-center" data-testid="no-matches-message">
            <div className="w-24 h-24 bg-gradient-to-br from-purple-200 to-purple-300 rounded-full flex items-center justify-center mx-auto mb-6">
              <Heart className="w-12 h-12 text-purple-600" />
            </div>
            <h3 className="text-2xl font-bold text-gray-800 mb-3">No matches yet</h3>
            <p className="text-gray-600 mb-6">Start discovering to find AI-validated matches</p>
            <Button
              onClick={() => navigate("/dashboard")}
              data-testid="go-discover-btn"
              className="btn-primary text-white px-8 py-3 rounded-full"
            >
              <Sparkles className="w-5 h-5 mr-2" />
              Discover Matches
            </Button>
          </Card>
        ) : (
          <div className="grid lg:grid-cols-2 gap-8">
            {/* Matches List */}
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-800 mb-4">All Matches</h2>
              {matches.map((match, idx) => (
                <Card
                  key={match.id}
                  className={`glass-morphism p-6 card-hover cursor-pointer ${
                    selectedMatch?.id === match.id ? "ring-2 ring-purple-500" : ""
                  }`}
                  onClick={() => viewMatchDetails(match)}
                  data-testid={`match-item-${idx}`}
                >
                  <div className="flex items-start space-x-4">
                    <Avatar className="w-16 h-16 border-2 border-white shadow-md">
                      <AvatarImage src={match.matched_user?.picture} />
                      <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-xl">
                        {match.matched_user?.name?.charAt(0) || "?"}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-lg font-bold text-gray-800">
                          {match.matched_user?.name}
                        </h3>
                        <Badge
                          className="bg-gradient-to-r from-pink-500 to-purple-600 text-white"
                          data-testid={`compatibility-badge-${idx}`}
                        >
                          {Math.round(match.compatibility_score)}% Match
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600 mb-3">
                        {match.matched_user?.age} • {match.matched_user?.bio}
                      </p>

                      {/* Compatibility Breakdown */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-gray-600">Overall</span>
                          <span className="font-semibold">{Math.round(match.compatibility_score)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                          <div
                            className="bg-gradient-to-r from-pink-500 to-purple-600 h-1.5 rounded-full"
                            style={{ width: `${match.compatibility_score}%` }}
                          ></div>
                        </div>
                      </div>

                      {match.shared_interests?.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-3">
                          {match.shared_interests.map((interest, i) => (
                            <span
                              key={i}
                              className="bg-purple-100 text-purple-700 text-xs px-2 py-1 rounded-full"
                            >
                              {interest}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* Match Details */}
            <div className="sticky top-24">
              {selectedMatch ? (
                <Card className="glass-morphism p-8" data-testid="match-details-card">
                  <div className="text-center mb-6">
                    <Avatar className="w-24 h-24 border-4 border-white shadow-lg mx-auto mb-4">
                      <AvatarImage src={selectedMatch.matched_user?.picture} />
                      <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-2xl">
                        {selectedMatch.matched_user?.name?.charAt(0) || "?"}
                      </AvatarFallback>
                    </Avatar>
                    <h2 className="text-2xl font-bold text-gray-800 mb-1">
                      {selectedMatch.matched_user?.name}
                    </h2>
                    <p className="text-gray-600">
                      {selectedMatch.matched_user?.age} • {selectedMatch.matched_user?.bio}
                    </p>
                  </div>

                  {/* Compatibility Scores */}
                  <div className="space-y-4 mb-6">
                    <div>
                      <div className="flex items-center justify-between text-sm mb-2">
                        <span className="text-gray-600 flex items-center">
                          <TrendingUp className="w-4 h-4 mr-1" />
                          Overall Compatibility
                        </span>
                        <span className="font-bold gradient-text">
                          {Math.round(selectedMatch.compatibility_score)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className="bg-gradient-to-r from-pink-500 to-purple-600 h-3 rounded-full"
                          style={{ width: `${selectedMatch.compatibility_score}%` }}
                        ></div>
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between text-sm mb-2">
                        <span className="text-gray-600 flex items-center">
                          <Brain className="w-4 h-4 mr-1" />
                          Personality Match
                        </span>
                        <span className="font-bold gradient-text">
                          {Math.round(selectedMatch.personality_compatibility)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className="bg-gradient-to-r from-purple-500 to-indigo-600 h-3 rounded-full"
                          style={{ width: `${selectedMatch.personality_compatibility}%` }}
                        ></div>
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between text-sm mb-2">
                        <span className="text-gray-600 flex items-center">
                          <MessageCircle className="w-4 h-4 mr-1" />
                          Conversation Quality
                        </span>
                        <span className="font-bold gradient-text">
                          {Math.round(selectedMatch.conversation_quality)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className="bg-gradient-to-r from-indigo-500 to-blue-600 h-3 rounded-full"
                          style={{ width: `${selectedMatch.conversation_quality}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>

                  {/* AI Conversation Summary */}
                  {agentConversation && (
                    <div className="bg-purple-50 rounded-2xl p-4 mb-6" data-testid="ai-conversation-summary">
                      <h3 className="font-bold text-gray-800 mb-2 flex items-center">
                        <Sparkles className="w-4 h-4 mr-2 text-purple-600" />
                        AI Conversation Summary
                      </h3>
                      <p className="text-sm text-gray-600">
                        {agentConversation.conversation_summary || agentConversation.summary || "No conversation yet"}
                      </p>
                    </div>
                  )}

                  {/* Shared Interests */}
                  {selectedMatch.shared_interests?.length > 0 && (
                    <div className="mb-6">
                      <h3 className="font-bold text-gray-800 mb-3">Shared Interests</h3>
                      <div className="flex flex-wrap gap-2">
                        {selectedMatch.shared_interests.map((interest, i) => (
                          <span
                            key={i}
                            className="bg-purple-100 text-purple-700 text-sm px-3 py-1.5 rounded-full"
                          >
                            {interest}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <Button
                    onClick={() => navigate(`/chat/${selectedMatch.id}`)}
                    data-testid="start-chat-btn"
                    className="w-full btn-primary text-white py-3 rounded-xl"
                  >
                    <MessageCircle className="w-5 h-5 mr-2" />
                    Start Chatting
                  </Button>
                </Card>
              ) : (
                <Card className="glass-morphism p-12 text-center" data-testid="select-match-message">
                  <div className="w-20 h-20 bg-gradient-to-br from-purple-200 to-purple-300 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Heart className="w-10 h-10 text-purple-600" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-800 mb-2">Select a match</h3>
                  <p className="text-gray-600">Click on a match to see details and compatibility scores</p>
                </Card>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Matches;
