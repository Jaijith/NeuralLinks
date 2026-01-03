/**
 * Missions Page
 * View and manage workflow missions
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Target, Rocket, Pause, Play, XCircle, Clock, CheckCircle,
  AlertCircle, Users, MessageCircle, TrendingUp, ChevronRight,
  Plus, Bot, Loader2, Heart
} from 'lucide-react';
import { missionService, leadService } from '@/services/api/workflowService';
import { toast } from 'sonner';
import AppHeader from '@/components/AppHeader';
import AvatarChatInterface from '@/components/workflow/AvatarChatInterface';

const Missions = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [missions, setMissions] = useState([]);
  const [selectedMission, setSelectedMission] = useState(null);
  const [missionStatus, setMissionStatus] = useState(null);
  const [leads, setLeads] = useState([]);
  const [leadStats, setLeadStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('all');

  useEffect(() => {
    if (user?.id) {
      loadMissions();
      loadLeadStats();
    }
  }, [user?.id, activeTab]);

  const loadMissions = async () => {
    setLoading(true);
    try {
      const statusFilter = activeTab === 'all' ? null : activeTab;
      const response = await missionService.list(user.id, { status: statusFilter });
      if (response.success) {
        setMissions(response.missions || []);
      }
    } catch (error) {
      console.error('Failed to load missions:', error);
      toast.error('Failed to load missions');
    } finally {
      setLoading(false);
    }
  };

  const loadLeadStats = async () => {
    try {
      const response = await leadService.getStats(user.id);
      if (response.success) {
        setLeadStats(response.stats);
      }
    } catch (error) {
      console.error('Failed to load lead stats:', error);
    }
  };

  const selectMission = async (mission) => {
    setSelectedMission(mission);
    
    // Load mission status
    try {
      const statusResponse = await missionService.getStatus(mission.id);
      if (statusResponse.success) {
        setMissionStatus(statusResponse);
      }
    } catch (error) {
      console.error('Failed to load mission status:', error);
    }

    // Load leads for this mission
    try {
      const leadsResponse = await leadService.listForMission(mission.id);
      if (leadsResponse.success) {
        setLeads(leadsResponse.leads || []);
      }
    } catch (error) {
      console.error('Failed to load leads:', error);
    }
  };

  const handleMissionAction = async (missionId, action) => {
    try {
      let response;
      switch (action) {
        case 'pause':
          response = await missionService.pause(missionId);
          toast.success('Mission paused');
          break;
        case 'resume':
          response = await missionService.resume(missionId);
          toast.success('Mission resumed');
          break;
        case 'cancel':
          response = await missionService.cancel(missionId);
          toast.success('Mission cancelled');
          break;
        default:
          break;
      }
      loadMissions();
      if (selectedMission?.id === missionId) {
        selectMission({ id: missionId });
      }
    } catch (error) {
      console.error(`Failed to ${action} mission:`, error);
      toast.error(`Failed to ${action} mission`);
    }
  };

  const handleMissionCreated = (missionInfo) => {
    toast.success(`Mission started: ${missionInfo.mission_name}`);
    loadMissions();
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return <Rocket className="w-4 h-4 text-blue-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'paused':
        return <Pause className="w-4 h-4 text-yellow-500" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'cancelled':
        return <XCircle className="w-4 h-4 text-gray-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running':
        return 'bg-blue-100 text-blue-700';
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'paused':
        return 'bg-yellow-100 text-yellow-700';
      case 'failed':
        return 'bg-red-100 text-red-700';
      case 'cancelled':
        return 'bg-gray-100 text-gray-700';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const getMissionTypeIcon = (type) => {
    switch (type) {
      case 'matchmaking':
        return '💕';
      case 'networking':
        return '🤝';
      case 'sales_leads':
        return '💼';
      case 'job_finder':
        return '🎯';
      default:
        return '🚀';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50">
      <AppHeader user={user} setUser={setUser} currentPage="missions" />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats Bar */}
        {leadStats && (
          <div className="grid grid-cols-4 gap-4 mb-8">
            <Card className="p-4 text-center">
              <Target className="w-6 h-6 mx-auto text-purple-500 mb-2" />
              <p className="text-2xl font-bold">{leadStats.total}</p>
              <p className="text-sm text-gray-500">Total Leads</p>
            </Card>
            <Card className="p-4 text-center">
              <TrendingUp className="w-6 h-6 mx-auto text-blue-500 mb-2" />
              <p className="text-2xl font-bold">{leadStats.avg_score}%</p>
              <p className="text-sm text-gray-500">Avg Score</p>
            </Card>
            <Card className="p-4 text-center">
              <Users className="w-6 h-6 mx-auto text-green-500 mb-2" />
              <p className="text-2xl font-bold">{leadStats.high_priority}</p>
              <p className="text-sm text-gray-500">High Priority</p>
            </Card>
            <Card className="p-4 text-center">
              <CheckCircle className="w-6 h-6 mx-auto text-orange-500 mb-2" />
              <p className="text-2xl font-bold">{leadStats.conversion_rate}%</p>
              <p className="text-sm text-gray-500">Conversion</p>
            </Card>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Left Column - Chat & Missions List */}
          <div className="lg:col-span-1 space-y-6">
            {/* Avatar Chat */}
            <AvatarChatInterface
              user={user}
              avatarName={user?.avatar_name}
              avatarPicture={user?.avatar_picture}
              onMissionCreated={handleMissionCreated}
            />

            {/* Missions List */}
            <Card className="overflow-hidden">
              <div className="p-4 border-b">
                <h3 className="font-semibold flex items-center gap-2">
                  <Rocket className="w-5 h-5 text-purple-500" />
                  Your Missions
                </h3>
              </div>

              <Tabs value={activeTab} onValueChange={setActiveTab} className="p-2">
                <TabsList className="w-full">
                  <TabsTrigger value="all" className="flex-1">All</TabsTrigger>
                  <TabsTrigger value="running" className="flex-1">Active</TabsTrigger>
                  <TabsTrigger value="completed" className="flex-1">Done</TabsTrigger>
                </TabsList>
              </Tabs>

              <ScrollArea className="h-[300px]">
                {loading ? (
                  <div className="p-4 text-center">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-purple-500" />
                  </div>
                ) : missions.length === 0 ? (
                  <div className="p-4 text-center text-gray-500">
                    <Target className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                    <p>No missions yet</p>
                    <p className="text-sm">Chat with your avatar to start one</p>
                  </div>
                ) : (
                  <div className="p-2 space-y-2">
                    {missions.map((mission) => (
                      <Card
                        key={mission.id}
                        className={`p-3 cursor-pointer hover:bg-gray-50 transition-colors ${
                          selectedMission?.id === mission.id ? 'ring-2 ring-purple-500' : ''
                        }`}
                        onClick={() => selectMission(mission)}
                      >
                        <div className="flex items-start gap-3">
                          <span className="text-2xl">{getMissionTypeIcon(mission.type)}</span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm truncate">{mission.name}</span>
                              {getStatusIcon(mission.status)}
                            </div>
                            <Badge variant="outline" className={`text-xs mt-1 ${getStatusColor(mission.status)}`}>
                              {mission.status}
                            </Badge>
                            {mission.progress && (
                              <Progress 
                                value={mission.progress.percentage} 
                                className="h-1 mt-2" 
                              />
                            )}
                          </div>
                          <ChevronRight className="w-4 h-4 text-gray-400" />
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </Card>
          </div>

          {/* Right Column - Mission Details & Leads */}
          <div className="lg:col-span-2 space-y-6">
            {selectedMission ? (
              <>
                {/* Mission Details */}
                <Card className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-4">
                      <span className="text-4xl">{getMissionTypeIcon(selectedMission.type)}</span>
                      <div>
                        <h2 className="text-xl font-bold">{selectedMission.name}</h2>
                        <p className="text-gray-500">{selectedMission.description}</p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {selectedMission.status === 'running' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleMissionAction(selectedMission.id, 'pause')}
                        >
                          <Pause className="w-4 h-4 mr-1" /> Pause
                        </Button>
                      )}
                      {selectedMission.status === 'paused' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleMissionAction(selectedMission.id, 'resume')}
                        >
                          <Play className="w-4 h-4 mr-1" /> Resume
                        </Button>
                      )}
                      {['running', 'paused', 'queued'].includes(selectedMission.status) && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleMissionAction(selectedMission.id, 'cancel')}
                        >
                          <XCircle className="w-4 h-4 mr-1" /> Cancel
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Progress */}
                  {missionStatus && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-500">{missionStatus.progress?.current_action}</span>
                        <span className="font-medium">{missionStatus.progress?.percentage}%</span>
                      </div>
                      <Progress value={missionStatus.progress?.percentage || 0} />
                      
                      <div className="grid grid-cols-4 gap-4 mt-4">
                        <div className="text-center">
                          <p className="text-lg font-bold">{missionStatus.progress?.stats?.profiles_discovered || 0}</p>
                          <p className="text-xs text-gray-500">Discovered</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-bold">{missionStatus.progress?.stats?.profiles_evaluated || 0}</p>
                          <p className="text-xs text-gray-500">Evaluated</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-bold">{missionStatus.progress?.stats?.conversations_started || 0}</p>
                          <p className="text-xs text-gray-500">Conversations</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-bold text-green-600">{missionStatus.lead_count || 0}</p>
                          <p className="text-xs text-gray-500">Leads</p>
                        </div>
                      </div>
                    </div>
                  )}
                </Card>

                {/* Leads */}
                <Card className="overflow-hidden">
                  <div className="p-4 border-b flex items-center justify-between">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Heart className="w-5 h-5 text-pink-500" />
                      Leads Found ({leads.length})
                    </h3>
                  </div>

                  <ScrollArea className="h-[400px]">
                    {leads.length === 0 ? (
                      <div className="p-8 text-center text-gray-500">
                        <Users className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                        <p>No leads yet</p>
                        <p className="text-sm">Leads will appear here as your avatar finds matches</p>
                      </div>
                    ) : (
                      <div className="divide-y">
                        {leads.map((lead) => (
                          <div
                            key={lead.id}
                            className="p-4 hover:bg-gray-50 cursor-pointer"
                            onClick={() => navigate(`/profile/${lead.target_user_id}`)}
                          >
                            <div className="flex items-start gap-4">
                              <Avatar className="w-12 h-12">
                                <AvatarImage src={lead.target_picture} />
                                <AvatarFallback className="bg-gradient-to-br from-purple-400 to-pink-400 text-white">
                                  {lead.target_avatar_name?.charAt(0) || '?'}
                                </AvatarFallback>
                              </Avatar>
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium">{lead.target_avatar_name}</span>
                                  <Badge variant={lead.priority === 'high' ? 'default' : 'outline'}>
                                    {lead.score}% match
                                  </Badge>
                                </div>
                                <p className="text-sm text-gray-500 mt-1">
                                  {lead.target_real_name}
                                </p>
                                {lead.match_details?.shared_interests?.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mt-2">
                                    {lead.match_details.shared_interests.slice(0, 3).map((interest, idx) => (
                                      <Badge key={idx} variant="secondary" className="text-xs">
                                        {interest}
                                      </Badge>
                                    ))}
                                  </div>
                                )}
                              </div>
                              <Button variant="outline" size="sm">
                                <MessageCircle className="w-4 h-4 mr-1" />
                                Connect
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </ScrollArea>
                </Card>
              </>
            ) : (
              <Card className="p-12 text-center">
                <Target className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                <h3 className="text-xl font-semibold text-gray-700 mb-2">Select a mission</h3>
                <p className="text-gray-500">
                  Choose a mission from the list or chat with your avatar to start a new one
                </p>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Missions;

