/**
 * useInstalledSkills - Shared hook for installed skills
 * Used by BOTH Siddhi Bazaar tab and EditMayaProfileDialog
 */

import { useState, useEffect, useCallback } from 'react';
import marketplaceService from '@/services/api/marketplaceService';

let _cache = null;
let _cacheTime = 0;
const CACHE_TTL = 30000; // 30 seconds
const _listeners = new Set();

function notifyListeners() {
  _listeners.forEach((fn) => fn());
}

export function invalidateInstalledSkills() {
  _cache = null;
  _cacheTime = 0;
  notifyListeners();
}

export function useInstalledSkills() {
  const [installedSkills, setInstalledSkills] = useState(_cache || []);
  const [loading, setLoading] = useState(!_cache);
  const [error, setError] = useState(null);

  const fetchInstalled = useCallback(async (force = false) => {
    const now = Date.now();
    if (!force && _cache && now - _cacheTime < CACHE_TTL) {
      setInstalledSkills(_cache);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await marketplaceService.getInstalled();
      const data = response.data || response;
      const items = Array.isArray(data) ? data : [];

      const mapped = items.map((item) => {
        const skill = item.skill || {};
        const inst = item.installation || {};
        return {
          skill_id: skill.id || inst.skill_id,
          slug: inst.skill_slug || skill.slug,
          name: skill.name || inst.skill_slug,
          tagline: skill.tagline || '',
          description: skill.description || '',
          icon: skill.icon || 'box',
          color: skill.color || '#6366f1',
          category: skill.category || '',
          tier: skill.tier || 'standard',
          type: skill.type || inst.skill_type || 'mcp_tool',
          enabled: inst.enabled ?? true,
          permission_key: skill.binding?.permission_key || null,
          usage: inst.usage || {},
          gateway_state: inst.gateway_state || {},
          installed_at: inst.installed_at,
          user_rating: inst.user_rating,
          stats: skill.stats || {},
          is_default: skill.is_default || false,
          tags: skill.tags || [],
          state_affinity: skill.state_affinity || {},
          binding: skill.binding || {},
        };
      });

      _cache = mapped;
      _cacheTime = Date.now();
      setInstalledSkills(mapped);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch installed skills:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInstalled();

    const listener = () => fetchInstalled(true);
    _listeners.add(listener);
    return () => _listeners.delete(listener);
  }, [fetchInstalled]);

  const refetch = useCallback(() => fetchInstalled(true), [fetchInstalled]);

  return { installedSkills, loading, error, refetch };
}

export default useInstalledSkills;
