import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { X, Send, Minimize2, Maximize2, Bot, Sparkles } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SideMessenger = ({ user, otherUserId, otherUserData, onClose }) => {
  const { worldMode } = useWorldMode();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [otherUser, setOtherUser] = useState(otherUserData || null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (!otherUserData && otherUserId) {
      fetchOtherUser();
    }
  }, [otherUserId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchOtherUser = async () => {
    try {
      const response = await axios.get(`${API}/users/${otherUserId}?world_mode=${worldMode}`, {
        withCredentials: true,
      });
      setOtherUser(response.data);
    } catch (error) {
      console.error("Error fetching user:", error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const messageText = input;
    setInput("");
    setSending(true);

    // Add user's message immediately
    const userMessage = {
      sender_id: user.id,
      content: messageText,
      timestamp: new Date().toISOString(),
    };
    
    setMessages((prev) => [...prev, userMessage]);

    try {
      if (worldMode === 'avatar') {
        // Avatar mode: AI avatar response
        const response = await axios.post(
          `${API}/avatar/chat-response`,
          {
            other_user_id: otherUserId,
            conversation_history: messages,
            last_message: textToSend,
          },
          { withCredentials: true }
        );

        const aiMessage = {
          sender_id: otherUserId,
          content: response.data.content,
          timestamp: new Date().toISOString(),
          is_ai: true
        };

        setMessages((prev) => [...prev, aiMessage]);
      } else {
        // Real mode: Real person-to-person (placeholder for now)
        // In production, this would send actual message to the other user
        const autoReply = {
          sender_id: otherUserId,
          content: "Thanks for your message! (This is a demo auto-reply in Sense mode)",
          timestamp: new Date().toISOString(),
        };
        
        // Simulate delay
        setTimeout(() => {
          setMessages((prev) => [...prev, autoReply]);
        }, 1000);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("Failed to send message");
    } finally {
      setSending(false);
    }
  };

  if (!otherUser) return null;

  const displayName = worldMode === 'avatar' 
    ? (otherUser.avatar_name || otherUser.name) 
    : otherUser.name;
  
  const displayPicture = worldMode === 'avatar' 
    ? (otherUser.avatar_picture || otherUser.picture) 
    : otherUser.picture;

  return (
    <Card className="fixed bottom-4 right-4 w-80 h-[500px] flex flex-col shadow-2xl border-2 border-purple-300 bg-white z-50 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-3 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Avatar className="w-8 h-8 border-2 border-white">
            <AvatarImage src={displayPicture} />
            <AvatarFallback className="bg-white text-purple-600 text-sm">
              {displayName?.charAt(0) || "?"}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <h3 className="font-semibold text-white text-sm">{displayName}</h3>
            <div className="flex items-center space-x-1">
              {worldMode === 'avatar' && (
                <>
                  <Bot className="w-3 h-3 text-white" />
                  <span className="text-xs text-white/90">AI Avatar</span>
                </>
              )}
              {worldMode === 'Sense' && (
                <span className="text-xs text-white/90">Real Person</span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsMinimized(!isMinimized)}
            className="text-white hover:bg-white/20 p-1 h-auto"
          >
            {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-white hover:bg-white/20 p-1 h-auto"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Messages Area */}
      {!isMinimized && (
        <>
          <div className="flex-1 overflow-y-auto p-3 bg-gradient-to-br from-purple-50/30 to-pink-50/30">
            {messages.length === 0 ? (
              <div className="text-center py-8">
                <Sparkles className="w-8 h-8 text-purple-400 mx-auto mb-2" />
                <p className="text-sm text-gray-600">
                  {worldMode === 'Maya' 
                    ? 'Chat with AI avatar' 
                    : 'Start a conversation'}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${
                      msg.sender_id === user.id ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`flex items-end space-x-1 max-w-[85%] ${
                        msg.sender_id === user.id ? "flex-row-reverse space-x-reverse" : ""
                      }`}
                    >
                      <Avatar className="w-6 h-6 flex-shrink-0">
                        <AvatarImage
                          src={msg.sender_id === user.id 
                            ? (worldMode === 'Maya' ? user.avatar_picture || user.picture : user.picture)
                            : displayPicture
                          }
                        />
                        <AvatarFallback
                          className={`text-white text-xs ${
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
                        className={`px-3 py-2 rounded-2xl text-sm ${
                          msg.sender_id === user.id
                            ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white"
                            : "bg-white border border-purple-100 text-gray-800"
                        }`}
                      >
                        {msg.is_ai && msg.sender_id !== user.id && (
                          <div className="flex items-center space-x-1 mb-1">
                            <Bot className="w-2.5 h-2.5 text-purple-400" />
                            <span className="text-[10px] text-purple-400">AI</span>
                          </div>
                        )}
                        <p>{msg.content}</p>
                        <p
                          className={`text-[10px] mt-1 ${
                            msg.sender_id === user.id ? "text-pink-100" : "text-gray-400"
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

          {/* Input Area */}
          <div className="p-3 border-t border-purple-100 bg-white">
            <div className="flex space-x-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && !sending && sendMessage()}
                placeholder={`Message ${displayName}...`}
                disabled={sending}
                className="flex-1 border-2 border-purple-200 focus:border-purple-400 rounded-xl text-sm"
              />
              <Button
                onClick={sendMessage}
                disabled={sending || !input.trim()}
                className="bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl px-3"
              >
                {sending ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>
        </>
      )}
    </Card>
  );
};

export default SideMessenger;
