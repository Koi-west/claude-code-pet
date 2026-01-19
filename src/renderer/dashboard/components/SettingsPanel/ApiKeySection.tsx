import React, { useState } from 'react';
import { Input } from '@renderer/shared/components';
import { Button } from '@renderer/shared/components';
import { Eye, EyeOff } from 'lucide-react';

interface ApiKeySectionProps {
  apiKey: string;
  onApiKeyChange: (value: string) => void;
  onSave: () => void;
  onReset: () => void;
}

export function ApiKeySection({
  apiKey,
  onApiKeyChange,
  onSave,
  onReset,
}: ApiKeySectionProps) {
  const [showApiKey, setShowApiKey] = useState(false);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-neutral-900">API Key Configuration</h3>

      <div className="bg-neutral-50 rounded-lg p-4">
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Claude API Key
            </label>
            <div className="relative">
              <Input
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => onApiKeyChange(e.target.value)}
                placeholder="sk-ant-api03-..."
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-500 hover:text-neutral-700"
              >
                {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-neutral-500 mt-1">
              Your API key is stored securely in your local system.
            </p>
          </div>

          <div className="flex gap-2">
            <Button variant="primary" onClick={onSave}>
              Save API Key
            </Button>
            <Button variant="outline" onClick={onReset}>
              Reset
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}