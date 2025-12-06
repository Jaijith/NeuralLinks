import React from 'react';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} SidebarProps
 * @property {React.ReactNode} children - Sidebar content
 * @property {string} [className] - Additional CSS classes
 * @property {string} [variant] - Visual variant ('default' | 'compact')
 */

/**
 * Reusable Sidebar wrapper component for consistent sidebar styling.
 * @param {SidebarProps} props
 */
const Sidebar = React.memo(({ 
  children, 
  className,
  variant = 'default'
}) => {
  return (
    <div className={cn(
      "space-y-4",
      variant === 'compact' && "space-y-2",
      className
    )}>
      {children}
    </div>
  );
});

Sidebar.displayName = "Sidebar";

/**
 * @typedef {Object} SidebarSectionProps
 * @property {React.ReactNode} children - Section content
 * @property {string} [title] - Section title
 * @property {React.ReactNode} [headerAction] - Action element in header
 * @property {string} [className] - Additional CSS classes
 */

/**
 * Reusable Sidebar Section component for consistent section styling.
 * @param {SidebarSectionProps} props
 */
const SidebarSection = React.memo(({ 
  children, 
  title,
  headerAction,
  className
}) => {
  return (
    <Card className={cn("rounded-xl overflow-hidden glass-card", className)}>
      {title && (
        <div className="flex items-center justify-between p-4 pb-3 border-b border-gray-200">
          <h3 className="font-semibold text-sm text-gray-900">
            {title}
          </h3>
          {headerAction && (
            <div>{headerAction}</div>
          )}
        </div>
      )}
      <div className={title ? "p-4" : "p-3"}>
        {children}
      </div>
    </Card>
  );
});

SidebarSection.displayName = "SidebarSection";

Sidebar.Section = SidebarSection;

export default Sidebar;
export { SidebarSection };

