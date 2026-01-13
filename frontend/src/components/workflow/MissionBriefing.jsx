/**
 * MissionBriefing Component
 * Concise briefing view explaining mission results and recommendations
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Target, Users, MessageCircle, TrendingUp, Star,
  ArrowRight, Lightbulb, RefreshCw, ChevronRight,
  Sparkles, CheckCircle, AlertTriangle, Send
} from 'lucide-react';

const MissionBriefing = ({
  mission,
  leads = [],
  activities = [],
  summary = null,
  avatarName,
  avatarPicture,
  onFollowUp,
  onRefineScope,
  onNewMission,
  onViewLead,
  className = '',
}) => {
  if (!mission) return null;

  const getInsights = () => {
    const insights = [];
    
    // Generate insights from results
    if (summary) {
      if (summary.total_leads > 0) {
        insights.push({
          type: 'success',
          icon: Users,
          text: `Found ${summary.total_leads} potential ${mission.type === 'matchmaking' ? 'matches' : 'leads'}`,
        });
      }
      
      if (summary.high_priority_leads > 0) {
        insights.push({
          type: 'highlight',
          icon: Star,
          text: `${summary.high_priority_leads} high-priority ${summary.high_priority_leads === 1 ? 'result' : 'results'} ready for follow-up`,
        });
      }
      
      if (summary.avg_match_score > 70) {
        insights.push({
          type: 'success',
          icon: TrendingUp,
          text: `Strong compatibility (${summary.avg_match_score}% average match)`,
        });
      } else if (summary.avg_match_score > 0 && summary.avg_match_score < 50) {
        insights.push({
          type: 'warning',
          icon: AlertTriangle,
          text: `Low compatibility scores - consider refining criteria`,
        });
      }
      
      if (summary.top_interest_matches?.length > 0) {
        insights.push({
          type: 'info',
          icon: Sparkles,
          text: `Top shared interests: ${summary.top_interest_matches.slice(0, 3).join(', ')}`,
        });
      }
    }
    
    return insights;
  };

  const getRecommendations = () => {
    const recommendations = [];
    
    if (leads.length > 0) {
      const highPriority = leads.filter(l => l.priority === 'high');
      if (highPriority.length > 0) {
        recommendations.push({
          action: 'follow_up',
          text: `Connect with ${highPriority.length} high-priority ${highPriority.length === 1 ? 'lead' : 'leads'}`,
          priority: 'high',
        });
      }
    }
    
    if (summary?.total_leads === 0) {
      recommendations.push({
        action: 'refine',
        text: 'Expand search criteria for better results',
        priority: 'medium',
      });
    }
    
    if (mission.status === 'completed' && leads.length < 5) {
      recommendations.push({
        action: 'new_mission',
        text: 'Run another mission with different parameters',
        priority: 'low',
      });
    }
    
    return recommendations;
  };

  const insights = getInsights();
  const recommendations = getRecommendations();
  const topLeads = leads.slice(0, 3);

  return (
    <motion.div
      className={`rounded-xl overflow-hidden bg-white/90 backdrop-blur-sm border border-gray-200 shadow-sm ${className}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Avatar className="w-10 h-10 border-2 border-purple-400">
              <AvatarImage src={avatarPicture} />
              <AvatarFallback className="bg-gradient-to-br from-purple-500 to-pink-500 text-white">
                {avatarName?.charAt(0)?.toUpperCase() || 'A'}
              </AvatarFallback>
            </Avatar>
            <CheckCircle className="absolute -bottom-1 -right-1 w-4 h-4 text-green-500 bg-white rounded-full" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-800">Mission Briefing</h3>
            <p className="text-xs text-gray-500">{mission.name}</p>
          </div>
          <Badge 
            variant="outline" 
            className="ml-auto text-green-600 border-green-500/50 bg-green-50"
          >
            Complete
          </Badge>
        </div>
      </div>

      <ScrollArea className="h-[calc(100vh-180px)]">
        <div className="p-4 space-y-6">
          {/* Quick Stats */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Explored', value: mission.progress?.stats?.profiles_discovered || 0, icon: Target },
              { label: 'Evaluated', value: mission.progress?.stats?.profiles_evaluated || 0, icon: Users },
              { label: 'Engaged', value: mission.progress?.stats?.conversations_started || 0, icon: MessageCircle },
              { label: 'Leads', value: summary?.total_leads || 0, icon: Star },
            ].map((stat, i) => (
              <div key={i} className="text-center p-2 rounded-lg bg-purple-50 border border-purple-100">
                <stat.icon className="w-4 h-4 mx-auto text-purple-500 mb-1" />
                <p className="text-lg font-bold text-gray-800">{stat.value}</p>
                <p className="text-[10px] text-gray-500 uppercase">{stat.label}</p>
              </div>
            ))}
          </div>

          {/* Insights */}
          {insights.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs uppercase tracking-wider text-gray-500 flex items-center gap-2">
                <Lightbulb className="w-3 h-3 text-gray-500" />
                Key Insights
              </h4>
              {insights.map((insight, i) => (
                <motion.div
                  key={i}
                  className={`flex items-center gap-3 p-3 rounded-lg ${
                    insight.type === 'success' ? 'bg-green-50 border border-green-200' :
                    insight.type === 'highlight' ? 'bg-purple-50 border border-purple-200' :
                    insight.type === 'warning' ? 'bg-yellow-50 border border-yellow-200' :
                    'bg-gray-50 border border-gray-200'
                  }`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                >
                  <insight.icon className={`w-4 h-4 flex-shrink-0 ${
                    insight.type === 'success' ? 'text-green-500' :
                    insight.type === 'highlight' ? 'text-purple-500' :
                    insight.type === 'warning' ? 'text-yellow-500' :
                    'text-gray-500'
                  }`} />
                  <p className="text-sm text-gray-700">{insight.text}</p>
                </motion.div>
              ))}
            </div>
          )}

          {/* Marketing Campaign Engagement Details */}
          {(mission.type === 'sales_leads' || mission.type === 'marketing') && activities.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs uppercase tracking-wider text-gray-500 flex items-center gap-2">
                <Send className="w-3 h-3 text-gray-500" />
                Campaign Engagement ({activities.filter(a => a.type === 'send_campaign_message').length})
              </h4>
              <div className="overflow-y-auto overflow-x-hidden space-y-2 pr-2" style={{ maxHeight: '400px' }}>
                {activities
                  .filter(activity => activity.type === 'send_campaign_message')
                  .map((activity, i) => (
                      <motion.div
                        key={i}
                        className="p-3 rounded-lg bg-blue-50 border border-blue-200 hover:bg-blue-100 transition-colors cursor-pointer"
                        onClick={() => window.location.href = `/profile/${activity.metadata?.target_user_id}`}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: Math.min(i * 0.03, 0.5) }}
                      >
                        <div className="flex items-start gap-3">
                          <Avatar className="w-8 h-8 flex-shrink-0">
                            <AvatarFallback className="bg-gradient-to-br from-blue-400 to-cyan-400 text-white text-xs">
                              {activity.metadata?.target_name?.charAt(0) || '?'}
                            </AvatarFallback>
                          </Avatar>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <p className="font-medium text-gray-800 text-sm">
                                {activity.metadata?.target_name || 'Unknown'}
                              </p>
                              {activity.metadata?.is_friend && (
                                <Badge variant="outline" className="text-[10px] text-blue-600 border-blue-500/50 bg-blue-50">
                                  Friend
                                </Badge>
                              )}
                            </div>
                            <p className="text-xs text-gray-600 italic mb-1">
                              "{activity.metadata?.message_content || 'Message sent'}"
                            </p>
                            {activity.metadata?.shared_interests?.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {activity.metadata.shared_interests.map((interest, idx) => (
                                  <Badge 
                                    key={idx} 
                                    variant="outline" 
                                    className="text-[10px] text-gray-600 border-gray-300 bg-white"
                                  >
                                    {interest}
                                  </Badge>
                                ))}
                              </div>
                            )}
                            <p className="text-[10px] text-gray-400 mt-1">
                              {new Date(activity.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      </motion.div>
                    ))}
              </div>
            </div>
          )}

          {/* Top Results - NOW SHOWS ALL LEADS WITH SCROLL */}
          {leads.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs uppercase tracking-wider text-gray-500 flex items-center gap-2">
                <Star className="w-3 h-3 text-gray-500" />
                Top Results ({leads.length})
              </h4>
              {leads.map((lead, i) => (
                <motion.div
                  key={lead.id}
                  className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 border border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => window.location.href = `/profile/${lead.target_user_id}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(0.2 + i * 0.05, 1) }}
                >
                  <Avatar className="w-10 h-10">
                    <AvatarImage src={lead.target_picture} />
                    <AvatarFallback className="bg-gradient-to-br from-purple-400 to-pink-400 text-white text-sm">
                      {lead.target_avatar_name?.charAt(0) || '?'}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-800 text-sm truncate">
                      {lead.target_avatar_name}
                    </p>
                    <p className="text-xs text-gray-500 truncate">
                      {lead.match_details?.shared_interests?.slice(0, 2).join(', ') || lead.target_real_name}
                    </p>
                  </div>
                  <Badge 
                    variant="outline" 
                    className={`text-xs ${
                      lead.priority === 'high' 
                        ? 'text-green-600 border-green-500/50 bg-green-50' 
                        : 'text-gray-600 border-gray-300'
                    }`}
                  >
                    {lead.score}%
                  </Badge>
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                </motion.div>
              ))}
            </div>
          )}

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs uppercase tracking-wider text-gray-500 flex items-center gap-2">
                <ArrowRight className="w-3 h-3 text-gray-500" />
                Recommended Actions
              </h4>
              <div className="grid gap-2">
                {recommendations.map((rec, i) => (
                  <Button
                    key={i}
                    variant="ghost"
                    className={`justify-start text-sm h-auto py-3 ${
                      rec.priority === 'high' 
                        ? 'bg-purple-50 hover:bg-purple-100 border border-purple-200' 
                        : 'bg-gray-50 hover:bg-gray-100 border border-gray-200'
                    }`}
                    onClick={() => {
                      if (rec.action === 'follow_up') onFollowUp?.();
                      else if (rec.action === 'refine') onRefineScope?.();
                      else if (rec.action === 'new_mission') onNewMission?.();
                    }}
                  >
                    {rec.action === 'follow_up' && <MessageCircle className="w-4 h-4 mr-2 text-purple-500" />}
                    {rec.action === 'refine' && <RefreshCw className="w-4 h-4 mr-2 text-purple-500" />}
                    {rec.action === 'new_mission' && <Target className="w-4 h-4 mr-2 text-purple-500" />}
                    <span className="text-gray-700">{rec.text}</span>
                    <ChevronRight className="w-4 h-4 ml-auto text-gray-400" />
                  </Button>
                ))}
              </div>
            </div>
          )}

          {/* Avatar narration */}
          <div className="p-4 rounded-lg bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200">
            <div className="flex items-start gap-3">
              <Avatar className="w-8 h-8 border border-purple-400">
                <AvatarImage src={avatarPicture} />
                <AvatarFallback className="bg-gradient-to-br from-purple-500 to-pink-500 text-white text-xs">
                  {avatarName?.charAt(0)?.toUpperCase() || 'A'}
                </AvatarFallback>
              </Avatar>
              <div>
                <p className="text-sm text-gray-700">
                  {leads.length > 0 
                    ? `I found ${leads.length} interesting ${mission.type === 'matchmaking' ? 'people' : 'opportunities'} for you. ${
                        leads.filter(l => l.priority === 'high').length > 0 
                          ? `${leads.filter(l => l.priority === 'high').length} look especially promising.`
                          : ''
                      }`
                    : "The search didn't find strong matches with current criteria. Want me to try with different parameters?"
                  }
                </p>
                <p className="text-xs text-gray-500 mt-1">— {avatarName}</p>
              </div>
            </div>
          </div>
        </div>
      </ScrollArea>
    </motion.div>
  );
};

export default MissionBriefing;

