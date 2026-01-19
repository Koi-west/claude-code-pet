import React from 'react';

export const Button = ({ variant = 'ghost', size = 'icon', className = '', children, ...props }) => {
  return (
    <button
      className={`px-4 py-2 rounded-full ${variant === 'ghost' ? 'bg-transparent hover:bg-transparent' : ''} ${size === 'icon' ? 'w-10 h-10 p-0' : ''} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;