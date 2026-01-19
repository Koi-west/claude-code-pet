import React from 'react';

export const Input = ({ value, onChange, placeholder, className = '', ...props }) => {
  return (
    <input
      type="text"
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className={`px-4 py-2 bg-transparent border-none text-gray-700 placeholder:text-gray-500 focus:ring-0 focus:outline-none text-lg ${className}`}
      {...props}
    />
  );
};

export default Input;