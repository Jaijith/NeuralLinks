/**
 * Avatar Chat Interface
 * Chat interface for communicating with your avatar
 */

import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Send, Bot, User, Sparkles, Target, MessageCircle,
  Loader2, ChevronDown, Rocket, XCircle
} from 'lucide-react';
import { chatService, missionService } from '@/services/api/workflowService';
import { toast } from 'sonner';

const AvatarChatInterface = ({ user, avatarName, avatarPicture, onMissionCreated }) => {
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef(null);

  // Initialize chat session
  useEffect(() => {
    if (user?.id) {
      initializeSession();
    }
  }, [user?.id]);

  const initializeSession = async () => {
    setIsLoading(true);
    try {
      const response = await chatService.createSession(user.id);
      if (response.success) {
        setSession(response);
        
        // Load history if session has messages
        if (response.message_count > 0) {
          const historyResponse = await chatService.getHistory(user.id, 20);
          if (historyResponse.success) {
            setMessages(historyResponse.messages.reverse());
          }
        }
      }
    } catch (error) {
      console.error('Failed to initialize chat session:', error);
      toast.error('Failed to connect to avatar');
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isSending || !session) return;

    const content = inputValue.trim();
    setInputValue('');
    setIsSending(true);

    // Add user message immediately
    const userMessage = {
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await chatService.sendMessage(session.session_id, content);
      
      if (response.success) {
        // Add avatar response
        if (response.avatar_response) {
          setMessages(prev => [...prev, {
            role: 'avatar',
            content: response.avatar_response,
            timestamp: new Date().toISOString(),
            intent: response.intent,
            mission_created: response.mission_created
          }]);
        }

        // Notify parent if mission was created
        if (response.mission_created && onMissionCreated) {
          onMissionCreated(response.mission_created);
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to send message');
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const renderMessage = (message, index) => {
    const isUser = message.role === 'user';
    const isAvatar = message.role === 'avatar';

    return (
      <div
        key={index}
        className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
      >
        {/* Avatar */}
        <Avatar className="w-8 h-8 shrink-0">
          {isUser ? (
            <>
              <AvatarImage src={user?.picture} />
              <AvatarFallback className="bg-blue-500 text-white">
                <User className="w-4 h-4" />
              </AvatarFallback>
            </>
          ) : (
            <>
              <AvatarImage src={avatarPicture} />
              <AvatarFallback className="bg-gradient-to-br from-purple-500 to-pink-500 text-white">
                <Bot className="w-4 h-4" />
              </AvatarFallback>
            </>
          )}
        </Avatar>

        {/* Message bubble */}
        <div className={`max-w-[80%] space-y-1`}>
          <div
            className={`px-4 py-2.5 rounded-2xl ${
              isUser
                ? 'bg-blue-500 text-white rounded-tr-none'
                : 'bg-gray-100 text-gray-800 rounded-tl-none'
            }`}
          >
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          </div>

          {/* Intent badge */}
          {message.intent && message.intent !== 'general_chat' && (
            <div className="flex justify-start">
              <Badge variant="outline" className="text-xs">
                {message.intent === 'start_mission' && <Target className="w-3 h-3 mr-1" />}
                {message.intent}
              </Badge>
            </div>
          )}

          {/* Mission created indicator */}
          {message.mission_created && (
            <Card className="p-2 bg-green-50 border-green-200">
              <div className="flex items-center gap-2 text-green-700 text-xs">
                <Rocket className="w-4 h-4" />
                <span>Mission started: {message.mission_created.mission_name}</span>
              </div>
            </Card>
          )}

          {/* Timestamp */}
          <p className={`text-xs text-gray-400 ${isUser ? 'text-right' : 'text-left'}`}>
            {new Date(message.timestamp).toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </p>
        </div>
      </div>
    );
  };

  const suggestedPrompts = [
    { text: "Find me matches who love technology", icon: <Target className="w-4 h-4" /> },
    { text: "Search for people interested in AI", icon: <Sparkles className="w-4 h-4" /> },
    { text: "How many leads do I have?", icon: <MessageCircle className="w-4 h-4" /> }
  ];

  if (isLoading) {
    return (
      <Card className="p-6 flex items-center justify-center h-96">
        <div className="text-center space-y-3">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-purple-500" />
          <p className="text-gray-500">Connecting to your avatar...</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="flex flex-col h-[500px] overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b bg-gradient-to-r from-purple-500 to-pink-500">
        <div className="flex items-center gap-3">
          <Avatar className="w-10 h-10 border-2 border-white/50">
            <AvatarImage src={avatarPicture} />
            <AvatarFallback className="bg-white/20 text-white">
              <Bot className="w-5 h-5" />
            </AvatarFallback>
          </Avatar>
          <div>
            <h3 className="font-semibold text-white">{avatarName || 'Your Avatar'}</h3>
            <p className="text-xs text-white/80 flex items-center gap-1">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              Online • Ready to help
            </p>
          </div>
        </div>
      </div>

      {/* Messages area */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-8 space-y-4">
              <div className="w-16 h-16 mx-auto bg-gradient-to-br from-purple-100 to-pink-100 rounded-full flex items-center justify-center">
                <Bot className="w-8 h-8 text-purple-500" />
              </div>
              <div>
                <h4 className="font-medium text-gray-700">Chat with your avatar</h4>
                <p className="text-sm text-gray-500 mt-1">
                  Ask me to find matches, search for leads, or run any workflow
                </p>
              </div>

              {/* Suggested prompts */}
              <div className="space-y-2 pt-4">
                {suggestedPrompts.map((prompt, idx) => (
                  <Button
                    key={idx}
                    variant="outline"
                    size="sm"
                    className="w-full justify-start text-left"
                    onClick={() => setInputValue(prompt.text)}
                  >
                    {prompt.icon}
                    <span className="ml-2">{prompt.text}</span>
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            messages.map(renderMessage)
          )}

          {isSending && (
            <div className="flex gap-3">
              <Avatar className="w-8 h-8 shrink-0">
                <AvatarImage src={avatarPicture} />
                <AvatarFallback className="bg-gradient-to-br from-purple-500 to-pink-500 text-white">
                  <Bot className="w-4 h-4" />
                </AvatarFallback>
              </Avatar>
              <div className="bg-gray-100 px-4 py-2.5 rounded-2xl rounded-tl-none">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input area */}
      <div className="p-4 border-t bg-gray-50">
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask your avatar to find matches, search leads..."
            className="flex-1"
            disabled={isSending}
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isSending}
            className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
          >
            {isSending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </Card>
  );
};

export default AvatarChatInterface;

