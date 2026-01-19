import React from 'react';
import { Slider } from '@renderer/shared/components';

interface FontSizeControlProps {
  fontSize: number;
  onFontSizeChange: (size: number) => void;
}

export function FontSizeControl({ fontSize, onFontSizeChange }: FontSizeControlProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-neutral-900">
        Font Size: {fontSize}px
      </h3>

      <div className="bg-neutral-50 rounded-lg p-4">
        <Slider
          value={fontSize}
          min={12}
          max={20}
          step={1}
          onChange={onFontSizeChange}
          className="w-full"
        />
        <p className="text-xs text-neutral-500 mt-2">
          Adjust the font size for better readability.
        </p>
      </div>

      <div className="flex justify-between text-sm text-neutral-600">
        <span>Small</span>
        <span>Medium</span>
        <span>Large</span>
      </div>
    </div>
  );
}