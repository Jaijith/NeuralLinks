/**
 * EditMayaProfileDialog - Professional, immersive-aware Edit Maya Profile dialog
 * 
 * Replaces the duplicated inline dialogs in ProfilePageFull.jsx with a single,
 * well-styled component that adapts to both classic and immersive view modes.
 * 
 * Since Dialog renders via Portal (outside the page wrapper DOM), all immersive
 * styles must be applied explicitly — the ImmersivePageWrapper CSS won't reach it.
 */

import { useState, useEffect, useCallback } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Sparkles, Edit2, User, FileText, Briefcase, MapPin, Image,
  Bot, Zap, Activity, Mic, Shield, ChevronRight, ExternalLink
} from "lucide-react";
import { useInstalledSkills } from "@/features/marketplace/hooks/useInstalledSkills";
import { useSkillInstall } from "@/features/marketplace/hooks/useSkillInstall";
import { getIcon } from "@/features/marketplace/components/SkillCard";

// ── Sub-components rendered inside the dialog ──────────────────────────

const AvatarActivityLog = ({ isImmersive }) => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

  useState(() => {
    const fetchActivities = async () => {
      try {
        const axios = (await import("axios")).default;
        const response = await axios.get(`${BACKEND_URL}/api/avatar/activity?limit=20`, {
          withCredentials: true,
        });
        setActivities(response.data.activities || []);
      } catch (error) {
        console.error('Failed to fetch activities:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchActivities();
  }, []);

  const bg = isImmersive ? 'rgba(30, 35, 55, 0.8)' : 'white';
  const border = isImmersive ? 'rgba(71, 85, 105, 0.4)' : undefined;
  const textPrimary = isImmersive ? '#e2e8f0' : '#1e293b';
  const textMuted = isImmersive ? '#94a3b8' : '#64748b';

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-3 border-purple-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  
  if (activities.length === 0) {
    return (
      <div className="text-center py-12">
        <Activity className="w-12 h-12 mx-auto mb-3" style={{ color: textMuted }} />
        <p style={{ color: textMuted }} className="text-sm">
          No activities yet. Enable autonomy to see your avatar in action!
        </p>
      </div>
    );
  }

  const getActivityIcon = (type) => {
    switch (type) {
      case 'post': return { icon: '📝', color: isImmersive ? '#60a5fa' : '#2563eb' };
      case 'comment': return { icon: '💬', color: isImmersive ? '#34d399' : '#16a34a' };
      case 'like': return { icon: '❤️', color: isImmersive ? '#f87171' : '#dc2626' };
      default: return { icon: '🤖', color: isImmersive ? '#fbbf24' : '#d97706' };
    }
  };

  return (
    <div className="space-y-2 max-h-80 overflow-y-auto pr-1 custom-scrollbar">
      {activities.map((activity, idx) => {
        const { icon } = getActivityIcon(activity.action_type);
        return (
          <div 
            key={idx} 
            className="flex items-start gap-3 p-3 rounded-xl transition-colors"
            style={{ 
              backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.6)' : '#f8fafc',
              border: `1px solid ${isImmersive ? 'rgba(71, 85, 105, 0.3)' : '#e2e8f0'}`
            }}
          >
            <span className="text-lg mt-0.5 flex-shrink-0">{icon}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate" style={{ color: textPrimary }}>
                {activity.description}
              </p>
              <p className="text-xs mt-0.5" style={{ color: textMuted }}>
                {new Date(activity.timestamp).toLocaleString()}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const AvatarStatusPanel = ({ isImmersive }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

  useState(() => {
    const fetchStatus = async () => {
      try {
        const axios = (await import("axios")).default;
        const response = await axios.get(`${BACKEND_URL}/api/avatar/status`, {
          withCredentials: true,
        });
        setStatus(response.data);
      } catch (error) {
        console.error('Failed to fetch status:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
  }, []);

  const textPrimary = isImmersive ? '#e2e8f0' : '#1e293b';
  const textMuted = isImmersive ? '#94a3b8' : '#64748b';
  const cardBg = isImmersive ? 'rgba(30, 35, 55, 0.6)' : '#f8fafc';
  const borderColor = isImmersive ? 'rgba(71, 85, 105, 0.3)' : '#e2e8f0';

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-3 border-purple-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  
  if (!status) {
    return (
      <div className="text-center py-12">
        <Zap className="w-12 h-12 mx-auto mb-3" style={{ color: textMuted }} />
        <p style={{ color: textMuted }} className="text-sm">Status unavailable</p>
      </div>
    );
  }

  const StatusRow = ({ label, value }) => (
    <div className="flex justify-between items-center py-2">
      <span className="text-sm" style={{ color: textMuted }}>{label}</span>
      <span className="text-sm font-medium" style={{ color: textPrimary }}>{value}</span>
    </div>
  );

  return (
    <div className="space-y-4">
      <div 
        className="rounded-xl p-4"
        style={{ backgroundColor: cardBg, border: `1px solid ${borderColor}` }}
      >
        <h4 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: textPrimary }}>
          <Bot className="w-4 h-4" style={{ color: isImmersive ? '#a78bfa' : '#7c3aed' }} />
          Configuration
        </h4>
        <div className="divide-y" style={{ borderColor }}>
          <StatusRow label="Status" value={status.is_autonomous ? 'Active' : 'Inactive'} />
          <StatusRow label="Personality" value={status.archetype || 'Not set'} />
          <StatusRow label="Activity Level" value={status.activity_level || 'Medium'} />
        </div>
      </div>
      
      <div 
        className="rounded-xl p-4"
        style={{ backgroundColor: cardBg, border: `1px solid ${borderColor}` }}
      >
        <h4 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: textPrimary }}>
          <Activity className="w-4 h-4" style={{ color: isImmersive ? '#a78bfa' : '#7c3aed' }} />
          Recent Performance
        </h4>
        <div className="divide-y" style={{ borderColor }}>
          <StatusRow 
            label="Last Activity" 
            value={status.last_activity ? new Date(status.last_activity).toLocaleString() : 'Never'} 
          />
          <StatusRow label="Actions (Last Hour)" value={status.actions_last_hour || 0} />
        </div>
      </div>

      {!status.has_avatar && (
        <div 
          className="rounded-xl p-4 text-center"
          style={{ 
            backgroundColor: isImmersive ? 'rgba(120, 80, 20, 0.2)' : '#fefce8',
            border: `1px solid ${isImmersive ? 'rgba(161, 130, 50, 0.3)' : '#fde68a'}`
          }}
        >
          <p className="text-sm" style={{ color: isImmersive ? '#fbbf24' : '#92400e' }}>
            Avatar profile not yet configured
          </p>
        </div>
      )}
    </div>
  );
};

// ── Voice Settings Panel ──────────────────────────

const VoiceSettingsPanelDialog = ({ isImmersive }) => {
  const [settings, setSettings] = useState({
    preset: 'default',
    noise_threshold: 0.5,
    response_speed: 'balanced',
    prefer_shorter_responses: false,
    enable_transcription: true
  });
  const [presets, setPresets] = useState(['default']);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);

  const presetDescriptions = {
    default: 'Balanced settings for most environments',
    low_latency: 'Fast response time for natural conversations',
    ultra_low_latency: 'Fastest possible - may be sensitive to noise',
    quiet_environment: 'Higher sensitivity for quiet rooms',
    noisy_environment: 'Filters background noise better',
    push_to_talk: 'Manual control - hold to speak'
  };

  const textPrimary = isImmersive ? '#e2e8f0' : '#1e293b';
  const textMuted = isImmersive ? '#94a3b8' : '#64748b';
  const cardBg = isImmersive ? 'rgba(30, 35, 55, 0.6)' : '#f8fafc';
  const borderColor = isImmersive ? 'rgba(71, 85, 105, 0.3)' : '#e2e8f0';

  useState(() => {
    const loadSettings = async () => {
      try {
        const { getVoiceSettings } = await import("@/services/api/voiceService");
        const data = await getVoiceSettings();
        if (data.success) {
          setSettings(prev => ({ ...prev, ...data.settings }));
          setPresets(data.presets || ['default']);
        }
      } catch (err) {
        console.error('Error loading voice settings:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadSettings();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus(null);
    try {
      const { updateVoiceSettings } = await import("@/services/api/voiceService");
      const { toast } = await import("sonner");
      const result = await updateVoiceSettings({
        preset: settings.preset,
        custom: {
          noise_threshold: settings.noise_threshold,
          response_speed: settings.response_speed,
          prefer_shorter_responses: settings.prefer_shorter_responses,
          enable_transcription: settings.enable_transcription
        }
      });
      if (result.success) {
        setSaveStatus('saved');
        toast.success('Voice settings saved');
        setTimeout(() => setSaveStatus(null), 2000);
      } else {
        setSaveStatus('error');
        toast.error('Failed to save voice settings');
      }
    } catch (err) {
      console.error('Error saving voice settings:', err);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-3 border-purple-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Presets */}
      <div>
        <label className="block text-sm font-semibold mb-3" style={{ color: textPrimary }}>
          Environment Preset
        </label>
        <div className="grid grid-cols-1 gap-2">
          {presets.map((preset) => (
            <button
              key={preset}
              onClick={() => setSettings(prev => ({ ...prev, preset }))}
              className="p-3 rounded-xl text-left transition-all"
              style={{
                backgroundColor: settings.preset === preset
                  ? (isImmersive ? 'rgba(139, 92, 246, 0.15)' : '#f5f3ff')
                  : cardBg,
                border: `1px solid ${settings.preset === preset 
                  ? (isImmersive ? 'rgba(139, 92, 246, 0.5)' : '#8b5cf6') 
                  : borderColor}`,
              }}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium capitalize" style={{ color: textPrimary }}>
                  {preset.replace(/_/g, ' ')}
                </span>
                {settings.preset === preset && (
                  <span style={{ color: isImmersive ? '#a78bfa' : '#7c3aed' }}>✓</span>
                )}
              </div>
              <p className="text-xs mt-1" style={{ color: textMuted }}>
                {presetDescriptions[preset] || 'Custom preset'}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Response Speed */}
      <div>
        <label className="block text-sm font-semibold mb-2" style={{ color: textPrimary }}>
          Response Speed
        </label>
        <div className="flex gap-2">
          {['quick', 'balanced', 'thoughtful'].map((speed) => (
            <button
              key={speed}
              onClick={() => setSettings(prev => ({ ...prev, response_speed: speed }))}
              className="flex-1 py-2.5 px-3 rounded-xl text-sm font-medium transition-all"
              style={{
                backgroundColor: settings.response_speed === speed
                  ? (isImmersive ? 'rgba(139, 92, 246, 0.15)' : '#f5f3ff')
                  : cardBg,
                border: `1px solid ${settings.response_speed === speed 
                  ? (isImmersive ? 'rgba(139, 92, 246, 0.5)' : '#8b5cf6') 
                  : borderColor}`,
                color: settings.response_speed === speed 
                  ? (isImmersive ? '#c4b5fd' : '#7c3aed') 
                  : textMuted
              }}
            >
              {speed.charAt(0).toUpperCase() + speed.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Toggle options */}
      <div className="space-y-3">
        {[
          { key: 'prefer_shorter_responses', label: 'Prefer shorter responses', desc: 'More concise answers from Maya' },
          { key: 'enable_transcription', label: 'Show transcription', desc: 'Display text of conversation' },
        ].map((option) => (
          <div 
            key={option.key}
            className="flex items-center justify-between p-3.5 rounded-xl"
            style={{ backgroundColor: cardBg, border: `1px solid ${borderColor}` }}
          >
            <div>
              <p className="text-sm font-medium" style={{ color: textPrimary }}>{option.label}</p>
              <p className="text-xs mt-0.5" style={{ color: textMuted }}>{option.desc}</p>
            </div>
            <Switch
              checked={settings[option.key]}
              onCheckedChange={(checked) => setSettings(prev => ({ ...prev, [option.key]: checked }))}
            />
          </div>
        ))}
      </div>

      {/* Save */}
      <Button 
        onClick={handleSave} 
        disabled={isSaving}
        className="w-full bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white font-medium py-2.5 rounded-xl"
      >
        {isSaving ? 'Saving...' : 'Save Voice Settings'}
      </Button>
      {saveStatus === 'saved' && (
        <p className="text-sm text-center" style={{ color: isImmersive ? '#34d399' : '#16a34a' }}>
          Settings saved successfully
        </p>
      )}
    </div>
  );
};

// ── Fallback action list (used if marketplace is not available) ──────────

const FALLBACK_AVATAR_ACTIONS = [
  { key: 'like_posts', label: 'Like Posts', icon: 'heart', desc: 'Like posts from friends' },
  { key: 'comment_posts', label: 'Comment on Posts', icon: 'message-circle', desc: 'Comment on posts from friends' },
  { key: 'create_posts', label: 'Create Posts', icon: 'pen-tool', desc: 'Create and publish new posts' },
  { key: 'send_friend_requests', label: 'Send Friend Requests', icon: 'user-plus', desc: 'Send friend requests to other avatars' },
  { key: 'accept_friend_requests', label: 'Accept Friend Requests', icon: 'user-check', desc: 'Accept incoming friend requests' },
  { key: 'message_friends', label: 'Message Friends', icon: 'mail', desc: 'Send messages to friends' },
  { key: 'discover_profiles', label: 'Discover Profiles', icon: 'compass', desc: 'Browse and view other profiles' },
  { key: 'read_messages', label: 'Read Messages', icon: 'inbox', desc: 'Read and mark messages as read' },
  { key: 'browse_feed', label: 'Browse Feed', icon: 'rss', desc: 'Browse posts from friends and network' },
  { key: 'get_friend_activities', label: 'Track Friend Activities', icon: 'activity', desc: 'Get updates on friend posts' },
  { key: 'get_trending_topics', label: 'Follow Trending Topics', icon: 'trending-up', desc: 'Get news and trending topics' },
  { key: 'share_posts', label: 'Share Posts', icon: 'share-2', desc: 'Share posts (coming soon)' }
];

// ── Installed Skills Section (synced with Siddhi Bazaar) ──────────

const InstalledSkillsSection = ({ editData, setEditData, isImmersive, t }) => {
  const { installedSkills, loading } = useInstalledSkills();
  const { toggleSkill, toggling } = useSkillInstall();
  const hasMarketplace = !loading && installedSkills.length > 0;

  const actions = hasMarketplace
    ? installedSkills.map((s) => ({
        key: s.permission_key || s.slug,
        label: s.name,
        desc: s.tagline || s.description?.slice(0, 60) || '',
        icon: s.icon || 'box',
        color: s.color || '#6366f1',
        enabled: s.enabled,
        skill_id: s.skill_id,
        slug: s.slug,
        type: s.type,
        fromMarketplace: true,
      }))
    : FALLBACK_AVATAR_ACTIONS.map((a) => ({
        ...a,
        color: '#6366f1',
        enabled: editData.avatar_actions_enabled?.[a.key] ?? true,
        fromMarketplace: false,
      }));

  const handleToggle = async (action, checked) => {
    if (action.fromMarketplace && action.skill_id) {
      try {
        await toggleSkill(action.skill_id, checked);
      } catch (err) {
        console.error('Toggle failed:', err);
      }
    } else {
      setEditData({
        ...editData,
        avatar_actions_enabled: {
          ...editData.avatar_actions_enabled,
          [action.key]: checked,
        },
      });
    }
  };

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ border: `1px solid ${t.cardBorder}` }}
    >
      <div
        className="px-4 py-3 flex items-center gap-2"
        style={{
          backgroundColor: isImmersive ? 'rgba(20, 25, 45, 0.6)' : '#f1f5f9',
          borderBottom: `1px solid ${t.cardBorder}`,
        }}
      >
        <Shield className="w-4 h-4" style={{ color: t.accentPurple }} />
        <h4 className="text-sm font-semibold" style={{ color: t.text }}>
          Installed Skills
        </h4>
        {hasMarketplace && (
          <Badge variant="outline" className="text-[10px] ml-1 px-1.5 py-0 border-purple-200 text-purple-600">
            Siddhi Bazaar
          </Badge>
        )}
        <span className="text-xs ml-auto" style={{ color: t.textMuted }}>
          {actions.length} skills
        </span>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="w-5 h-5 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div
          className="divide-y max-h-72 overflow-y-auto"
          style={{ borderColor: t.sectionBorder }}
        >
          {actions.map((action) => {
            const IconComp = action.fromMarketplace ? getIcon(action.icon) : getIcon(action.icon);
            return (
              <div
                key={action.key || action.slug}
                className="flex items-center justify-between px-4 py-3 transition-colors"
                style={{ backgroundColor: 'transparent' }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = t.cardHoverBg)}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <span className="flex-shrink-0" style={{ color: action.color || t.accentPurple }}>
                    <IconComp className="w-4 h-4" />
                  </span>
                  <div className="min-w-0">
                    <label
                      className="text-sm font-medium cursor-pointer block truncate"
                      style={{ color: t.text }}
                    >
                      {action.label}
                      {action.type === 'workflow_engine' && (
                        <Badge variant="outline" className="text-[9px] ml-1.5 px-1 py-0 border-purple-200 text-purple-600">Engine</Badge>
                      )}
                    </label>
                    <p className="text-xs truncate" style={{ color: t.textMuted }}>
                      {action.desc}
                    </p>
                  </div>
                </div>
                <Switch
                  checked={action.enabled}
                  onCheckedChange={(checked) => handleToggle(action, checked)}
                  disabled={!editData.avatar_autonomous || toggling === action.skill_id}
                />
              </div>
            );
          })}
        </div>
      )}

      {hasMarketplace && (
        <div
          className="px-4 py-2.5 flex items-center justify-between"
          style={{
            backgroundColor: isImmersive ? 'rgba(20, 25, 45, 0.4)' : '#faf5ff',
            borderTop: `1px solid ${t.cardBorder}`,
          }}
        >
          <p className="text-xs" style={{ color: t.textMuted }}>
            Manage skills in Siddhi Bazaar
          </p>
          <a
            href="/settings?tab=siddhi"
            className="text-xs flex items-center gap-1 hover:underline"
            style={{ color: t.accentPurple }}
          >
            Open Bazaar <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      )}

      {!editData.avatar_autonomous && (
        <div
          className="px-4 py-3 text-center"
          style={{
            backgroundColor: isImmersive ? 'rgba(20, 25, 45, 0.4)' : '#fefce8',
            borderTop: `1px solid ${t.cardBorder}`,
          }}
        >
          <p className="text-xs" style={{ color: t.textMuted }}>
            Enable autonomy above to configure individual actions
          </p>
        </div>
      )}
    </div>
  );
};

// ── Main Dialog Component ──────────────────────────

const EditMayaProfileDialog = ({
  open,
  onOpenChange,
  editData,
  setEditData,
  onSave,
  isImmersive = false,
  triggerVariant = 'default', // 'default' | 'compact'
  triggerElement = null,      // custom trigger element
}) => {
  // Theme tokens
  const t = {
    dialogBg: isImmersive ? 'rgba(10, 15, 30, 0.98)' : '#ffffff',
    dialogBorder: isImmersive ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0',
    headerBg: isImmersive 
      ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.12), rgba(236, 72, 153, 0.08))' 
      : 'linear-gradient(135deg, #faf5ff, #fdf2f8)',
    text: isImmersive ? '#e2e8f0' : '#1e293b',
    textMuted: isImmersive ? '#94a3b8' : '#64748b',
    textSubtle: isImmersive ? '#64748b' : '#94a3b8',
    labelColor: isImmersive ? '#cbd5e1' : '#374151',
    inputBg: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff',
    inputBorder: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#d1d5db',
    inputText: isImmersive ? '#e2e8f0' : '#1e293b',
    inputPlaceholder: isImmersive ? '#64748b' : '#9ca3af',
    cardBg: isImmersive ? 'rgba(30, 35, 55, 0.6)' : '#f8fafc',
    cardBorder: isImmersive ? 'rgba(71, 85, 105, 0.3)' : '#e2e8f0',
    cardHoverBg: isImmersive ? 'rgba(40, 45, 65, 0.7)' : '#f1f5f9',
    tabsBg: isImmersive ? 'rgba(20, 25, 45, 0.8)' : undefined,
    tabActiveBg: isImmersive ? 'rgba(139, 92, 246, 0.2)' : undefined,
    tabActiveText: isImmersive ? '#c4b5fd' : undefined,
    accentPurple: isImmersive ? '#a78bfa' : '#7c3aed',
    sectionBorder: isImmersive ? 'rgba(71, 85, 105, 0.2)' : '#f1f5f9',
  };

  // Styled input props
  const inputStyle = {
    backgroundColor: t.inputBg,
    borderColor: t.inputBorder,
    color: t.inputText,
  };

  // Field component for consistency
  const FormField = ({ icon: Icon, label, hint, children }) => (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm font-semibold" style={{ color: t.labelColor }}>
        {Icon && <Icon className="w-4 h-4" style={{ color: t.accentPurple }} />}
        {label}
      </label>
      {children}
      {hint && (
        <p className="text-xs" style={{ color: t.textSubtle }}>{hint}</p>
      )}
    </div>
  );

  const defaultTrigger = triggerVariant === 'compact' ? (
    <Button size="sm" className="bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:from-pink-600 hover:to-purple-700 text-xs h-8 px-2.5">
      <Edit2 className="w-3 h-3 mr-1" />
      Edit
    </Button>
  ) : (
    <Button size="sm" className="bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:from-pink-600 hover:to-purple-700 text-xs h-8 sm:h-9 px-2 sm:px-3 sm:text-sm">
      <Sparkles className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
      <span className="hidden sm:inline">Edit Maya</span>
      <span className="sm:hidden">Maya</span>
    </Button>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        {triggerElement || defaultTrigger}
      </DialogTrigger>
      <DialogContent 
        className="max-w-3xl max-h-[85vh] overflow-y-auto rounded-2xl p-0 border"
        style={{ 
          backgroundColor: t.dialogBg, 
          borderColor: t.dialogBorder,
          boxShadow: isImmersive 
            ? '0 25px 60px rgba(0, 0, 0, 0.6), 0 0 80px rgba(139, 92, 246, 0.08)' 
            : '0 25px 50px -12px rgba(0, 0, 0, 0.15)',
        }}
      >
        {/* Header */}
        <div 
          className="px-6 pt-6 pb-4 rounded-t-2xl"
          style={{ background: t.headerBg }}
        >
          <DialogHeader>
            <DialogTitle 
              className="text-xl font-bold flex items-center gap-2.5"
              style={{ color: t.text }}
            >
              <div 
                className="p-2 rounded-xl"
                style={{ 
                  background: isImmersive 
                    ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(236, 72, 153, 0.15))' 
                    : 'linear-gradient(135deg, #ede9fe, #fce7f3)' 
                }}
              >
                <Sparkles className="w-5 h-5" style={{ color: t.accentPurple }} />
              </div>
              Edit Maya Profile
            </DialogTitle>
            <p className="text-sm mt-1 ml-12" style={{ color: t.textMuted }}>
              Customize your avatar's identity, autonomy, and voice
            </p>
          </DialogHeader>
        </div>

        {/* Tabs */}
        <div className="px-4 sm:px-6 pb-6">
          <Tabs defaultValue="profile" className="w-full">
            <TabsList 
              className="flex sm:grid sm:grid-cols-5 w-full mb-6 h-11 rounded-xl p-1 overflow-x-auto gap-0.5 sm:gap-0"
              style={{ 
                backgroundColor: isImmersive ? 'rgba(20, 25, 45, 0.8)' : undefined,
                scrollbarWidth: 'none',
                msOverflowStyle: 'none',
                WebkitOverflowScrolling: 'touch',
              }}
            >
              {[
                { value: 'profile', icon: User, label: 'Profile' },
                { value: 'autonomy', icon: Bot, label: 'Auto' },
                { value: 'activity', icon: Activity, label: 'Activity' },
                { value: 'status', icon: Zap, label: 'Status' },
                { value: 'voice', icon: Mic, label: 'Voice' },
              ].map(tab => (
                <TabsTrigger 
                  key={tab.value}
                  value={tab.value} 
                  className="flex-shrink-0 flex items-center justify-center gap-1 text-[11px] sm:text-sm rounded-lg data-[state=active]:shadow-sm transition-all min-w-0 px-2 sm:px-3"
                  style={{
                    color: t.textMuted,
                    touchAction: 'manipulation',
                    WebkitTapHighlightColor: 'transparent',
                    minHeight: '36px',
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <tab.icon className="w-3.5 h-3.5 hidden sm:block flex-shrink-0" />
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>

            {/* ─── PROFILE TAB ─── */}
            <TabsContent value="profile" className="space-y-5 mt-0">
              <FormField icon={User} label="Avatar Nickname">
                <Input
                  value={editData.name}
                  onChange={(e) => setEditData({...editData, name: e.target.value})}
                  placeholder="Your avatar's nickname (e.g., 'Phoenix', 'Shadow')"
                  className="rounded-xl h-11"
                  style={inputStyle}
                />
              </FormField>

              <FormField icon={FileText} label="Avatar Bio">
                <Textarea
                  value={editData.bio}
                  onChange={(e) => setEditData({...editData, bio: e.target.value})}
                  placeholder="Your avatar's story..."
                  rows={3}
                  className="rounded-xl resize-none"
                  style={inputStyle}
                />
              </FormField>

              <FormField 
                icon={Image} 
                label="Avatar Image URL"
                hint="Try: https://api.dicebear.com/7.x/adventurer/svg?seed=YourName"
              >
                <Input
                  value={editData.picture}
                  onChange={(e) => setEditData({...editData, picture: e.target.value})}
                  placeholder="https://api.dicebear.com/7.x/adventurer/svg?seed=YourName"
                  className="rounded-xl h-11"
                  style={inputStyle}
                />
              </FormField>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FormField icon={Briefcase} label="Job Title">
                  <Input
                    value={editData.job_title}
                    onChange={(e) => setEditData({...editData, job_title: e.target.value})}
                    placeholder="Digital Warrior, Dream Architect..."
                    className="rounded-xl h-11"
                    style={inputStyle}
                  />
                </FormField>
                <FormField icon={MapPin} label="Location">
                  <Input
                    value={editData.location}
                    onChange={(e) => setEditData({...editData, location: e.target.value})}
                    placeholder="Virtual Realm, Cyberspace..."
                    className="rounded-xl h-11"
                    style={inputStyle}
                  />
                </FormField>
              </div>

              <Button 
                onClick={onSave} 
                className="w-full bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white font-medium py-2.5 rounded-xl mt-2"
              >
                Save Profile
              </Button>
            </TabsContent>

            {/* ─── AUTONOMY TAB ─── */}
            <TabsContent value="autonomy" className="space-y-5 mt-0">
              {/* Autonomy Toggle - Hero Card */}
              <div 
                className="rounded-xl p-5"
                style={{ 
                  background: isImmersive 
                    ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.08))' 
                    : 'linear-gradient(135deg, #faf5ff, #eff6ff)',
                  border: `1px solid ${isImmersive ? 'rgba(139, 92, 246, 0.2)' : '#e9d5ff'}` 
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div 
                      className="p-2.5 rounded-xl" 
                      style={{ 
                        background: isImmersive 
                          ? 'rgba(139, 92, 246, 0.2)' 
                          : '#ede9fe' 
                      }}
                    >
                      <Bot className="w-5 h-5" style={{ color: t.accentPurple }} />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold" style={{ color: t.text }}>
                        Enable Autonomy
                      </label>
                      <p className="text-xs mt-0.5" style={{ color: t.textMuted }}>
                        Let your avatar act independently
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={editData.avatar_autonomous || false}
                    onCheckedChange={(checked) => setEditData({...editData, avatar_autonomous: checked})}
                  />
                </div>
              </div>

              {/* Activity Level & Archetype */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FormField icon={Activity} label="Activity Level">
                  <Select
                    value={editData.avatar_activity_level || 'medium'}
                    onValueChange={(value) => setEditData({...editData, avatar_activity_level: value})}
                  >
                    <SelectTrigger 
                      className="rounded-xl h-11"
                      style={inputStyle}
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent 
                      style={{ 
                        backgroundColor: isImmersive ? 'rgb(20, 25, 45)' : undefined,
                        borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : undefined,
                      }}
                    >
                      <SelectItem value="hypo">Hypo (Testing)</SelectItem>
                      <SelectItem value="low">Low (1-2/day)</SelectItem>
                      <SelectItem value="medium">Medium (5-10/day)</SelectItem>
                      <SelectItem value="high">High (15-20/day)</SelectItem>
                    </SelectContent>
                  </Select>
                </FormField>

                <FormField icon={Shield} label="Personality">
                  <Select
                    value={editData.archetype || 'casual_observer'}
                    onValueChange={(value) => setEditData({...editData, archetype: value})}
                  >
                    <SelectTrigger 
                      className="rounded-xl h-11"
                      style={inputStyle}
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent 
                      style={{ 
                        backgroundColor: isImmersive ? 'rgb(20, 25, 45)' : undefined,
                        borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : undefined,
                      }}
                    >
                      <SelectItem value="social_butterfly">Social Butterfly</SelectItem>
                      <SelectItem value="thoughtful_contributor">Thoughtful Contributor</SelectItem>
                      <SelectItem value="casual_observer">Casual Observer</SelectItem>
                      <SelectItem value="niche_expert">Niche Expert</SelectItem>
                      <SelectItem value="enthusiastic_newcomer">Enthusiastic Newcomer</SelectItem>
                    </SelectContent>
                  </Select>
                </FormField>
              </div>

              {/* Installed Skills (from Siddhi Bazaar) */}
              <InstalledSkillsSection
                editData={editData}
                setEditData={setEditData}
                isImmersive={isImmersive}
                t={t}
              />

              <Button 
                onClick={onSave} 
                className="w-full bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white font-medium py-2.5 rounded-xl"
              >
                Save Autonomy Settings
              </Button>
            </TabsContent>

            {/* ─── ACTIVITY TAB ─── */}
            <TabsContent value="activity" className="mt-0">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5" style={{ color: t.accentPurple }} />
                <h3 className="text-lg font-semibold" style={{ color: t.text }}>Recent Activity</h3>
              </div>
              <AvatarActivityLog isImmersive={isImmersive} />
            </TabsContent>

            {/* ─── STATUS TAB ─── */}
            <TabsContent value="status" className="mt-0">
              <div className="flex items-center gap-2 mb-4">
                <Zap className="w-5 h-5" style={{ color: t.accentPurple }} />
                <h3 className="text-lg font-semibold" style={{ color: t.text }}>Avatar Status</h3>
              </div>
              <AvatarStatusPanel isImmersive={isImmersive} />
            </TabsContent>

            {/* ─── VOICE TAB ─── */}
            <TabsContent value="voice" className="mt-0">
              <div className="flex items-center gap-2 mb-4">
                <Mic className="w-5 h-5" style={{ color: t.accentPurple }} />
                <h3 className="text-lg font-semibold" style={{ color: t.text }}>Voice Settings</h3>
              </div>
              <VoiceSettingsPanelDialog isImmersive={isImmersive} />
            </TabsContent>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default EditMayaProfileDialog;
