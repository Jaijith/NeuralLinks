/**
 * AgentCard - Display card for AI Agent Assistants in the Siddhi Bazaar
 * Shows agent avatar, domain, bio, and subscribe/toggle controls
 */

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Bot, Sparkles } from 'lucide-react';

const AgentCard = ({
  agentSkill,
  agentUser,
  isSubscribed,
  isEnabled,
  onSubscribe,
  onUnsubscribe,
  onToggle,
  onViewDetail,
  subscribing,
  toggling,
  isImmersive = false,
}) => {
  const cardBg = isImmersive ? 'rgba(30, 35, 55, 0.6)' : '#ffffff';
  const borderColor = isImmersive ? 'rgba(71, 85, 105, 0.3)' : '#e2e8f0';
  const textPrimary = isImmersive ? '#e2e8f0' : '#1e293b';
  const textMuted = isImmersive ? '#94a3b8' : '#64748b';

  const agentName = agentUser?.avatar_name || agentSkill?.name || 'Agent';
  const agentPicture = agentUser?.avatar_picture || '';
  const domainLabel = agentUser?.agent_domain_label || agentSkill?.binding?.agent_domain || '';
  const bio = agentSkill?.description || agentUser?.avatar_bio || '';
  const expertise = agentUser?.agent_expertise || agentSkill?.binding?.agent_expertise || [];
  const color = agentSkill?.color || '#10b981';

  return (
    <div
      className="rounded-xl p-4 cursor-pointer transition-all hover:shadow-md"
      style={{
        backgroundColor: cardBg,
        border: `1px solid ${borderColor}`,
        borderLeft: `3px solid ${color}`,
      }}
      onClick={() => onViewDetail && onViewDetail(agentSkill)}
    >
      <div className="flex items-start gap-3">
        {/* Agent Avatar */}
        <div className="relative flex-shrink-0">
          {agentPicture ? (
            <img
              src={agentPicture}
              alt={agentName}
              className="w-11 h-11 rounded-full object-cover"
              style={{ border: `2px solid ${color}` }}
            />
          ) : (
            <div
              className="w-11 h-11 rounded-full flex items-center justify-center"
              style={{ backgroundColor: `${color}20`, border: `2px solid ${color}` }}
            >
              <Bot className="w-5 h-5" style={{ color }} />
            </div>
          )}
          {/* AI Badge */}
          <div
            className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full flex items-center justify-center"
            style={{ backgroundColor: color }}
          >
            <Sparkles className="w-2.5 h-2.5 text-white" />
          </div>
        </div>

        {/* Agent Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h4 className="text-sm font-semibold truncate" style={{ color: textPrimary }}>
              {agentName}
            </h4>
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0"
              style={{
                backgroundColor: `${color}15`,
                borderColor: `${color}40`,
                color,
              }}
            >
              {domainLabel}
            </Badge>
          </div>
          <p className="text-xs line-clamp-2 mb-1" style={{ color: textMuted }}>
            {bio}
          </p>
          {expertise.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {expertise.slice(0, 3).map((exp, i) => (
                <span
                  key={i}
                  className="text-[9px] px-1.5 py-0.5 rounded-full"
                  style={{
                    backgroundColor: isImmersive ? 'rgba(71, 85, 105, 0.3)' : '#f1f5f9',
                    color: textMuted,
                  }}
                >
                  {exp}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          {isSubscribed ? (
            <Switch
              checked={isEnabled}
              onCheckedChange={(v) => onToggle && onToggle(agentSkill, v)}
              disabled={toggling === agentSkill?.id}
            />
          ) : (
            <Button
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onSubscribe && onSubscribe(agentSkill);
              }}
              disabled={subscribing === agentSkill?.id}
              className="h-7 px-3 text-xs text-white"
              style={{
                background: `linear-gradient(135deg, ${color}, ${color}cc)`,
              }}
            >
              {subscribing === agentSkill?.id ? 'Hiring...' : 'Hire'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentCard;
