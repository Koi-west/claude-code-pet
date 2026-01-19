import React, { useState } from 'react';
import { Brain, ChevronDown } from 'lucide-react';

interface ThinkingBlockProps {
  content: string;
}

export function ThinkingBlock({ content }: ThinkingBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="mt-2">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-700 transition-colors"
      >
        <Brain className="w-4 h-4" />
        <span>Thinking</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
      </button>

      {isExpanded && (
        <div className="mt-2 p-3 bg-neutral-100 rounded-lg text-sm text-neutral-700">
          {content}
        </div>
      )}
    </div>
  );
}
