import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Heart, MessageCircle, Share2, PenTool, Newspaper, Image, UserPlus, UserCheck, Mail, Inbox, Compass, Rss, Globe, Activity, TrendingUp, Search, Tag, Filter, BarChart, Brain, Send, MessageSquarePlus, Bell, FileText, Save, Eye, Loader, Network, Database, Megaphone, Link, Crown, Sparkles, Map, Palette, Package, Target, HeartHandshake, Cpu, Plane, Music, Film, Gamepad2, BookOpen, Shirt, Dumbbell, UtensilsCrossed, Waves, Footprints, Telescope, HeartPulse, Bot, Brush } from 'lucide-react';

const ICON_MAP = {
  'heart': Heart, 'message-circle': MessageCircle, 'share-2': Share2,
  'pen-tool': PenTool, 'newspaper': Newspaper, 'image': Image,
  'user-plus': UserPlus, 'user-check': UserCheck, 'mail': Mail,
  'inbox': Inbox, 'compass': Compass, 'rss': Rss, 'globe': Globe,
  'activity': Activity, 'trending-up': TrendingUp, 'search': Search,
  'tag': Tag, 'filter': Filter, 'bar-chart': BarChart, 'brain': Brain,
  'send': Send, 'message-square-plus': MessageSquarePlus, 'bell': Bell,
  'file-text': FileText, 'save': Save, 'eye': Eye, 'loader': Loader,
  'network': Network, 'database': Database, 'megaphone': Megaphone,
  'link': Link, 'crown': Crown, 'sparkles': Sparkles, 'map': Map,
  'palette': Palette, 'package': Package, 'target': Target,
  'heart-handshake': HeartHandshake, 'cog': Loader,
  'user-search': Search, 'user-plus-2': UserPlus,
  'message-square': MessageCircle, 'git-merge': Link,
  'bar-chart-3': BarChart,
  // AI Agent icons
  'cpu': Cpu, 'plane': Plane, 'music': Music, 'film': Film,
  'gamepad-2': Gamepad2, 'book-open': BookOpen, 'shirt': Shirt,
  'dumbbell': Dumbbell, 'utensils': UtensilsCrossed, 'waves': Waves,
  'footprints': Footprints, 'telescope': Telescope,
  'heart-pulse': HeartPulse, 'bot': Bot, 'brush': Brush,
  'pen-line': PenTool, 'chef-hat': UtensilsCrossed, 'lotus': Sparkles,
};

function getIcon(iconName) {
  return ICON_MAP[iconName] || Package;
}

const TIER_COLORS = {
  core: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  standard: 'bg-blue-100 text-blue-700 border-blue-200',
  advanced: 'bg-purple-100 text-purple-700 border-purple-200',
  premium: 'bg-amber-100 text-amber-700 border-amber-200',
};

const SkillCard = ({ skill, isInstalled, isEnabled, onInstall, onToggle, onViewDetail, installing, toggling, isImmersive }) => {
  const IconComponent = getIcon(skill.icon);
  const tierClass = TIER_COLORS[skill.tier] || TIER_COLORS.standard;

  const cardBg = isImmersive ? 'rgba(30, 35, 55, 0.6)' : '#ffffff';
  const borderColor = isImmersive ? 'rgba(71, 85, 105, 0.3)' : '#e2e8f0';
  const textPrimary = isImmersive ? '#e2e8f0' : '#1e293b';
  const textMuted = isImmersive ? '#94a3b8' : '#64748b';

  return (
    <div
      className="rounded-xl p-4 cursor-pointer transition-all hover:shadow-md"
      style={{
        backgroundColor: cardBg,
        border: `1px solid ${borderColor}`,
      }}
      onClick={() => onViewDetail && onViewDetail(skill)}
    >
      <div className="flex items-start gap-3">
        <div
          className="p-2.5 rounded-xl flex-shrink-0"
          style={{ backgroundColor: `${skill.color}15`, border: `1px solid ${skill.color}30` }}
        >
          <IconComponent className="w-5 h-5" style={{ color: skill.color }} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h4 className="text-sm font-semibold truncate" style={{ color: textPrimary }}>
              {skill.name}
            </h4>
            <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${tierClass}`}>
              {skill.tier}
            </Badge>
          </div>
          <p className="text-xs truncate" style={{ color: textMuted }}>
            {skill.tagline}
          </p>

          {skill.stats && skill.stats.total_installs > 0 && (
            <p className="text-[10px] mt-1" style={{ color: textMuted }}>
              {skill.stats.total_installs}+ installs
              {skill.stats.avg_rating > 0 && ` · ★ ${skill.stats.avg_rating}`}
            </p>
          )}
        </div>

        <div className="flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          {isInstalled ? (
            <Switch
              checked={isEnabled}
              onCheckedChange={(v) => onToggle && onToggle(skill, v)}
              disabled={toggling === skill.id}
            />
          ) : (
            <Button
              size="sm"
              onClick={(e) => { e.stopPropagation(); onInstall && onInstall(skill); }}
              disabled={installing === skill.id}
              className="h-7 px-3 text-xs bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:from-pink-600 hover:to-purple-700"
            >
              {installing === skill.id ? 'Installing...' : 'Install'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export { SkillCard, getIcon, TIER_COLORS };
export default SkillCard;
