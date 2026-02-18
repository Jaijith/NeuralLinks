/**
 * useAgentSubscription - Hook for managing AI Agent subscriptions
 */

import { useState, useEffect, useCallback } from 'react';
import marketplaceService from '@/services/api/marketplaceService';

export function useAgentSubscription() {
  const [agents, setAgents] = useState([]);
  const [subscribedAgents, setSubscribedAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState(null);
  const [toggling, setToggling] = useState(null);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    try {
      const [agentsRes, subscribedRes] = await Promise.all([
        marketplaceService.getAiAgents(),
        marketplaceService.getSubscribedAgents(),
      ]);
      setAgents(Array.isArray(agentsRes.data || agentsRes) ? (agentsRes.data || agentsRes) : []);
      setSubscribedAgents(Array.isArray(subscribedRes.data || subscribedRes) ? (subscribedRes.data || subscribedRes) : []);
    } catch (err) {
      console.error('Failed to fetch agents:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const subscribeAgent = useCallback(async (skillId) => {
    setSubscribing(skillId);
    try {
      const res = await marketplaceService.subscribeAgent(skillId);
      await fetchAgents();
      return res.data || res;
    } finally {
      setSubscribing(null);
    }
  }, [fetchAgents]);

  const unsubscribeAgent = useCallback(async (skillId) => {
    setSubscribing(skillId);
    try {
      const res = await marketplaceService.unsubscribeAgent(skillId);
      await fetchAgents();
      return res.data || res;
    } finally {
      setSubscribing(null);
    }
  }, [fetchAgents]);

  const toggleAgent = useCallback(async (skillId, enabled) => {
    setToggling(skillId);
    try {
      const res = await marketplaceService.toggleAgent(skillId, enabled);
      await fetchAgents();
      return res.data || res;
    } finally {
      setToggling(null);
    }
  }, [fetchAgents]);

  // Build a map of subscribed agent skill IDs for quick lookup
  const subscribedMap = {};
  subscribedAgents.forEach((sub) => {
    const skillId = sub.subscription?.skill_id || sub.skill?.id;
    if (skillId) subscribedMap[skillId] = sub;
  });

  const isAgentSubscribed = (skill) => !!subscribedMap[skill?.id];
  const isAgentEnabled = (skill) => {
    const sub = subscribedMap[skill?.id];
    return sub ? sub.subscription?.active !== false : false;
  };

  return {
    agents,
    subscribedAgents,
    loading,
    subscribing,
    toggling,
    subscribeAgent,
    unsubscribeAgent,
    toggleAgent,
    isAgentSubscribed,
    isAgentEnabled,
    refreshAgents: fetchAgents,
  };
}

export default useAgentSubscription;
