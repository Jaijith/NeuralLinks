import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ArrowLeft, Send, Heart } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Chat = ({ user }) => {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const [match, setMatch] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchMatchAndMessages();
  }, [matchId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchMatchAndMessages = async () => {
    try {
      // Fetch match details
      const matchesResponse = await axios.get(`${API}/matches`, {
        withCredentials: true,
      });
      const foundMatch = matchesResponse.data.find((m) => m.id === matchId);
      if (!foundMatch) {
        toast.error("Match not found");
        navigate("/matches");
        return;
      }
      setMatch(foundMatch);

      // Fetch messages
      const messagesResponse = await axios.get(`${API}/chat/${matchId}/messages`, {
        withCredentials: true,
      });
      setMessages(messagesResponse.data.messages || []);
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Failed to load conversation");
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const messageText = input;
    setInput("");
    setSending(true);

    try {
      const response = await axios.post(
        `${API}/chat/send`,
        {
          match_id: matchId,
          message: messageText,
        },
        { withCredentials: true }
      );

      setMessages((prev) => [...prev, response.data]);
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("Failed to send message");
      setInput(messageText); // Restore message
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading conversation...</p>
        </div>
      </div>
    );
  }

  if (!match) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50 flex flex-col">
      {/* Header */}
      <header className="bg-white/70 backdrop-blur-md border-b border-purple-100 sticky top-0 z-50" data-testid="chat-header">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              onClick={() => navigate("/matches")}
              data-testid="back-to-matches-btn"
              className="hover:bg-purple-50"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <Avatar className="w-10 h-10 border-2 border-white shadow-md">
              <AvatarImage src={match.matched_user?.picture} />
              <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white">
                {match.matched_user?.name?.charAt(0) || "?"}
              </AvatarFallback>
            </Avatar>
            <div>
              <h2 className="font-bold text-gray-800">{match.matched_user?.name}</h2>
              <p className="text-sm text-gray-600">
                {Math.round(match.compatibility_score)}% Match
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            data-testid="match-info-btn"
            className="text-pink-600 hover:bg-pink-50"
          >
            <Heart className="w-5 h-5" />
          </Button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 max-w-4xl w-full mx-auto px-6 py-8 overflow-y-auto" data-testid="messages-container">
        {messages.length === 0 ? (
          <div className="text-center py-20" data-testid="no-messages">
            <div className="w-20 h-20 bg-gradient-to-br from-purple-200 to-purple-300 rounded-full flex items-center justify-center mx-auto mb-4">
              <Heart className="w-10 h-10 text-purple-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-800 mb-2">Start the conversation!</h3>
            <p className="text-gray-600">Say hello to {match.matched_user?.name}</p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${
                  msg.sender_id === user.id ? "justify-end" : "justify-start"
                } fade-in`}
                data-testid={`chat-message-${idx}`}
              >
                <div
                  className={`flex items-end space-x-2 max-w-md ${
                    msg.sender_id === user.id ? "flex-row-reverse space-x-reverse" : ""
                  }`}
                >
                  <Avatar className="w-8 h-8 flex-shrink-0">
                    <AvatarImage
                      src={
                        msg.sender_id === user.id
                          ? user.picture
                          : match.matched_user?.picture
                      }
                    />
                    <AvatarFallback
                      className={`text-white text-sm ${
                        msg.sender_id === user.id
                          ? "bg-gradient-to-br from-indigo-400 to-indigo-600"
                          : "bg-gradient-to-br from-pink-400 to-purple-600"
                      }`}
                    >
                      {msg.sender_id === user.id
                        ? user.name?.charAt(0)
                        : match.matched_user?.name?.charAt(0)}
                    </AvatarFallback>
                  </Avatar>
                  <div
                    className={`px-4 py-3 rounded-2xl ${
                      msg.sender_id === user.id
                        ? "bg-gradient-to-r from-pink-500 to-purple-600 text-white"
                        : "bg-white border border-purple-100"
                    }`}
                  >
                    <p
                      className={msg.sender_id === user.id ? "text-white" : "text-gray-800"}
                    >
                      {msg.message}
                    </p>
                    <p
                      className={`text-xs mt-1 ${
                        msg.sender_id === user.id ? "text-pink-100" : "text-gray-500"
                      }`}
                    >
                      {new Date(msg.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="bg-white/70 backdrop-blur-md border-t border-purple-100 sticky bottom-0" data-testid="chat-input-container">
        <div className="max-w-4xl mx-auto px-6 py-4 flex space-x-3">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && sendMessage()}
            placeholder={`Message ${match.matched_user?.name}...`}
            disabled={sending}
            className="flex-1 border-2 border-purple-200 focus:border-purple-400 rounded-xl px-4 py-3"
            data-testid="chat-input-field"
          />
          <Button
            onClick={sendMessage}
            disabled={sending || !input.trim()}
            data-testid="send-message-btn"
            className="btn-primary text-white px-6 py-3 rounded-xl"
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Chat;
