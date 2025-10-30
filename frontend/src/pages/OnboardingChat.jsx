import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Bot, Send, Sparkles } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const OnboardingChat = ({ user }) => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: `Hi ${user.name}! I'm your AI dating assistant. I'll help you create an amazing profile by getting to know you better. Let's start with the basics - how old are you and where are you located?`,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const [profileData, setProfileData] = useState({
    age: null,
    gender: null,
    location: null,
    bio: "",
    interests: [],
  });

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await axios.post(
        `${API}/profile/onboarding-chat`,
        { message: input },
        { withCredentials: true }
      );

      const aiMessage = { role: "assistant", content: response.data.response };
      setMessages((prev) => [...prev, aiMessage]);

      // TODO: Extract profile data from AI response and update profileData
    } catch (error) {
      console.error("Error:", error);
      toast.error("Failed to send message");
      const errorMessage = {
        role: "assistant",
        content: "I'm sorry, I'm having trouble right now. Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const completeOnboarding = async () => {
    try {
      await axios.put(
        `${API}/profile`,
        { ...profileData, profile_completed: true, onboarding_stage: "complete" },
        { withCredentials: true }
      );
      toast.success("Profile completed!");
      navigate("/dashboard");
    } catch (error) {
      console.error("Error:", error);
      toast.error("Failed to complete profile");
    }
  };

  const skipForNow = () => {
    toast.info("You can complete your profile later from settings");
    navigate("/dashboard");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50">
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="text-center mb-8 fade-in" data-testid="onboarding-header">
          <div className="w-20 h-20 bg-gradient-to-br from-pink-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <Bot className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold gradient-text mb-2">Meet Your AI Assistant</h1>
          <p className="text-gray-600">Let's build your perfect profile together</p>
        </div>

        {/* Chat Container */}
        <Card className="glass-morphism p-6 mb-6" data-testid="chat-container">
          <div className="h-96 overflow-y-auto mb-4 space-y-4" style={{ scrollBehavior: "smooth" }}>
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} fade-in`}
                data-testid={`message-${idx}`}
              >
                <div
                  className={`flex items-start space-x-3 max-w-md ${
                    msg.role === "user" ? "flex-row-reverse space-x-reverse" : ""
                  }`}
                >
                  {msg.role === "assistant" ? (
                    <div className="w-10 h-10 bg-gradient-to-br from-pink-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <Bot className="w-6 h-6 text-white" />
                    </div>
                  ) : (
                    <Avatar className="w-10 h-10 flex-shrink-0">
                      <AvatarImage src={user.picture} />
                      <AvatarFallback className="bg-gradient-to-br from-indigo-400 to-indigo-600 text-white">
                        {user.name?.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                  )}
                  <div
                    className={`px-4 py-3 rounded-2xl ${
                      msg.role === "user"
                        ? "bg-gradient-to-r from-pink-500 to-purple-600 text-white"
                        : "bg-white border border-purple-100"
                    }`}
                  >
                    <p className={msg.role === "user" ? "text-white" : "text-gray-800"}>{msg.content}</p>
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start" data-testid="loading-indicator">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-pink-500 to-purple-600 rounded-full flex items-center justify-center">
                    <Bot className="w-6 h-6 text-white" />
                  </div>
                  <div className="bg-white border border-purple-100 px-4 py-3 rounded-2xl">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                      <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="flex space-x-3" data-testid="chat-input">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Type your message..."
              disabled={loading}
              className="flex-1 border-2 border-purple-200 focus:border-purple-400 rounded-xl px-4 py-3"
              data-testid="message-input"
            />
            <Button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              data-testid="send-message-btn"
              className="btn-primary text-white px-6 py-3 rounded-xl"
            >
              <Send className="w-5 h-5" />
            </Button>
          </div>
        </Card>

        {/* Actions */}
        <div className="flex justify-between items-center" data-testid="onboarding-actions">
          <Button
            variant="ghost"
            onClick={skipForNow}
            data-testid="skip-btn"
            className="text-gray-600 hover:text-gray-800"
          >
            Skip for now
          </Button>
          <Button
            onClick={completeOnboarding}
            data-testid="complete-profile-btn"
            className="btn-primary text-white px-8 py-3 rounded-full"
          >
            <Sparkles className="w-5 h-5 mr-2" />
            Complete Profile
          </Button>
        </div>
      </div>
    </div>
  );
};

export default OnboardingChat;
