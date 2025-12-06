/**
 * Centralized error handling utilities
 */

/**
 * Format error message for user display
 */
export const formatErrorMessage = (error) => {
  if (!error) return 'An unexpected error occurred';

  // Handle axios errors
  if (error.response) {
    const { status, data } = error.response;
    
    if (data?.detail) {
      return data.detail;
    }
    
    switch (status) {
      case 400:
        return 'Invalid request. Please check your input.';
      case 401:
        return 'You are not authorized. Please log in again.';
      case 403:
        return 'You do not have permission to perform this action.';
      case 404:
        return 'The requested resource was not found.';
      case 500:
        return 'Server error. Please try again later.';
      default:
        return `Error ${status}: ${data?.message || 'Something went wrong'}`;
    }
  }
  
  // Handle network errors
  if (error.request) {
    return 'Network error. Please check your connection.';
  }
  
  // Handle other errors
  return error.message || 'An unexpected error occurred';
};

/**
 * Log error for monitoring
 */
export const logError = (error, context = {}) => {
  const errorInfo = {
    message: error?.message || 'Unknown error',
    stack: error?.stack,
    context,
    timestamp: new Date().toISOString(),
    url: window.location.href,
  };

  // In production, send to error tracking service (e.g., Sentry)
  if (process.env.NODE_ENV === 'production') {
    // TODO: Integrate with error tracking service
    console.error('[Error Log]', errorInfo);
  } else {
    console.error('[Error Log]', errorInfo);
  }
};

/**
 * Handle API error with logging and user-friendly message
 */
export const handleApiError = (error, context = {}) => {
  logError(error, context);
  return formatErrorMessage(error);
};

