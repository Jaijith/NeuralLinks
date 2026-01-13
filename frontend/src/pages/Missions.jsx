/**
 * Missions Page - World Simulation & Command Interface
 * A living canvas where the user's avatar operates in a social world
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  MessageCircle, Send, Loader2, Maximize2, Minimize2
} from 'lucide-react';
import { missionService, leadService, chatService } from '@/services/api/workflowService';
import { toast } from 'sonner';
import AppHeader from '@/components/AppHeader';
import WorldCanvas from '@/components/workflow/WorldCanvas';
import AvatarStatusStrip from '@/components/workflow/AvatarStatusStrip';
import MissionTimeline from '@/components/workflow/MissionTimeline';
import MissionBriefing from '@/components/workflow/MissionBriefing';

const Missions = ({ user, setUser }) => {
  const navigate = useNavigate();
  
  // Core state
  const [missions, setMissions] = useState([]);
  const [selectedMission, setSelectedMission] = useState(null);
  const [missionStatus, setMissionStatus] = useState(null);
  const [leads, setLeads] = useState([]);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // World canvas state
  const [worldEntities, setWorldEntities] = useState([]);
  const [worldInteractions, setWorldInteractions] = useState([]);
  const [worldPhase, setWorldPhase] = useState('idle');
  const [focusedEntity, setFocusedEntity] = useState(null);
  
  // Avatar state
  const [avatarStatus, setAvatarStatus] = useState('idle');
  const [currentAction, setCurrentAction] = useState(null);
  const [lastAction, setLastAction] = useState(null);
  
  // Chat state
  const [chatSession, setChatSession] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);
  const chatEndRef = useRef(null);
  
  // Polling ref
  const pollingRef = useRef(null);

  // Initialize
  useEffect(() => {
    if (user?.id) {
      loadMissions();
      initializeChatSession();
      initializeWorld();
    }
    
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [user?.id]);

  // Poll for updates when mission is running
  useEffect(() => {
    if (selectedMission?.status === 'running') {
      pollingRef.current = setInterval(() => {
        refreshMissionStatus(selectedMission.id);
      }, 3000);
    } else {
      if (pollingRef.current) clearInterval(pollingRef.current);
    }
    
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [selectedMission?.id, selectedMission?.status]);

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const loadMissions = async () => {
    setLoading(true);
    try {
      const response = await missionService.list(user.id);
      if (response.success) {
        setMissions(response.missions || []);
        
        // If there's a running mission, select it
        const runningMission = response.missions?.find(m => m.status === 'running');
        if (runningMission) {
          selectMission(runningMission);
        }
      }
    } catch (error) {
      console.error('Failed to load missions:', error);
    } finally {
      setLoading(false);
    }
  };

  const initializeChatSession = async () => {
    try {
      const response = await chatService.initSession(user.id, user.id);
      if (response.success) {
        // Store the full response which includes session_id
        setChatSession({
          id: response.session_id,
          user_id: response.user_id,
          avatar_id: response.avatar_id,
          messages: []
        });
        setChatMessages([]);
      }
    } catch (error) {
      console.error('Failed to init chat session:', error);
      toast.error('Failed to initialize chat');
    }
  };

  const initializeWorld = () => {
    // Add user's avatar as the central entity
    setWorldEntities([{
      id: user.id,
      name: user.avatar_name || user.name,
      picture: user.avatar_picture || user.picture,
      isUserAvatar: true,
      signal: 1.0,
      type: 'avatar',
    }]);
  };

  const selectMission = async (mission) => {
    setSelectedMission(mission);
    updateWorldForMission(mission);
    
    // Load mission status
    try {
      const statusResponse = await missionService.getStatus(mission.id);
      if (statusResponse.success) {
        setMissionStatus(statusResponse);
        updateAvatarStatus(statusResponse);
      }
    } catch (error) {
      console.error('Failed to load mission status:', error);
    }

    // Load leads
    try {
      const leadsResponse = await leadService.listForMission(mission.id);
      if (leadsResponse.success) {
        setLeads(leadsResponse.leads || []);
        updateWorldWithLeads(leadsResponse.leads || []);
      }
    } catch (error) {
      console.error('Failed to load leads:', error);
    }

    // Load activities (for marketing campaigns)
    try {
      const activitiesResponse = await missionService.getActivities(mission.id);
      if (activitiesResponse.success) {
        setActivities(activitiesResponse.activities || []);
      }
    } catch (error) {
      console.error('Failed to load activities:', error);
    }
  };

  const refreshMissionStatus = async (missionId) => {
    try {
      const statusResponse = await missionService.getStatus(missionId);
      if (statusResponse.success) {
        setMissionStatus(statusResponse);
        updateAvatarStatus(statusResponse);
        
        // Update mission in list
        setMissions(prev => prev.map(m => 
          m.id === missionId 
            ? { ...m, status: statusResponse.status, progress: statusResponse.progress, phase: statusResponse.phase }
            : m
        ));
        
        // Update selected mission if it's the same
        if (selectedMission?.id === missionId) {
          setSelectedMission(prev => ({
            ...prev,
            status: statusResponse.status,
            progress: statusResponse.progress,
            phase: statusResponse.phase,
          }));
        }
        
        // Refresh leads if mission completed
        if (statusResponse.status === 'completed' && selectedMission?.status === 'running') {
          const leadsResponse = await leadService.listForMission(missionId);
          if (leadsResponse.success) {
            setLeads(leadsResponse.leads || []);
            updateWorldWithLeads(leadsResponse.leads || []);
          }
        }
      }
    } catch (error) {
      console.error('Failed to refresh mission status:', error);
    }
  };

  const updateAvatarStatus = (statusResponse) => {
    const phase = statusResponse.phase;
    const status = statusResponse.status;
    
    if (status === 'completed') {
      setAvatarStatus('completed');
      setCurrentAction('Mission completed');
      setWorldPhase('stabilizing');
    } else if (status === 'paused') {
      setAvatarStatus('paused');
      setCurrentAction('Mission paused');
    } else if (status === 'running') {
      switch (phase) {
        case 'discovering':
          setAvatarStatus('searching');
          setCurrentAction('Exploring the world...');
          setWorldPhase('exploring');
          break;
        case 'evaluating':
          setAvatarStatus('analyzing');
          setCurrentAction('Evaluating profiles...');
          setWorldPhase('detecting');
          break;
        case 'engaging':
          setAvatarStatus('messaging');
          setCurrentAction('Engaging with matches...');
          setWorldPhase('interacting');
          break;
        case 'analyzing':
          setAvatarStatus('thinking');
          setCurrentAction('Generating insights...');
          setWorldPhase('stabilizing');
          break;
        default:
          setAvatarStatus('thinking');
          setCurrentAction('Initializing...');
          setWorldPhase('initializing');
      }
    } else {
      setAvatarStatus('idle');
      setCurrentAction(null);
      setWorldPhase('idle');
    }
  };

  const updateWorldForMission = (mission) => {
    // Keep user avatar, add placeholder entities for exploration effect
    const userEntity = {
      id: user.id,
      name: user.avatar_name || user.name,
      picture: user.avatar_picture || user.picture,
      isUserAvatar: true,
      signal: 1.0,
      type: 'avatar',
    };
    
    // Add discovered profiles as entities (from mission progress)
    const discoveredCount = mission.progress?.stats?.profiles_discovered || 0;
    const placeholders = Array.from({ length: Math.min(discoveredCount, 10) }, (_, i) => ({
      id: `discovered-${i}`,
      name: `Profile ${i + 1}`,
      signal: 0.3 + Math.random() * 0.3,
      type: 'discovered',
    }));
    
    setWorldEntities([userEntity, ...placeholders]);
  };

  const updateWorldWithLeads = (newLeads) => {
    const userEntity = {
      id: user.id,
      name: user.avatar_name || user.name,
      picture: user.avatar_picture || user.picture,
      isUserAvatar: true,
      signal: 1.0,
      type: 'avatar',
    };
    
    const leadEntities = newLeads.map(lead => ({
      id: lead.target_user_id,
      name: lead.target_avatar_name || 'Unknown',
      picture: lead.target_picture,
      signal: (lead.score || 50) / 100,
      type: 'lead',
      priority: lead.priority,
      score: lead.score,
    }));
    
    // Create interactions from user to high-signal leads
    const interactions = leadEntities
      .filter(e => e.signal > 0.6)
      .map(e => ({
        from: user.id,
        to: e.id,
        active: selectedMission?.status === 'running',
      }));
    
    setWorldEntities([userEntity, ...leadEntities]);
    setWorldInteractions(interactions);
    setWorldPhase(selectedMission?.status === 'completed' ? 'stabilizing' : 'detecting');
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isSending) return;
    
    // Ensure we have a chat session
    if (!chatSession || !chatSession.id) {
      toast.error('Chat session not initialized. Please refresh the page.');
      return;
    }
    
    const message = inputMessage.trim();
    setInputMessage('');
    setIsSending(true);
    setAvatarStatus('thinking');
    
    // Add user message to chat
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setChatMessages(prev => [...prev, userMessage]);
    
    try {
      const response = await chatService.sendMessage(chatSession.id, message);
      
      if (response.success) {
        // Add avatar response
        const avatarMessage = {
          role: 'assistant',
          content: response.avatar_response,
          timestamp: new Date().toISOString(),
        };
        setChatMessages(prev => [...prev, avatarMessage]);
        setLastAction(message);
        
        // Handle mission creation
        if (response.mission_created) {
          toast.success(`Mission started: ${response.mission_created.mission_name}`);
          
          // Auto-start the mission if requested
          if (response.mission_created.auto_start) {
            try {
              await missionService.start(response.mission_created.mission_id);
              console.log(`Auto-started mission: ${response.mission_created.mission_id}`);
            } catch (error) {
              console.error('Failed to auto-start mission:', error);
              toast.error('Mission created but failed to start automatically');
            }
          }
          
          loadMissions();
          setWorldPhase('initializing');
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to send message');
    } finally {
      setIsSending(false);
      setAvatarStatus(selectedMission?.status === 'running' ? 'searching' : 'idle');
    }
  };

  const handleMissionAction = async (missionId, action) => {
    try {
      switch (action) {
        case 'pause':
          await missionService.pause(missionId);
          toast.success('Mission paused');
          break;
        case 'resume':
          await missionService.resume(missionId);
          toast.success('Mission resumed');
          break;
        case 'cancel':
          await missionService.cancel(missionId);
          toast.success('Mission cancelled');
          break;
      }
      loadMissions();
    } catch (error) {
      toast.error(`Failed to ${action} mission`);
    }
  };

  const handleEntityClick = (entity) => {
    if (entity.isUserAvatar) return;
    setFocusedEntity(entity.id);
    
    if (entity.type === 'lead') {
      // Force full page navigation to profile
      window.location.href = `/profile/${entity.id}`;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-slate-50">
      <AppHeader user={user} setUser={setUser} currentPage="missions" />

      <main className="h-[calc(100vh-56px)] flex overflow-hidden">
        {/* Left Panel - Timeline & Chat */}
        <div className="w-80 flex flex-col border-r border-gray-200 bg-white shadow-sm">
          {/* Mission Timeline */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <MissionTimeline
              missions={missions}
              selectedMission={selectedMission}
              onSelectMission={selectMission}
              onReplayMission={(m) => toast.info('Replay coming soon')}
              onResumeMission={(m) => handleMissionAction(m.id, 'resume')}
              loading={loading}
              className="h-full"
            />
          </div>
          
          {/* Chat Interface - Fixed height container */}
          <div 
            className="flex-shrink-0 border-t border-gray-200 bg-white"
            style={{ height: chatExpanded ? '280px' : '180px', transition: 'height 0.2s ease' }}
          >
            <div className="h-full flex flex-col">
              {/* Chat Header */}
              <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700 flex items-center gap-2">
                  <MessageCircle className="w-4 h-4 text-purple-500" />
                  Command Center
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 text-gray-500 hover:text-gray-700"
                  onClick={() => setChatExpanded(!chatExpanded)}
                >
                  {chatExpanded ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
                </Button>
              </div>
              
              {/* Chat Messages */}
              <div className="flex-1 min-h-0 overflow-y-auto">
                <div className="p-3 space-y-2">
                  {chatMessages.length === 0 ? (
                    <p className="text-xs text-gray-400 text-center py-4">
                      Tell me what you're looking for...
                    </p>
                  ) : (
                    chatMessages.map((msg, i) => (
                      <div
                        key={i}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[85%] px-3 py-2 rounded-lg text-sm ${
                            msg.role === 'user'
                              ? 'bg-purple-500 text-white'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {msg.content}
                        </div>
                      </div>
                    ))
                  )}
                  <div ref={chatEndRef} />
                </div>
              </div>
              
              {/* Chat Input - Fixed at bottom */}
              <div className="flex-shrink-0 p-3 border-t border-gray-100 bg-gray-50/50">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                    placeholder="Find people who..."
                    className="flex-1 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                    disabled={isSending}
                  />
                  <Button
                    size="sm"
                    onClick={handleSendMessage}
                    disabled={isSending || !inputMessage.trim()}
                    className="bg-purple-500 hover:bg-purple-600 px-3"
                  >
                    {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Center Panel - World Canvas */}
        <div className="flex-1 flex flex-col">
          {/* Avatar Status Strip */}
          <div className="p-4">
            <AvatarStatusStrip
              avatarName={user?.avatar_name || user?.name}
              avatarPicture={user?.avatar_picture || user?.picture}
              status={avatarStatus}
              currentAction={currentAction}
              activeMission={selectedMission?.status === 'running' ? selectedMission : null}
              lastAction={lastAction}
            />
          </div>
          
          {/* World Canvas */}
          <div className="flex-1 p-4 pt-0">
            <WorldCanvas
              entities={worldEntities}
              interactions={worldInteractions}
              phase={worldPhase}
              focusedEntity={focusedEntity}
              onEntityClick={handleEntityClick}
              onEntityHover={(e) => e && setFocusedEntity(e.id)}
              missionActive={selectedMission?.status === 'running'}
              className="h-full"
            />
          </div>
        </div>

        {/* Right Panel - Briefing (when mission selected) */}
        <AnimatePresence>
          {selectedMission?.status === 'completed' && (
            <motion.div
              className="w-96 border-l border-gray-200 bg-white/80 backdrop-blur-sm"
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 384, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
            >
              <MissionBriefing
                mission={selectedMission}
                leads={leads}
                activities={activities}
                summary={missionStatus?.results_summary}
                avatarName={user?.avatar_name || user?.name}
                avatarPicture={user?.avatar_picture || user?.picture}
                onFollowUp={() => toast.info('Follow-up coming soon')}
                onRefineScope={() => toast.info('Refine scope coming soon')}
                onNewMission={() => setChatExpanded(true)}
                onViewLead={(lead) => navigate(`/profile/${lead.target_user_id}`)}
                className="h-full"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
};

export default Missions;
