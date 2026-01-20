import React from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Sparkles, Heart, Brain, Target, TrendingUp, MessageCircle } from 'lucide-react';

/**
 * BondingResponse - Main container for bonding workflow responses
 * Displays cards, metrics, and interactive elements from bonding conversations
 */
const BondingResponse = ({ response, onFeedback }) => {
  if (!response || !response.cards) {
    return null;
  }

  const { cards, detected_intent, bonding_mode, metrics, session_id } = response;

  // Card type to icon mapping
  const getCardIcon = (type) => {
    const icons = {
      warm_presence: Heart,
      recap: MessageCircle,
      serendipity: Sparkles,
      reflection: Brain,
      growth: TrendingUp,
      guidance: Target,
      micro_mission: Target,
      celebration: Sparkles
    };
    return icons[type] || MessageCircle;
  };

  // Card type to color mapping
  const getCardColor = (type) => {
    const colors = {
      warm_presence: 'from-pink-500/20 to-rose-500/20 border-pink-500/30',
      recap: 'from-blue-500/20 to-cyan-500/20 border-blue-500/30',
      serendipity: 'from-purple-500/20 to-fuchsia-500/20 border-purple-500/30',
      reflection: 'from-indigo-500/20 to-blue-500/20 border-indigo-500/30',
      growth: 'from-green-500/20 to-emerald-500/20 border-green-500/30',
      guidance: 'from-amber-500/20 to-orange-500/20 border-amber-500/30',
      micro_mission: 'from-teal-500/20 to-cyan-500/20 border-teal-500/30',
      celebration: 'from-yellow-500/20 to-amber-500/20 border-yellow-500/30'
    };
    return colors[type] || 'from-gray-500/20 to-slate-500/20 border-gray-500/30';
  };

  const handleFeedback = (rating, helpful) => {
    if (onFeedback && session_id) {
      onFeedback({
        session_id,
        rating,
        helpful
      });
    }
  };

  return (
    <div className="space-y-4 py-4">
      {/* Intent & Mode Badges */}
      <div className="flex items-center gap-2 flex-wrap">
        {detected_intent && (
          <Badge variant="outline" className="text-xs">
            Intent: {detected_intent.replace('_', ' ')}
          </Badge>
        )}
        {bonding_mode && (
          <Badge variant="outline" className="text-xs bg-purple-500/10 text-purple-400 border-purple-500/30">
            Mode: {bonding_mode.replace('_', ' ')}
          </Badge>
        )}
      </div>

      {/* Cards */}
      <div className="space-y-3">
        {cards.map((card, index) => {
          const Icon = getCardIcon(card.type);
          const colorClass = getCardColor(card.type);

          return (
            <Card
              key={index}
              className={`p-4 bg-gradient-to-br ${colorClass} border backdrop-blur-sm transition-all hover:shadow-lg`}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-1">
                  <Icon className="w-5 h-5 text-white/80" />
                </div>
                <div className="flex-1 space-y-2">
                  <div className="text-sm text-white/90 leading-relaxed">
                    {card.content}
                  </div>
                  
                  {/* Additional card data */}
                  {card.activity && (
                    <div className="text-xs text-white/60 pt-2 border-t border-white/10">
                      {card.activity.action_type && (
                        <span>Action: {card.activity.action_type}</span>
                      )}
                    </div>
                  )}
                  
                  {card.overlap && (
                    <div className="text-xs text-white/70 pt-2 border-t border-white/10">
                      <span className="font-medium">Connection: </span>
                      {card.overlap.description}
                    </div>
                  )}
                  
                  {card.question && (
                    <div className="mt-3 p-3 bg-white/5 rounded-lg border border-white/10">
                      <p className="text-sm text-white/90">{card.question}</p>
                    </div>
                  )}
                  
                  {card.mission && (
                    <div className="mt-3 p-3 bg-white/5 rounded-lg border border-white/10">
                      <p className="text-sm font-medium text-white/90">{card.mission.title}</p>
                      {card.mission.description && (
                        <p className="text-xs text-white/70 mt-1">{card.mission.description}</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Metrics */}
      {metrics && (Object.keys(metrics).length > 0) && (
        <Card className="p-4 bg-gradient-to-br from-slate-800/50 to-slate-900/50 border-slate-700/50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-white/70">Relationship Growth</div>
            <div className="flex items-center gap-4 text-xs">
              {metrics.bond_delta !== undefined && (
                <div className="flex items-center gap-1">
                  <Heart className="w-3 h-3 text-pink-400" />
                  <span className="text-pink-400">
                    {metrics.bond_delta > 0 ? '+' : ''}{(metrics.bond_delta * 100).toFixed(1)}%
                  </span>
                </div>
              )}
              {metrics.trust_delta !== undefined && (
                <div className="flex items-center gap-1">
                  <TrendingUp className="w-3 h-3 text-green-400" />
                  <span className="text-green-400">
                    {metrics.trust_delta > 0 ? '+' : ''}{(metrics.trust_delta * 100).toFixed(1)}%
                  </span>
                </div>
              )}
              {metrics.delight_score !== undefined && (
                <div className="flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-purple-400" />
                  <span className="text-purple-400">
                    {(metrics.delight_score * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Feedback (optional) */}
      {session_id && onFeedback && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            onClick={() => handleFeedback(5, true)}
            className="text-xs text-white/50 hover:text-green-400 transition-colors"
          >
            👍 Helpful
          </button>
          <span className="text-white/30">•</span>
          <button
            onClick={() => handleFeedback(1, false)}
            className="text-xs text-white/50 hover:text-red-400 transition-colors"
          >
            👎 Not helpful
          </button>
        </div>
      )}
    </div>
  );
};

export default BondingResponse;
