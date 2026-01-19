import React from 'react';
import { cn } from '../utils/cva';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'sm' | 'base' | 'lg' | 'xl';
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input: React.FC<InputProps> = ({
  className,
  variant = 'default',
  size = 'base',
  leftIcon,
  rightIcon,
  style,
  ...props
}) => {
  const variants = {
    default: 'bg-neutral-50 border-neutral-200 text-neutral-900 placeholder-neutral-500 focus:ring-primary-500 focus:border-primary-500',
    outline: 'bg-transparent border-neutral-300 text-neutral-900 placeholder-neutral-400 focus:ring-primary-500 focus:border-primary-500',
    ghost: 'bg-neutral-50 border-transparent text-neutral-900 placeholder-neutral-500 focus:ring-primary-500 focus:border-primary-500',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    base: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
    xl: 'px-8 py-4 text-xl',
  };

  const mergedStyle = { transitionDuration: 'var(--motion-duration)', ...style };

  return (
    <div className="relative">
      {leftIcon && <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500">{leftIcon}</span>}
      <input
        className={cn(
          'w-full rounded-lg border transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none',
          leftIcon && 'pl-10',
          rightIcon && 'pr-10',
          variants[variant],
          sizes[size],
          className
        )}
        style={mergedStyle}
        {...props}
      />
      {rightIcon && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500">{rightIcon}</span>}
    </div>
  );
};

export default Input;
