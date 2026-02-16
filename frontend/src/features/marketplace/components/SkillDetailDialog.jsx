import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Star } from 'lucide-react';
import { getIcon, TIER_COLORS } from './SkillCard';
import marketplaceService from '@/services/api/marketplaceService';

const SkillDetailDialog = ({ skill, open, onOpenChange, isInstalled, isEnabled, onInstall, onUninstall, onToggle, installing, isImmersive }) => {
  const [reviews, setReviews] = useState([]);
  const [loadingReviews, setLoadingReviews] = useState(false);

  useEffect(() => {
    if (open && skill) {
      setLoadingReviews(true);
      marketplaceService.getReviews(skill.id).then((res) => {
        setReviews(res.data || res || []);
      }).catch(() => setReviews([])).finally(() => setLoadingReviews(false));
    }
  }, [open, skill]);

  if (!skill) return null;

  const IconComponent = getIcon(skill.icon);
  const tierClass = TIER_COLORS[skill.tier] || TIER_COLORS.standard;
  const bg = isImmersive ? 'rgba(10, 15, 30, 0.98)' : '#ffffff';
  const borderColor = isImmersive ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0';
  const textPrimary = isImmersive ? '#e2e8f0' : '#1e293b';
  const textMuted = isImmersive ? '#94a3b8' : '#64748b';
  const cardBg = isImmersive ? 'rgba(30, 35, 55, 0.6)' : '#f8fafc';

  const affinity = skill.state_affinity || {};
  const includedTools = skill.binding?.workflow_tools_included || [];
  const bundledIds = skill.binding?.bundled_skill_ids || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-lg max-h-[80vh] overflow-y-auto rounded-2xl p-0 border"
        style={{ backgroundColor: bg, borderColor }}
      >
        <div className="p-6">
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-3 rounded-xl" style={{ backgroundColor: `${skill.color}15`, border: `1px solid ${skill.color}30` }}>
                <IconComponent className="w-6 h-6" style={{ color: skill.color }} />
              </div>
              <div>
                <DialogTitle className="text-lg font-bold" style={{ color: textPrimary }}>
                  {skill.name}
                </DialogTitle>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${tierClass}`}>
                    {skill.tier}
                  </Badge>
                  <span className="text-xs" style={{ color: textMuted }}>{skill.category?.replace(/_/g, ' ')}</span>
                </div>
              </div>
            </div>
          </DialogHeader>

          {/* Stats */}
          {skill.stats && (
            <div className="flex items-center gap-4 mb-4 text-xs" style={{ color: textMuted }}>
              {skill.stats.total_installs > 0 && <span>{skill.stats.total_installs}+ installs</span>}
              {skill.stats.avg_rating > 0 && (
                <span className="flex items-center gap-0.5">
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                  {skill.stats.avg_rating} ({skill.stats.total_ratings})
                </span>
              )}
              {skill.stats.total_executions > 0 && <span>{skill.stats.total_executions} runs</span>}
            </div>
          )}

          {/* Description */}
          <p className="text-sm mb-4 leading-relaxed" style={{ color: textPrimary }}>
            {skill.description}
          </p>

          {/* State Affinity */}
          {affinity.preferred_states && affinity.preferred_states.length > 0 && (
            <div className="mb-4 rounded-xl p-3" style={{ backgroundColor: cardBg, border: `1px solid ${borderColor}` }}>
              <h5 className="text-xs font-semibold mb-2" style={{ color: textPrimary }}>Best in States</h5>
              <div className="flex flex-wrap gap-1.5">
                {affinity.preferred_states.map((s) => (
                  <Badge key={s} variant="outline" className="text-[10px]">{s}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Included Tools (for engines) */}
          {includedTools.length > 0 && (
            <div className="mb-4 rounded-xl p-3" style={{ backgroundColor: cardBg, border: `1px solid ${borderColor}` }}>
              <h5 className="text-xs font-semibold mb-2" style={{ color: textPrimary }}>Includes {includedTools.length} tools</h5>
              <div className="flex flex-wrap gap-1.5">
                {includedTools.map((t) => (
                  <Badge key={t} variant="outline" className="text-[10px]">{t.replace(/_/g, ' ')}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Bundled skills count */}
          {bundledIds.length > 0 && (
            <div className="mb-4 rounded-xl p-3" style={{ backgroundColor: cardBg, border: `1px solid ${borderColor}` }}>
              <h5 className="text-xs font-semibold" style={{ color: textPrimary }}>
                Bundle includes {bundledIds.length} skills
              </h5>
            </div>
          )}

          {/* Reviews */}
          {reviews.length > 0 && (
            <div className="mb-4">
              <h5 className="text-xs font-semibold mb-2" style={{ color: textPrimary }}>Reviews</h5>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {reviews.map((r) => (
                  <div key={r.id} className="rounded-lg p-2.5" style={{ backgroundColor: cardBg, border: `1px solid ${borderColor}` }}>
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-xs font-medium" style={{ color: textPrimary }}>{r.avatar_name}</span>
                      <span className="text-[10px]" style={{ color: textMuted }}>{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</span>
                    </div>
                    {r.review_text && <p className="text-[11px]" style={{ color: textMuted }}>{r.review_text}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-3 pt-2">
            {isInstalled ? (
              <>
                <div className="flex items-center gap-2 flex-1">
                  <span className="text-sm" style={{ color: textPrimary }}>Enabled</span>
                  <Switch checked={isEnabled} onCheckedChange={(v) => onToggle && onToggle(skill, v)} />
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onUninstall && onUninstall(skill)}
                  className="text-red-600 border-red-200 hover:bg-red-50"
                >
                  Uninstall
                </Button>
              </>
            ) : (
              <Button
                onClick={() => onInstall && onInstall(skill)}
                disabled={installing === skill.id}
                className="w-full bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:from-pink-600 hover:to-purple-700"
              >
                {installing === skill.id ? 'Installing...' : 'Install Skill'}
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default SkillDetailDialog;
