import React from 'react';
import { cn } from '../utils/cva';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'outline';
}

const Card: React.FC<CardProps> = ({
  className,
  variant = 'default',
  ...props
}) => {
  const variants = {
    default: 'bg-white shadow-sm',
    elevated: 'bg-white shadow-lg',
    outline: 'bg-white border border-neutral-200',
  };

  return (
    <div
      className={cn(
        'rounded-lg overflow-hidden',
        variants[variant],
        className
      )}
      {...props}
    />
  );
};

const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        'px-6 py-4 border-b border-neutral-100',
        className
      )}
      {...props}
    />
  );
};

const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  className,
  ...props
}) => {
  return (
    <h3
      className={cn(
        'text-lg font-semibold text-neutral-900',
        className
      )}
      {...props}
    />
  );
};

const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        'px-6 py-4',
        className
      )}
      {...props}
    />
  );
};

const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        'px-6 py-4 border-t border-neutral-100',
        className
      )}
      {...props}
    />
  );
};

export { CardHeader, CardTitle, CardContent, CardFooter };

export default Card;