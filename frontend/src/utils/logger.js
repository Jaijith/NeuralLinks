/**
 * Centralized logging utility
 * Provides structured logging with different log levels
 */

const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
};

const currentLogLevel = process.env.NODE_ENV === 'production' 
  ? LOG_LEVELS.WARN 
  : LOG_LEVELS.DEBUG;

/**
 * Create a log entry
 */
const createLogEntry = (level, message, data = {}) => {
  return {
    level,
    message,
    data,
    timestamp: new Date().toISOString(),
    url: window.location.href,
  };
};

/**
 * Log debug message
 */
export const debug = (message, data = {}) => {
  if (currentLogLevel <= LOG_LEVELS.DEBUG) {
    const entry = createLogEntry('DEBUG', message, data);
    console.debug('[DEBUG]', entry);
  }
};

/**
 * Log info message
 */
export const info = (message, data = {}) => {
  if (currentLogLevel <= LOG_LEVELS.INFO) {
    const entry = createLogEntry('INFO', message, data);
    console.info('[INFO]', entry);
  }
};

/**
 * Log warning message
 */
export const warn = (message, data = {}) => {
  if (currentLogLevel <= LOG_LEVELS.WARN) {
    const entry = createLogEntry('WARN', message, data);
    console.warn('[WARN]', entry);
  }
};

/**
 * Log error message
 */
export const error = (message, data = {}) => {
  if (currentLogLevel <= LOG_LEVELS.ERROR) {
    const entry = createLogEntry('ERROR', message, data);
    console.error('[ERROR]', entry);
  }
};

/**
 * Log API request
 */
export const logApiRequest = (method, url, data = {}) => {
  debug(`API Request: ${method} ${url}`, data);
};

/**
 * Log API response
 */
export const logApiResponse = (method, url, status, data = {}) => {
  debug(`API Response: ${method} ${url} [${status}]`, data);
};

export default {
  debug,
  info,
  warn,
  error,
  logApiRequest,
  logApiResponse,
};

