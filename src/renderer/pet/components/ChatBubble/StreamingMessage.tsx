import React from 'react';

interface StreamingMessageProps {
  content: string;
  thinkingContent?: string;
}

export function StreamingMessage({ content, thinkingContent }: StreamingMessageProps) {
  return (
    <div className="space-y-2">
      <div className="prose prose-sm max-w-none text-neutral-800">
        {content}
        <span className="animate-pulse">|</span>
      </div>

      {thinkingContent && (
        <div className="text-sm text-neutral-500 italic">
          {thinkingContent}
        </div>
      )}
    </div>
  );
}
