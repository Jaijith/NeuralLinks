/**
 * Performance utilities
 * Helpers for measuring and optimizing performance
 */

import { logger } from './logger';

/**
 * Measure function execution time
 */
export const measurePerformance = (fn, label = 'Function') => {
  return (...args) => {
    const start = performance.now();
    const result = fn(...args);
    const end = performance.now();
    const duration = end - start;
    
    if (duration > 100) {
      logger.warn(`${label} took ${duration.toFixed(2)}ms`);
    } else {
      logger.debug(`${label} took ${duration.toFixed(2)}ms`);
    }
    
    return result;
  };
};

/**
 * Measure async function execution time
 */
export const measureAsyncPerformance = async (fn, label = 'Async Function') => {
  const start = performance.now();
  const result = await fn();
  const end = performance.now();
  const duration = end - start;
  
  if (duration > 1000) {
    logger.warn(`${label} took ${duration.toFixed(2)}ms`);
  } else {
    logger.debug(`${label} took ${duration.toFixed(2)}ms`);
  }
  
  return result;
};

/**
 * Debounce function with performance tracking
 */
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

/**
 * Throttle function with performance tracking
 */
export const throttle = (func, limit) => {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

/**
 * Get performance metrics
 */
export const getPerformanceMetrics = () => {
  if (typeof window === 'undefined' || !window.performance) {
    return null;
  }

  const navigation = performance.getEntriesByType('navigation')[0];
  if (!navigation) {
    return null;
  }

  return {
    dns: navigation.domainLookupEnd - navigation.domainLookupStart,
    tcp: navigation.connectEnd - navigation.connectStart,
    request: navigation.responseStart - navigation.requestStart,
    response: navigation.responseEnd - navigation.responseStart,
    domProcessing: navigation.domComplete - navigation.domInteractive,
    load: navigation.loadEventEnd - navigation.loadEventStart,
    total: navigation.loadEventEnd - navigation.fetchStart,
  };
};

/**
 * Log performance metrics
 */
export const logPerformanceMetrics = () => {
  const metrics = getPerformanceMetrics();
  if (metrics) {
    logger.info('Performance Metrics:', metrics);
  }
};

