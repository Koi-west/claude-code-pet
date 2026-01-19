import React from 'react';
import { BookOpen, Brain, Zap } from 'lucide-react';

type Model = 'sonnet' | 'opus' | 'haiku';

interface ModelSelectorProps {
  selectedModel: Model;
  onModelChange: (model: Model) => void;
}

const models = [
  {
    id: 'sonnet' as const,
    name: 'Sonnet',
    description: 'Balanced performance and speed for most tasks',
    icon: BookOpen,
  },
  {
    id: 'opus' as const,
    name: 'Opus',
    description: 'Most capable model for complex tasks',
    icon: Brain,
  },
  {
    id: 'haiku' as const,
    name: 'Haiku',
    description: 'Fastest model for simple tasks',
    icon: Zap,
  },
];

export function ModelSelector({ selectedModel, onModelChange }: ModelSelectorProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-neutral-900">Model Selection</h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {models.map((model) => (
          <button
            key={model.id}
            onClick={() => onModelChange(model.id)}
            className={`p-4 rounded-lg border-2 transition-all text-left ${
              selectedModel === model.id
                ? 'border-primary-500 bg-primary-50'
                : 'border-neutral-200 hover:border-neutral-300'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <model.icon className="w-5 h-5 text-primary-600" />
              <span className="font-semibold text-neutral-900">{model.name}</span>
            </div>
            <p className="text-sm text-neutral-600">{model.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
