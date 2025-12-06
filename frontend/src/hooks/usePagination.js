/**
 * Reusable pagination hook
 * Manages pagination state and provides load more functionality
 */

import { useState, useCallback } from 'react';

export const usePagination = (fetchFunction, initialLimit = 20) => {
  const [items, setItems] = useState([]);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const fetchItems = useCallback(
    async (reset = false, ...args) => {
      const currentSkip = reset ? 0 : skip;

      if (reset) {
        setLoading(true);
        setItems([]);
        setSkip(0);
        setHasMore(true);
      } else {
        setLoadingMore(true);
      }

      try {
        const result = await fetchFunction(currentSkip, ...args);
        const newItems = result.posts || result.data || result || [];
        const hasMoreItems = result.has_more !== undefined ? result.has_more : newItems.length === initialLimit;

        if (reset) {
          setItems(newItems);
        } else {
          setItems((prev) => [...prev, ...newItems]);
        }

        setSkip(currentSkip + newItems.length);
        setHasMore(hasMoreItems);
      } catch (error) {
        console.error('Pagination fetch error:', error);
        throw error;
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [fetchFunction, skip, initialLimit]
  );

  const loadMore = useCallback(
    async (...args) => {
      if (!loadingMore && hasMore) {
        await fetchItems(false, ...args);
      }
    },
    [fetchItems, loadingMore, hasMore]
  );

  const reset = useCallback(() => {
    setItems([]);
    setSkip(0);
    setHasMore(true);
    setLoading(false);
    setLoadingMore(false);
  }, []);

  return {
    items,
    loading,
    loadingMore,
    hasMore,
    fetchItems,
    loadMore,
    reset,
  };
};

export default usePagination;

