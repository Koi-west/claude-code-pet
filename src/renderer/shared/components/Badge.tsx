import React from 'react';
import { cn } from '../utils/cva';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'success' | 'error' | 'warning' | 'neutral';
  size?: 'sm' | 'base' | 'lg';
}

const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'primary',
  size = 'base',
  ...props
}) => {
  const variants = {
    primary: 'bg-primary-500 text-white',
    success: 'bg-success-500 text-white',
    error: 'bg-error-500 text-white',
    warning: 'bg-warning-500 text-white',
    neutral: 'bg-neutral-200 text-neutral-800',
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    base: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded-full font-medium',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
};

export default Badge;