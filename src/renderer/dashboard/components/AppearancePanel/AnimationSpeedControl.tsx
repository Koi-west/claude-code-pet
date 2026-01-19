import React from 'react';
import { Zap, FastForward, Play, Clock } from 'lucide-react';

type AnimationSpeed = 'instant' | 'fast' | 'normal' | 'slow';

interface AnimationSpeedControlProps {
  speed: AnimationSpeed;
  onSpeedChange: (speed: AnimationSpeed) => void;
}

const speeds = [
  {
    id: 'instant' as const,
    name: 'Instant',
    description: 'No animations',
    icon: Zap,
  },
  {
    id: 'fast' as const,
    name: 'Fast',
    description: 'Quick animations',
    icon: FastForward,
  },
  {
    id: 'normal' as const,
    name: 'Normal',
    description: 'Balanced speed',
    icon: Play,
  },
  {
    id: 'slow' as const,
    name: 'Slow',
    description: 'Smooth animations',
    icon: Clock,
  },
];

export function AnimationSpeedControl({ speed, onSpeedChange }: AnimationSpeedControlProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-neutral-900">Animation Speed</h3>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {speeds.map((s) => (
          <button
            key={s.id}
            onClick={() => onSpeedChange(s.id)}
            className={`p-3 rounded-lg border-2 transition-all text-left ${
              speed === s.id
                ? 'border-primary-500 bg-primary-50'
                : 'border-neutral-200 hover:border-neutral-300'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <s.icon className="w-5 h-5 text-primary-600" />
              <span className="font-semibold text-neutral-900">{s.name}</span>
            </div>
            <p className="text-xs text-neutral-600">{s.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
