/**
 * MissionTimeline Component
 * Shows missions as timelines with phase progression
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Rocket, CheckCircle, Clock, Pause, XCircle, AlertCircle,
  Play, RotateCcw, ChevronRight, Zap, Search, MessageCircle,
  Brain, Target
} from 'lucide-react';

const PHASES = [
  { id: 'initializing', label: 'Init', icon: Zap },
  { id: 'discovering', label: 'Explore', icon: Search },
  { id: 'evaluating', label: 'Evaluate', icon: Brain },
  { id: 'engaging', label: 'Engage', icon: MessageCircle },
  { id: 'analyzing', label: 'Analyze', icon: Target },
];

const MissionTimelineItem = ({ 
  mission, 
  isSelected, 
  onClick,
  onReplay,
  onResume,
}) => {
  const getStatusConfig = (status) => {
    switch (status) {
      case 'running':
        return { 
          color: 'text-blue-500', 
          bg: 'bg-blue-50', 
          border: 'border-blue-200',
          icon: Rocket,
          pulse: true 
        };
      case 'completed':
        return { 
          color: 'text-green-500', 
          bg: 'bg-green-50', 
          border: 'border-green-200',
          icon: CheckCircle,
          pulse: false 
        };
      case 'paused':
        return { 
          color: 'text-yellow-500', 
          bg: 'bg-yellow-50', 
          border: 'border-yellow-200',
          icon: Pause,
          pulse: false 
        };
      case 'failed':
        return { 
          color: 'text-red-500', 
          bg: 'bg-red-50', 
          border: 'border-red-200',
          icon: AlertCircle,
          pulse: false 
        };
      case 'cancelled':
        return { 
          color: 'text-gray-400', 
          bg: 'bg-gray-50', 
          border: 'border-gray-200',
          icon: XCircle,
          pulse: false 
        };
      default:
        return { 
          color: 'text-gray-400', 
          bg: 'bg-gray-50', 
          border: 'border-gray-200',
          icon: Clock,
          pulse: false 
        };
    }
  };

  const config = getStatusConfig(mission.status);
  const StatusIcon = config.icon;
  
  // Find current phase index
  const currentPhaseIndex = PHASES.findIndex(p => p.id === mission.phase);
  
  // Get most recent event
  const lastEvent = mission.timeline?.last_activity_at 
    ? new Date(mission.timeline.last_activity_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null;

  const getMissionEmoji = (type) => {
    switch (type) {
      case 'matchmaking': return '💕';
      case 'networking': return '🤝';
      case 'sales_leads': return '💼';
      case 'job_finder': return '🎯';
      case 'research': return '🔬';
      default: return '🚀';
    }
  };

  return (
    <motion.div
      className={`relative p-3 rounded-lg cursor-pointer transition-all ${
        isSelected 
          ? `${config.bg} ${config.border} border shadow-sm` 
          : 'hover:bg-gray-50 border border-transparent'
      }`}
      onClick={onClick}
      whileHover={{ x: 2 }}
      layout
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <span className="text-2xl">{getMissionEmoji(mission.type)}</span>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-800 text-sm truncate">
              {mission.name}
            </span>
            <motion.div
              animate={config.pulse ? { scale: [1, 1.2, 1] } : {}}
              transition={{ duration: 1, repeat: Infinity }}
            >
              <StatusIcon className={`w-4 h-4 ${config.color}`} />
            </motion.div>
          </div>
          
          {/* Phase timeline */}
          <div className="flex items-center gap-1 mt-2">
            {PHASES.map((phase, idx) => {
              const isCompleted = idx < currentPhaseIndex;
              const isCurrent = idx === currentPhaseIndex;
              const PhaseIcon = phase.icon;
              
              return (
                <div key={phase.id} className="flex items-center">
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center ${
                      isCompleted 
                        ? 'bg-green-100 text-green-500' 
                        : isCurrent && mission.status === 'running'
                          ? 'bg-blue-100 text-blue-500'
                          : 'bg-gray-100 text-gray-400'
                    }`}
                    title={phase.label}
                  >
                    <PhaseIcon className="w-3 h-3" />
                  </div>
                  {idx < PHASES.length - 1 && (
                    <div className={`w-3 h-0.5 ${
                      isCompleted ? 'bg-green-300' : 'bg-gray-200'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>
          
          {/* Stats row */}
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
            {mission.progress?.stats && (
              <>
                <span>{mission.progress.stats.profiles_discovered || 0} found</span>
                <span>•</span>
                <span>{mission.progress.stats.leads_generated || 0} leads</span>
              </>
            )}
            {lastEvent && (
              <>
                <span>•</span>
                <span>{lastEvent}</span>
              </>
            )}
          </div>
        </div>
        
        <ChevronRight className={`w-4 h-4 ${isSelected ? 'text-gray-600' : 'text-gray-400'}`} />
      </div>
      
      {/* Quick actions on hover/select */}
      {isSelected && (mission.status === 'completed' || mission.status === 'paused') && (
        <motion.div 
          className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-200"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
        >
          {mission.status === 'completed' && (
            <button
              onClick={(e) => { e.stopPropagation(); onReplay?.(mission); }}
              className="flex items-center gap-1 px-2 py-1 text-xs text-purple-600 hover:bg-purple-50 rounded font-medium"
            >
              <RotateCcw className="w-3 h-3" />
              Replay
            </button>
          )}
          {mission.status === 'paused' && (
            <button
              onClick={(e) => { e.stopPropagation(); onResume?.(mission); }}
              className="flex items-center gap-1 px-2 py-1 text-xs text-green-600 hover:bg-green-50 rounded font-medium"
            >
              <Play className="w-3 h-3" />
              Resume
            </button>
          )}
        </motion.div>
      )}
    </motion.div>
  );
};

const MissionTimeline = ({
  missions = [],
  selectedMission,
  onSelectMission,
  onReplayMission,
  onResumeMission,
  loading = false,
  className = '',
}) => {
  // Group missions by status
  const activeMissions = missions.filter(m => m.status === 'running' || m.status === 'paused');
  const completedMissions = missions.filter(m => m.status === 'completed');
  const otherMissions = missions.filter(m => !['running', 'paused', 'completed'].includes(m.status));

  return (
    <div className={`flex flex-col h-full bg-white ${className}`}>
      {/* Header with proper spacing from top */}
      <div className="flex-shrink-0 px-4 pt-5 pb-3 border-b border-gray-100">
        <h3 className="font-semibold text-gray-800 flex items-center gap-2">
          <Rocket className="w-5 h-5 text-purple-500" />
          Mission Timeline
        </h3>
        <p className="text-xs text-gray-500 mt-1">
          {missions.length} mission{missions.length !== 1 ? 's' : ''}
        </p>
      </div>
      
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : missions.length === 0 ? (
            <div className="text-center py-8">
              <Target className="w-10 h-10 mx-auto text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">No missions yet</p>
              <p className="text-xs text-gray-400 mt-1">
                Chat with your avatar to start one
              </p>
            </div>
          ) : (
            <>
              {/* Active missions first */}
              {activeMissions.length > 0 && (
                <div className="space-y-2">
                  <span className="text-[10px] uppercase tracking-wider text-gray-400 font-medium px-1">
                    Active
                  </span>
                  {activeMissions.map(mission => (
                    <MissionTimelineItem
                      key={mission.id}
                      mission={mission}
                      isSelected={selectedMission?.id === mission.id}
                      onClick={() => onSelectMission(mission)}
                      onResume={onResumeMission}
                    />
                  ))}
                </div>
              )}
              
              {/* Completed missions */}
              {completedMissions.length > 0 && (
                <div className="space-y-2">
                  <span className="text-[10px] uppercase tracking-wider text-gray-400 font-medium px-1">
                    Completed
                  </span>
                  {completedMissions.map(mission => (
                    <MissionTimelineItem
                      key={mission.id}
                      mission={mission}
                      isSelected={selectedMission?.id === mission.id}
                      onClick={() => onSelectMission(mission)}
                      onReplay={onReplayMission}
                    />
                  ))}
                </div>
              )}
              
              {/* Other missions */}
              {otherMissions.length > 0 && (
                <div className="space-y-2">
                  <span className="text-[10px] uppercase tracking-wider text-gray-400 font-medium px-1">
                    Other
                  </span>
                  {otherMissions.map(mission => (
                    <MissionTimelineItem
                      key={mission.id}
                      mission={mission}
                      isSelected={selectedMission?.id === mission.id}
                      onClick={() => onSelectMission(mission)}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};

export default MissionTimeline;

