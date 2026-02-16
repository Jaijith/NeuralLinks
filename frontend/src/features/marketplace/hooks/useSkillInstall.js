/**
 * useSkillInstall - Hook for install/uninstall/toggle mutations
 */

import { useState, useCallback } from 'react';
import marketplaceService from '@/services/api/marketplaceService';
import { invalidateInstalledSkills } from './useInstalledSkills';

export function useSkillInstall() {
  const [installing, setInstalling] = useState(null);
  const [toggling, setToggling] = useState(null);

  const installSkill = useCallback(async (skillId) => {
    setInstalling(skillId);
    try {
      const response = await marketplaceService.installSkill(skillId);
      invalidateInstalledSkills();
      return response.data || response;
    } catch (err) {
      console.error('Install failed:', err);
      throw err;
    } finally {
      setInstalling(null);
    }
  }, []);

  const uninstallSkill = useCallback(async (skillId) => {
    setInstalling(skillId);
    try {
      const response = await marketplaceService.uninstallSkill(skillId);
      invalidateInstalledSkills();
      return response.data || response;
    } catch (err) {
      console.error('Uninstall failed:', err);
      throw err;
    } finally {
      setInstalling(null);
    }
  }, []);

  const toggleSkill = useCallback(async (skillId, enabled) => {
    setToggling(skillId);
    try {
      const response = await marketplaceService.toggleSkill(skillId, enabled);
      invalidateInstalledSkills();
      return response.data || response;
    } catch (err) {
      console.error('Toggle failed:', err);
      throw err;
    } finally {
      setToggling(null);
    }
  }, []);

  return { installSkill, uninstallSkill, toggleSkill, installing, toggling };
}

export default useSkillInstall;
