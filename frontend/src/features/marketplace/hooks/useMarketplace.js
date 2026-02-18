/**
 * useMarketplace - Hook for marketplace catalog browsing
 */

import { useState, useEffect, useCallback } from 'react';
import marketplaceService from '@/services/api/marketplaceService';

export function useMarketplace() {
  const [skills, setSkills] = useState([]);
  const [categories, setCategories] = useState([]);
  const [featured, setFeatured] = useState([]);
  const [recommended, setRecommended] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCatalog = useCallback(async () => {
    try {
      setLoading(true);
      const [catRes, featRes, recRes] = await Promise.all([
        marketplaceService.getCategories().catch(() => ({ data: [] })),
        marketplaceService.getFeatured().catch(() => ({ data: [] })),
        marketplaceService.getRecommended().catch(() => ({ data: [] })),
      ]);

      setCategories(catRes.data || catRes || []);

      // Deduplicate by slug (guard against multiple seed runs)
      const dedup = (arr) => {
        const seen = new Set();
        return (Array.isArray(arr) ? arr : []).filter((s) => {
          const key = s.slug || s.id;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
      };

      setFeatured(dedup(featRes.data || featRes));
      setRecommended(dedup(recRes.data || recRes));
      setError(null);
    } catch (err) {
      console.error('Failed to load marketplace:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const searchSkills = useCallback(async (params = {}) => {
    try {
      const response = await marketplaceService.searchSkills(params);
      const data = response.data || response;
      setSkills(data.skills || []);
      return data;
    } catch (err) {
      console.error('Search failed:', err);
      return { skills: [], total: 0 };
    }
  }, []);

  const getSkillsByCategory = useCallback(async (category) => {
    try {
      const response = await marketplaceService.searchSkills({ category, limit: 50 });
      const data = response.data || response;
      return data.skills || [];
    } catch (err) {
      console.error('Category fetch failed:', err);
      return [];
    }
  }, []);

  useEffect(() => {
    fetchCatalog();
  }, [fetchCatalog]);

  return {
    skills, categories, featured, recommended,
    loading, error,
    searchSkills, getSkillsByCategory, refetch: fetchCatalog,
  };
}

export default useMarketplace;
