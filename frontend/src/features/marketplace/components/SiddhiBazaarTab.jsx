/**
 * SiddhiBazaarTab - Main marketplace tab component for Settings page
 * Contains: My Skills, Recommended, Browse by Category, Gateway Health
 */

import { useState, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Sparkles, Search, ChevronDown, ChevronUp, Shield, Activity, CheckCircle, AlertTriangle, XCircle, Package, Bot } from 'lucide-react';
import { toast } from 'sonner';
import SkillCard, { getIcon } from './SkillCard';
import AgentCard from './AgentCard';
import SkillDetailDialog from './SkillDetailDialog';
import { useInstalledSkills } from '../hooks/useInstalledSkills';
import { useMarketplace } from '../hooks/useMarketplace';
import { useSkillInstall } from '../hooks/useSkillInstall';
import { useAgentSubscription } from '../hooks/useAgentSubscription';
import marketplaceService from '@/services/api/marketplaceService';

const SiddhiBazaarTab = ({ user, isImmersive = false }) => {
  const { installedSkills, loading: installedLoading } = useInstalledSkills();
  const { categories, featured, recommended, loading: catalogLoading } = useMarketplace();
  const { installSkill, uninstallSkill, toggleSkill, installing, toggling } = useSkillInstall();
  const {
    agents, subscribedAgents, loading: agentsLoading,
    subscribing, toggling: agentToggling,
    subscribeAgent, unsubscribeAgent, toggleAgent,
    isAgentSubscribed, isAgentEnabled,
  } = useAgentSubscription();

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [expandedCategory, setExpandedCategory] = useState(null);
  const [categorySkills, setCategorySkills] = useState({});
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [gatewayStatus, setGatewayStatus] = useState(null);
  const [showGateway, setShowGateway] = useState(false);

  const textPrimary = isImmersive ? '#e2e8f0' : '#1e293b';
  const textMuted = isImmersive ? '#94a3b8' : '#64748b';
  const cardBg = isImmersive ? 'rgba(30, 35, 55, 0.6)' : '#f8fafc';
  const borderColor = isImmersive ? 'rgba(71, 85, 105, 0.3)' : '#e2e8f0';
  const sectionBg = isImmersive ? 'rgba(20, 25, 45, 0.6)' : '#f1f5f9';
  const accentPurple = isImmersive ? '#a78bfa' : '#7c3aed';

  const installedMap = {};
  installedSkills.forEach((s) => { installedMap[s.slug] = s; installedMap[s.skill_id] = s; });

  const isSkillInstalled = (skill) => !!(installedMap[skill.slug] || installedMap[skill.id]);
  const isSkillEnabled = (skill) => {
    const inst = installedMap[skill.slug] || installedMap[skill.id];
    return inst ? inst.enabled : false;
  };

  const handleInstall = async (skill) => {
    try {
      await installSkill(skill.id);
      toast.success(`${skill.name} installed`);
    } catch { toast.error('Install failed'); }
  };

  const handleUninstall = async (skill) => {
    try {
      await uninstallSkill(skill.id);
      toast.success(`${skill.name} uninstalled`);
      setDetailOpen(false);
    } catch { toast.error('Uninstall failed'); }
  };

  const handleToggle = async (skill, enabled) => {
    try {
      await toggleSkill(skill.id || skill.skill_id, enabled);
    } catch { toast.error('Toggle failed'); }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) { setSearchResults(null); return; }
    setSearching(true);
    try {
      const res = await marketplaceService.searchSkills({ query: searchQuery, limit: 20 });
      const data = res.data || res;
      setSearchResults(data.skills || []);
    } catch { setSearchResults([]); }
    finally { setSearching(false); }
  };

  const handleCategoryExpand = async (catId) => {
    if (expandedCategory === catId) { setExpandedCategory(null); return; }
    setExpandedCategory(catId);
    if (!categorySkills[catId]) {
      try {
        const res = await marketplaceService.searchSkills({ category: catId, limit: 50 });
        const data = res.data || res;
        setCategorySkills((prev) => ({ ...prev, [catId]: data.skills || [] }));
      } catch { setCategorySkills((prev) => ({ ...prev, [catId]: [] })); }
    }
  };

  const loadGateway = async () => {
    setShowGateway(!showGateway);
    if (!gatewayStatus) {
      try {
        const res = await marketplaceService.getGatewayStatus();
        setGatewayStatus(res.data || res);
      } catch { setGatewayStatus({ status: 'unknown' }); }
    }
  };

  const handleSubscribeAgent = async (skill) => {
    try {
      await subscribeAgent(skill.id);
      toast.success(`Hired ${skill.name}! They've been added as your AI friend.`);
    } catch { toast.error('Hiring failed'); }
  };

  const handleUnsubscribeAgent = async (skill) => {
    try {
      await unsubscribeAgent(skill.id);
      toast.success(`Unsubscribed from ${skill.name}`);
    } catch { toast.error('Unsubscribe failed'); }
  };

  const handleToggleAgent = async (skill, enabled) => {
    try {
      await toggleAgent(skill.id, enabled);
    } catch { toast.error('Toggle failed'); }
  };

  const viewDetail = (skill) => { setSelectedSkill(skill); setDetailOpen(true); };

  const loading = installedLoading || catalogLoading || agentsLoading;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-8 h-8 border-3 border-purple-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2.5 rounded-xl" style={{ background: isImmersive ? 'rgba(139, 92, 246, 0.2)' : '#ede9fe' }}>
          <Sparkles className="w-5 h-5" style={{ color: accentPurple }} />
        </div>
        <div>
          <h3 className="text-lg font-bold" style={{ color: textPrimary }}>Siddhi Bazaar</h3>
          <p className="text-xs" style={{ color: textMuted }}>Discover and manage your avatar's skills</p>
        </div>
      </div>

      {/* Search */}
      <div className="flex gap-2">
        <Input
          placeholder="Search skills..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          className="rounded-xl h-10"
          style={{ backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#fff', borderColor, color: textPrimary }}
        />
        <Button onClick={handleSearch} size="sm" className="h-10 px-4 rounded-xl bg-gradient-to-r from-pink-500 to-purple-600 text-white">
          <Search className="w-4 h-4" />
        </Button>
      </div>

      {/* Search Results */}
      {searchResults && (
        <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${borderColor}` }}>
          <div className="px-4 py-2.5 flex items-center justify-between" style={{ backgroundColor: sectionBg, borderBottom: `1px solid ${borderColor}` }}>
            <span className="text-sm font-semibold" style={{ color: textPrimary }}>Search Results ({searchResults.length})</span>
            <Button variant="ghost" size="sm" onClick={() => { setSearchResults(null); setSearchQuery(''); }} className="text-xs h-7">Clear</Button>
          </div>
          <div className="p-3 space-y-2 max-h-72 overflow-y-auto">
            {searchResults.length === 0 ? (
              <p className="text-sm text-center py-4" style={{ color: textMuted }}>No skills found</p>
            ) : searchResults.map((skill) => (
              <SkillCard key={skill.id} skill={skill} isInstalled={isSkillInstalled(skill)} isEnabled={isSkillEnabled(skill)}
                onInstall={handleInstall} onToggle={handleToggle} onViewDetail={viewDetail}
                installing={installing} toggling={toggling} isImmersive={isImmersive} />
            ))}
          </div>
        </div>
      )}

      {/* AI Assistants */}
      {agents.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${borderColor}` }}>
          <div className="px-4 py-3 flex items-center gap-2" style={{ backgroundColor: isImmersive ? 'rgba(16, 185, 129, 0.1)' : '#ecfdf5', borderBottom: `1px solid ${borderColor}` }}>
            <Bot className="w-4 h-4" style={{ color: '#10b981' }} />
            <h4 className="text-sm font-semibold" style={{ color: textPrimary }}>AI Agent Assistants</h4>
            <Badge variant="outline" className="text-[10px] ml-auto" style={{ borderColor: '#10b98140', color: '#10b981' }}>
              {subscribedAgents.length} hired
            </Badge>
          </div>
          <div className="p-3 space-y-2 max-h-96 overflow-y-auto">
            <p className="text-xs px-1 mb-2" style={{ color: textMuted }}>
              Hire expert AI agents who join your circle as friends and share domain knowledge.
            </p>
            {agents.map((item) => {
              const skill = item.skill || item;
              const agent = item.agent || null;
              return (
                <AgentCard
                  key={skill.id}
                  agentSkill={skill}
                  agentUser={agent}
                  isSubscribed={isAgentSubscribed(skill)}
                  isEnabled={isAgentEnabled(skill)}
                  onSubscribe={handleSubscribeAgent}
                  onUnsubscribe={handleUnsubscribeAgent}
                  onToggle={handleToggleAgent}
                  onViewDetail={viewDetail}
                  subscribing={subscribing}
                  toggling={agentToggling}
                  isImmersive={isImmersive}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* My Skills */}
      <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${borderColor}` }}>
        <div className="px-4 py-3 flex items-center gap-2" style={{ backgroundColor: sectionBg, borderBottom: `1px solid ${borderColor}` }}>
          <Shield className="w-4 h-4" style={{ color: accentPurple }} />
          <h4 className="text-sm font-semibold" style={{ color: textPrimary }}>My Skills</h4>
          <Badge variant="outline" className="text-[10px] ml-auto">{installedSkills.length} installed</Badge>
        </div>
        <div className="divide-y max-h-72 overflow-y-auto" style={{ borderColor }}>
          {installedSkills.length === 0 ? (
            <div className="text-center py-8">
              <Package className="w-10 h-10 mx-auto mb-2" style={{ color: textMuted }} />
              <p className="text-sm" style={{ color: textMuted }}>No skills installed yet</p>
              <p className="text-xs mt-1" style={{ color: textMuted }}>Browse below to add skills</p>
            </div>
          ) : installedSkills.map((skill) => (
            <div key={skill.slug} className="flex items-center justify-between px-4 py-2.5 transition-colors hover:bg-opacity-50"
              style={{ cursor: 'pointer' }}
              onClick={() => {
                const fullSkill = { id: skill.skill_id, slug: skill.slug, name: skill.name, tagline: skill.tagline, description: skill.description, icon: skill.icon, color: skill.color, category: skill.category, tier: skill.tier, type: skill.type, stats: skill.stats, state_affinity: skill.state_affinity, binding: skill.binding, tags: skill.tags };
                viewDetail(fullSkill);
              }}
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <span className="text-sm flex-shrink-0" style={{ color: skill.color || textPrimary }}>
                  {(() => { const Icon = getIcon(skill.icon); return <Icon className="w-4 h-4" />; })()}
                </span>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium truncate" style={{ color: textPrimary }}>{skill.name}</span>
                    {skill.gateway_state?.circuit_status === 'open' && (
                      <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0" />
                    )}
                  </div>
                  <p className="text-[10px]" style={{ color: textMuted }}>
                    {skill.usage?.total_executions > 0 ? `${skill.usage.total_executions} uses` : 'Not used yet'}
                    {skill.usage?.last_used_at && ` · Last: ${new Date(skill.usage.last_used_at).toLocaleDateString()}`}
                  </p>
                </div>
              </div>
              <div onClick={(e) => e.stopPropagation()}>
                <Switch
                  checked={skill.enabled}
                  onCheckedChange={(v) => handleToggle(skill, v)}
                  disabled={toggling === skill.skill_id}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recommended */}
      {recommended.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${borderColor}` }}>
          <div className="px-4 py-3 flex items-center gap-2" style={{ backgroundColor: sectionBg, borderBottom: `1px solid ${borderColor}` }}>
            <Sparkles className="w-4 h-4" style={{ color: accentPurple }} />
            <h4 className="text-sm font-semibold" style={{ color: textPrimary }}>Recommended for You</h4>
          </div>
          <div className="p-3 space-y-2 max-h-64 overflow-y-auto">
            {recommended.map((skill) => (
              <SkillCard key={skill.id} skill={skill} isInstalled={isSkillInstalled(skill)} isEnabled={isSkillEnabled(skill)}
                onInstall={handleInstall} onToggle={handleToggle} onViewDetail={viewDetail}
                installing={installing} toggling={toggling} isImmersive={isImmersive} />
            ))}
          </div>
        </div>
      )}

      {/* Featured */}
      {featured.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${borderColor}` }}>
          <div className="px-4 py-3 flex items-center gap-2" style={{ backgroundColor: sectionBg, borderBottom: `1px solid ${borderColor}` }}>
            <Sparkles className="w-4 h-4 text-amber-500" />
            <h4 className="text-sm font-semibold" style={{ color: textPrimary }}>Featured</h4>
          </div>
          <div className="p-3 space-y-2">
            {featured.map((skill) => (
              <SkillCard key={skill.id} skill={skill} isInstalled={isSkillInstalled(skill)} isEnabled={isSkillEnabled(skill)}
                onInstall={handleInstall} onToggle={handleToggle} onViewDetail={viewDetail}
                installing={installing} toggling={toggling} isImmersive={isImmersive} />
            ))}
          </div>
        </div>
      )}

      {/* Browse by Category */}
      <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${borderColor}` }}>
        <div className="px-4 py-3" style={{ backgroundColor: sectionBg, borderBottom: `1px solid ${borderColor}` }}>
          <h4 className="text-sm font-semibold" style={{ color: textPrimary }}>Browse by Category</h4>
        </div>
        <div className="divide-y" style={{ borderColor }}>
          {categories.map((cat) => (
            <div key={cat.id}>
              <button
                onClick={() => handleCategoryExpand(cat.id)}
                className="w-full flex items-center justify-between px-4 py-3 transition-colors"
                style={{ color: textPrimary }}
              >
                <div className="flex items-center gap-2.5">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cat.color }} />
                  <span className="text-sm font-medium">{cat.name}</span>
                  <Badge variant="outline" className="text-[10px]">{cat.skill_count}</Badge>
                </div>
                {expandedCategory === cat.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              {expandedCategory === cat.id && (
                <div className="px-3 pb-3 space-y-2">
                  {!categorySkills[cat.id] ? (
                    <div className="flex justify-center py-4"><div className="w-5 h-5 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" /></div>
                  ) : categorySkills[cat.id].length === 0 ? (
                    <p className="text-xs text-center py-3" style={{ color: textMuted }}>No skills in this category</p>
                  ) : categorySkills[cat.id].map((skill) => (
                    <SkillCard key={skill.id} skill={skill} isInstalled={isSkillInstalled(skill)} isEnabled={isSkillEnabled(skill)}
                      onInstall={handleInstall} onToggle={handleToggle} onViewDetail={viewDetail}
                      installing={installing} toggling={toggling} isImmersive={isImmersive} />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Gateway Health */}
      <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${borderColor}` }}>
        <button onClick={loadGateway} className="w-full px-4 py-3 flex items-center justify-between" style={{ backgroundColor: sectionBg }}>
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4" style={{ color: accentPurple }} />
            <h4 className="text-sm font-semibold" style={{ color: textPrimary }}>Gateway Health</h4>
          </div>
          {gatewayStatus && (
            <div className="flex items-center gap-1.5">
              {gatewayStatus.status === 'operational' && <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />}
              {gatewayStatus.status === 'degraded' && <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />}
              {gatewayStatus.status === 'unhealthy' && <XCircle className="w-3.5 h-3.5 text-red-500" />}
              <span className="text-xs capitalize" style={{ color: textMuted }}>{gatewayStatus.status}</span>
            </div>
          )}
          {showGateway ? <ChevronUp className="w-4 h-4" style={{ color: textMuted }} /> : <ChevronDown className="w-4 h-4" style={{ color: textMuted }} />}
        </button>
        {showGateway && gatewayStatus && (
          <div className="px-4 py-3 space-y-2" style={{ borderTop: `1px solid ${borderColor}` }}>
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center p-2 rounded-lg" style={{ backgroundColor: cardBg }}>
                <p className="text-lg font-bold" style={{ color: textPrimary }}>{gatewayStatus.skills_installed}</p>
                <p className="text-[10px]" style={{ color: textMuted }}>Installed</p>
              </div>
              <div className="text-center p-2 rounded-lg" style={{ backgroundColor: cardBg }}>
                <p className="text-lg font-bold" style={{ color: textPrimary }}>{gatewayStatus.total_executions}</p>
                <p className="text-[10px]" style={{ color: textMuted }}>Executions</p>
              </div>
              <div className="text-center p-2 rounded-lg" style={{ backgroundColor: cardBg }}>
                <p className="text-lg font-bold" style={{ color: textPrimary }}>{gatewayStatus.success_rate}%</p>
                <p className="text-[10px]" style={{ color: textMuted }}>Success</p>
              </div>
            </div>
            <div className="flex items-center gap-4 text-xs" style={{ color: textMuted }}>
              <span className="flex items-center gap-1"><CheckCircle className="w-3 h-3 text-emerald-500" /> {gatewayStatus.healthy} healthy</span>
              {gatewayStatus.degraded > 0 && <span className="flex items-center gap-1"><AlertTriangle className="w-3 h-3 text-amber-500" /> {gatewayStatus.degraded} degraded</span>}
              {gatewayStatus.broken > 0 && <span className="flex items-center gap-1"><XCircle className="w-3 h-3 text-red-500" /> {gatewayStatus.broken} broken</span>}
            </div>
          </div>
        )}
      </div>

      {/* Skill Detail Dialog */}
      <SkillDetailDialog
        skill={selectedSkill}
        open={detailOpen}
        onOpenChange={setDetailOpen}
        isInstalled={selectedSkill ? isSkillInstalled(selectedSkill) : false}
        isEnabled={selectedSkill ? isSkillEnabled(selectedSkill) : false}
        onInstall={handleInstall}
        onUninstall={handleUninstall}
        onToggle={handleToggle}
        installing={installing}
        isImmersive={isImmersive}
      />
    </div>
  );
};

export default SiddhiBazaarTab;
