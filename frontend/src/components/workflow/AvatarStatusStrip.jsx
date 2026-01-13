/**
 * AvatarStatusStrip Component
 * Persistent status strip showing what the avatar is currently doing
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { 
  Bot, Zap, Search, MessageCircle, Brain, CheckCircle, 
  Loader2, Pause, AlertCircle, Sparkles
} from 'lucide-react';

const AvatarStatusStrip = ({
  avatarName,
  avatarPicture,
  status = 'idle', // idle, thinking, searching, messaging, analyzing, completed
  currentAction = null,
  activeMission = null,
  lastAction = null,
  onlineTime = null,
  className = '',
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'thinking':
        return {
          icon: Brain,
          color: 'text-purple-400',
          bgColor: 'bg-purple-500/20',
          pulse: true,
          label: 'Thinking...',
        };
      case 'searching':
        return {
          icon: Search,
          color: 'text-blue-400',
          bgColor: 'bg-blue-500/20',
          pulse: true,
          label: 'Exploring world...',
        };
      case 'messaging':
        return {
          icon: MessageCircle,
          color: 'text-green-400',
          bgColor: 'bg-green-500/20',
          pulse: true,
          label: 'Engaging...',
        };
      case 'analyzing':
        return {
          icon: Sparkles,
          color: 'text-amber-400',
          bgColor: 'bg-amber-500/20',
          pulse: true,
          label: 'Analyzing signals...',
        };
      case 'completed':
        return {
          icon: CheckCircle,
          color: 'text-green-400',
          bgColor: 'bg-green-500/20',
          pulse: false,
          label: 'Mission complete',
        };
      case 'paused':
        return {
          icon: Pause,
          color: 'text-yellow-400',
          bgColor: 'bg-yellow-500/20',
          pulse: false,
          label: 'Paused',
        };
      case 'error':
        return {
          icon: AlertCircle,
          color: 'text-red-400',
          bgColor: 'bg-red-500/20',
          pulse: false,
          label: 'Error',
        };
      default:
        return {
          icon: Zap,
          color: 'text-slate-400',
          bgColor: 'bg-slate-500/20',
          pulse: false,
          label: 'Online',
        };
    }
  };

  const config = getStatusConfig();
  const StatusIcon = config.icon;

  return (
    <motion.div
      className={`relative flex items-center gap-4 px-4 py-3 rounded-xl border backdrop-blur-sm bg-white/90 shadow-sm ${className}`}
      style={{
        borderColor: 'rgba(168, 85, 247, 0.2)',
      }}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {/* Avatar with status ring */}
      <div className="relative">
        <Avatar className="w-12 h-12 border-2 border-purple-400">
          <AvatarImage src={avatarPicture} />
          <AvatarFallback className="bg-gradient-to-br from-purple-500 to-pink-500 text-white font-bold">
            {avatarName?.charAt(0)?.toUpperCase() || 'A'}
          </AvatarFallback>
        </Avatar>
        
        {/* Status indicator */}
        <motion.div
          className={`absolute -bottom-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center ${config.bgColor} border-2 border-white shadow-sm`}
          animate={config.pulse ? { scale: [1, 1.1, 1] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
        >
          <StatusIcon className={`w-3 h-3 ${config.color}`} />
        </motion.div>
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-gray-800 truncate">{avatarName}</span>
          <Badge 
            variant="outline" 
            className={`text-[10px] uppercase tracking-wider ${config.color} border-current/30`}
          >
            {config.label}
          </Badge>
        </div>
        
        {/* Current action or mission */}
        <div className="flex items-center gap-2 mt-1">
          {currentAction ? (
            <motion.p 
              className="text-sm text-gray-600 truncate"
              key={currentAction}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              {currentAction}
            </motion.p>
          ) : activeMission ? (
            <p className="text-sm text-gray-500 truncate">
              Mission: {activeMission.name}
            </p>
          ) : lastAction ? (
            <p className="text-xs text-gray-400 truncate">
              Last: {lastAction}
            </p>
          ) : (
            <p className="text-xs text-gray-400">
              Waiting for instructions...
            </p>
          )}
        </div>
      </div>

      {/* Activity indicator */}
      <div className="flex flex-col items-end gap-1">
        {activeMission && (
          <div className="flex items-center gap-1">
            {status === 'thinking' || status === 'searching' || status === 'messaging' ? (
              <Loader2 className="w-4 h-4 text-purple-500 animate-spin" />
            ) : (
              <div className="w-2 h-2 rounded-full bg-green-500" />
            )}
            <span className="text-xs text-gray-500">
              {activeMission.progress?.percentage || 0}%
            </span>
          </div>
        )}
        
        {onlineTime && (
          <span className="text-[10px] text-gray-400">
            Online {onlineTime}
          </span>
        )}
      </div>

      {/* Animated background pulse when active */}
      <AnimatePresence>
        {config.pulse && (
          <motion.div
            className="absolute inset-0 rounded-xl pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.05, 0] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2, repeat: Infinity }}
            style={{
              background: `radial-gradient(ellipse at center, ${config.color.replace('text-', 'rgb(').replace('-400', '-500/20)')} 0%, transparent 70%)`,
            }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default AvatarStatusStrip;

