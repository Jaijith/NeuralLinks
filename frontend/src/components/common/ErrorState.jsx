import React from 'react';
import { Button } from '@/components/ui/button';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} ErrorStateProps
 * @property {string} [title] - Error title (default: "Something went wrong")
 * @property {string} [message] - Error message
 * @property {function} [onRetry] - Retry button click handler
 * @property {string} [retryLabel] - Retry button label (default: "Try Again")
 * @property {string} [variant] - Visual variant ('default' | 'minimal')
 * @property {string} [className] - Additional CSS classes
 */

/**
 * Reusable Error State component for displaying errors consistently across pages.
 * @param {ErrorStateProps} props
 */
const ErrorState = React.memo(({ 
  title = "Something went wrong",
  message,
  onRetry,
  retryLabel = "Try Again",
  variant = 'default',
  className
}) => {
  const isMinimal = variant === 'minimal';

  return (
    <div className={cn(
      "flex flex-col items-center justify-center",
      isMinimal ? "py-4" : "min-h-[300px] p-8",
      className
    )}>
      <div className={cn(
        "mx-auto mb-4 rounded-full flex items-center justify-center",
        isMinimal ? "w-12 h-12 bg-red-100" : "w-16 h-16 bg-red-100"
      )}>
        <AlertTriangle className={cn(
          "text-red-500",
          isMinimal ? "w-6 h-6" : "w-8 h-8"
        )} />
      </div>
      
      <h3 className={cn(
        "font-bold mb-2 text-gray-900",
        isMinimal ? "text-lg" : "text-2xl"
      )}>
        {title}
      </h3>
      
      {message && (
        <p className={cn(
          "text-center mb-6 text-gray-600",
          isMinimal ? "text-sm mb-3" : ""
        )}>
          {message}
        </p>
      )}
      
      {onRetry && (
        <Button
          onClick={onRetry}
          variant="outline"
          className={cn(
            "px-6 py-3 rounded-full",
            isMinimal ? "px-4 py-2 text-sm" : ""
          )}
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          {retryLabel}
        </Button>
      )}
    </div>
  );
});

ErrorState.displayName = "ErrorState";

export default ErrorState;

