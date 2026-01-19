import React, { useState } from 'react';
import { Button } from '@renderer/shared/components';
import { ApiKeySection } from './ApiKeySection';
import { ModelSelector } from './ModelSelector';
import { ParametersSection } from './ParametersSection';
import { useSettings } from '../../hooks/useSettings';

type Model = 'sonnet' | 'opus' | 'haiku';

export function SettingsPanel() {
  const { settings, updateSettings, saveSettings, resetSettings } = useSettings();

  const [apiKey, setApiKey] = useState(settings.apiKey);
  const [model, setModel] = useState<Model>(settings.model as Model);
  const [temperature, setTemperature] = useState(settings.temperature);
  const [maxThinkingTokens, setMaxThinkingTokens] = useState(settings.maxThinkingTokens);
  const [systemPrompt, setSystemPrompt] = useState(settings.systemPrompt);

  const handleSave = () => {
    updateSettings({
      apiKey,
      model,
      temperature,
      maxThinkingTokens,
      systemPrompt,
    });
    saveSettings();
  };

  const handleReset = async () => {
    const defaultSettings = await resetSettings();
    setApiKey(defaultSettings.apiKey);
    setModel(defaultSettings.model as Model);
    setTemperature(defaultSettings.temperature);
    setMaxThinkingTokens(defaultSettings.maxThinkingTokens);
    setSystemPrompt(defaultSettings.systemPrompt);
  };

  return (
    <div className="space-y-8">
      <ApiKeySection
        apiKey={apiKey}
        onApiKeyChange={setApiKey}
        onSave={handleSave}
        onReset={handleReset}
      />

      <ModelSelector
        selectedModel={model}
        onModelChange={setModel}
      />

      <ParametersSection
        temperature={temperature}
        onTemperatureChange={setTemperature}
        maxThinkingTokens={maxThinkingTokens}
        onMaxThinkingTokensChange={setMaxThinkingTokens}
        systemPrompt={systemPrompt}
        onSystemPromptChange={setSystemPrompt}
      />

      <div className="flex gap-2">
        <Button variant="primary" onClick={handleSave}>
          Save All Settings
        </Button>
        <Button variant="outline" onClick={handleReset}>
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}
