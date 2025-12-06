/**
 * Generic API hook with loading and error states
 * Provides a reusable pattern for API calls
 */

import { useState, useCallback } from 'react';
import { handleApiError } from '@/utils/errorHandler';

export const useApi = (apiFunction) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(
    async (...args) => {
      setLoading(true);
      setError(null);

      try {
        const result = await apiFunction(...args);
        setData(result);
        return { data: result, error: null };
      } catch (err) {
        const errorMessage = handleApiError(err);
        setError(errorMessage);
        return { data: null, error: errorMessage };
      } finally {
        setLoading(false);
      }
    },
    [apiFunction]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return {
    data,
    loading,
    error,
    execute,
    reset,
  };
};

export default useApi;

