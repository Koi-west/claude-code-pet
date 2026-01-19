import React, { useState } from 'react';
import { ToolCallInfo } from '@renderer/shared/types';
import { Code2, ChevronDown, CheckCircle } from 'lucide-react';

interface ToolCallDisplayProps {
  toolCalls: ToolCallInfo[];
}

export function ToolCallDisplay({ toolCalls }: ToolCallDisplayProps) {
  const [expandedIds, setExpandedIds] = useState<string[]>([]);

  const toggleExpanded = (id: string) => {
    setExpandedIds(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  return (
    <div className="mt-3 space-y-2">
      {toolCalls.map((toolCall) => {
        const isExpanded = expandedIds.includes(toolCall.id);
        return (
          <div key={toolCall.id} className="border border-neutral-200 rounded-lg overflow-hidden">
            <div
              className="flex items-center justify-between p-2 bg-neutral-50 cursor-pointer hover:bg-neutral-100 transition-colors"
              onClick={() => toggleExpanded(toolCall.id)}
            >
              <div className="flex items-center gap-2">
                <Code2 className="w-4 h-4 text-neutral-600" />
                <span className="text-sm font-medium text-neutral-800">{toolCall.name}</span>
              </div>
              <div className="flex items-center gap-2">
                {toolCall.result && (
                  <CheckCircle className="w-4 h-4 text-success-500" />
                )}
                <ChevronDown className={`w-4 h-4 text-neutral-500 transition-transform ${
                  isExpanded ? 'rotate-180' : ''
                }`} />
              </div>
            </div>

            {isExpanded && (
              <div className="p-3 bg-white">
                <div className="mb-2">
                  <h4 className="text-xs font-medium text-neutral-500">Input</h4>
                  <pre className="mt-1 p-2 bg-neutral-50 rounded text-xs text-neutral-700 overflow-x-auto">
                    {JSON.stringify(toolCall.input, null, 2)}
                  </pre>
                </div>

                {toolCall.result && (
                  <div>
                    <h4 className="text-xs font-medium text-neutral-500">Output</h4>
                    <pre className="mt-1 p-2 bg-neutral-50 rounded text-xs text-neutral-700 overflow-x-auto">
                      {toolCall.result}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
