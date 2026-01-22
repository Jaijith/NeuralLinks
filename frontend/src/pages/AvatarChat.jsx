import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ArrowLeft, Send, Sparkles, Bot, Lightbulb } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";
import { ImmersivePageWrapper } from "@/components/ambient";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AvatarChat = ({ user }) => {
  const { userId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { worldMode } = useWorldMode();
  const [otherUser, setOtherUser] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [conversationStarters, setConversationStarters] = useState([]);
  const [showStarters, setShowStarters] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchUserAndStarters();
  }, [userId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchUserAndStarters = async () => {
    try {
      // Fetch other user's profile
      const userResponse = await axios.get(`${API}/users/${userId}?world_mode=${worldMode}`, {
        withCredentials: true,
      });
      setOtherUser(userResponse.data);

      // Fetch AI-generated conversation starters
      try {
        const startersResponse = await axios.get(`${API}/avatar/conversation-starters/${userId}`, {
          withCredentials: true,
        });
        setConversationStarters(startersResponse.data.starters || []);
      } catch (error) {
        console.error("Error fetching conversation starters:", error);
      }
    } catch (error) {
      console.error("Error fetching user data:", error);
      toast.error("Failed to load user profile");
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (messageText = null) => {
    const textToSend = messageText || input;
    if (!textToSend.trim()) return;

    setInput("");
    setSending(true);
    setShowStarters(false);

    // Add user's message immediately
    const userMessage = {
      sender_id: user.id,
      content: textToSend,
      timestamp: new Date().toISOString(),
      is_ai: false
    };
    
    setMessages((prev) => [...prev, userMessage]);

    try {
      // Get AI avatar response
      const response = await axios.post(
        `${API}/avatar/chat-response`,
        {
          other_user_id: userId,
          conversation_history: messages,
          last_message: textToSend,
        },
        { withCredentials: true }
      );

      // Add AI response
      const aiMessage = {
        sender_id: userId,
        content: response.data.content,
        timestamp: new Date().toISOString(),
        is_ai: true
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error("Error getting AI response:", error);
      toast.error("Failed to get response");
      
      // Add fallback response
      const fallbackMessage = {
        sender_id: userId,
        content: "I'm having trouble responding right now. Let's try again!",
        timestamp: new Date().toISOString(),
        is_ai: true
      };
      setMessages((prev) => [...prev, fallbackMessage]);
    } finally {
      setSending(false);
    }
  };

  const useStarter = (starter) => {
    setInput(starter);
    setShowStarters(false);
  };

  if (loading) {
    return (
      <ImmersivePageWrapper pageId="avatar-chat" showToggle={false} user={user}>
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600">Loading conversation...</p>
          </div>
        </div>
      </ImmersivePageWrapper>
    );
  }

  if (!otherUser) return null;

  const displayName = worldMode === 'Maya' ? otherUser.avatar_name || otherUser.name : otherUser.name;
  const displayPicture = worldMode === 'Maya' ? otherUser.avatar_picture || otherUser.picture : otherUser.picture;

  return (
    <ImmersivePageWrapper pageId="avatar-chat" user={user}>
      <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white/70 backdrop-blur-md border-b border-purple-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              onClick={() => navigate(-1)}
              className="hover:bg-purple-50"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <Avatar className="w-10 h-10 border-2 border-white shadow-md">
              <AvatarImage src={displayPicture} />
              <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white">
                {displayName?.charAt(0) || "?"}
              </AvatarFallback>
            </Avatar>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="font-bold text-gray-800">{displayName}</h2>
                {worldMode === 'Maya' && (
                  <span className="px-2 py-0.5 bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs rounded-full flex items-center">
                    <Bot className="w-3 h-3 mr-1" />
                    AI Avatar
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600">
                {worldMode === 'Maya' ? 'AI-powered conversation' : 'Chat'}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 max-w-4xl w-full mx-auto px-6 py-8 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-20 h-20 bg-gradient-to-br from-purple-200 to-pink-300 rounded-full flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-10 h-10 text-purple-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-800 mb-2">Start a conversation!</h3>
            <p className="text-gray-600 mb-6">
              {worldMode === 'Maya' 
                ? `Chat with ${displayName}'s AI avatar` 
                : `Say hello to ${displayName}`}
            </p>

            {/* Conversation Starters */}
            {showStarters && conversationStarters.length > 0 && (
              <Card className="glass-morphism p-6 max-w-md mx-auto">
                <div className="flex items-center space-x-2 mb-4">
                  <Lightbulb className="w-5 h-5 text-purple-600" />
                  <h4 className="font-semibold text-gray-800">Conversation Starters</h4>
                </div>
                <div className="space-y-2">
                  {conversationStarters.map((starter, idx) => (
                    <Button
                      key={idx}
                      variant="outline"
                      onClick={() => sendMessage(starter)}
                      className="w-full text-left justify-start hover:bg-purple-50 border-purple-200"
                    >
                      {starter}
                    </Button>
                  ))}
                </div>
              </Card>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${
                  msg.sender_id === user.id ? "justify-end" : "justify-start"
                } fade-in`}
              >
                <div
                  className={`flex items-end space-x-2 max-w-md ${
                    msg.sender_id === user.id ? "flex-row-reverse space-x-reverse" : ""
                  }`}
                >
                  <Avatar className="w-8 h-8 flex-shrink-0">
                    <AvatarImage
                      src={msg.sender_id === user.id ? user.picture : displayPicture}
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
                        : displayName?.charAt(0)}
                    </AvatarFallback>
                  </Avatar>
                  <div
                    className={`px-4 py-3 rounded-2xl ${
                      msg.sender_id === user.id
                        ? "bg-gradient-to-r from-pink-500 to-purple-600 text-white"
                        : "bg-white border border-purple-100"
                    }`}
                  >
                    {msg.is_ai && msg.sender_id !== user.id && (
                      <div className="flex items-center space-x-1 mb-1">
                        <Bot className="w-3 h-3 text-purple-500" />
                        <span className="text-xs text-purple-500">AI Response</span>
                      </div>
                    )}
                    <p className={msg.sender_id === user.id ? "text-white" : "text-gray-800"}>
                      {msg.content}
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
      <div className="bg-white/70 backdrop-blur-md border-t border-purple-100 sticky bottom-0">
        <div className="max-w-4xl mx-auto px-6 py-4 flex space-x-3">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && !sending && sendMessage()}
            placeholder={`Message ${displayName}...`}
            disabled={sending}
            className="flex-1 border-2 border-purple-200 focus:border-purple-400 rounded-xl px-4 py-3"
          />
          <Button
            onClick={() => sendMessage()}
            disabled={sending || !input.trim()}
            className="btn-primary text-white px-6 py-3 rounded-xl"
          >
            {sending ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </Button>
        </div>
      </div>
      </div>
    </ImmersivePageWrapper>
  );
};

export default AvatarChat;
