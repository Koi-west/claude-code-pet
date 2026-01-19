import React from 'react';
import { Slider } from '@renderer/shared/components';

interface ParametersSectionProps {
  temperature: number;
  onTemperatureChange: (value: number) => void;
  maxThinkingTokens: number;
  onMaxThinkingTokensChange: (value: number) => void;
  systemPrompt: string;
  onSystemPromptChange: (value: string) => void;
}

export function ParametersSection({
  temperature,
  onTemperatureChange,
  maxThinkingTokens,
  onMaxThinkingTokensChange,
  systemPrompt,
  onSystemPromptChange,
}: ParametersSectionProps) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-neutral-900">Advanced Parameters</h3>

      <div className="bg-neutral-50 rounded-lg p-4 space-y-4">
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-2">
            Temperature: {temperature.toFixed(1)}
          </label>
          <Slider
            value={temperature}
            min={0}
            max={1}
            step={0.1}
            onChange={onTemperatureChange}
            className="w-full"
          />
          <p className="text-xs text-neutral-500 mt-1">
            Lower values make responses more deterministic, higher values more creative.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-2">
            Max Thinking Tokens: {maxThinkingTokens}
          </label>
          <Slider
            value={maxThinkingTokens}
            min={1024}
            max={4096}
            step={256}
            onChange={onMaxThinkingTokensChange}
            className="w-full"
          />
          <p className="text-xs text-neutral-500 mt-1">
            Maximum number of tokens for Claude's thinking process.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-2">
            System Prompt
          </label>
          <textarea
            value={systemPrompt}
            onChange={(e) => onSystemPromptChange(e.target.value)}
            rows={4}
            className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            placeholder="You are Miko, a friendly desktop pet..."
          />
          <p className="text-xs text-neutral-500 mt-1">
            Customize Claude's personality and behavior.
          </p>
        </div>
      </div>
    </div>
  );
}
