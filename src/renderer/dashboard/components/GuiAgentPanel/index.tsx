import React, { useEffect, useMemo, useState } from 'react';
import { Badge, Button, Card, CardContent, CardFooter, CardHeader, CardTitle, Input, Switch } from '@renderer/shared/components';
import { GuiAgentConfig } from '@types';
import { useGuiAgentConfig } from '../../hooks/useGuiAgentConfig';

type ProviderOption = {
  value: GuiAgentConfig['vlmProvider'];
  label: string;
  hint: string;
};

const PROVIDER_OPTIONS: ProviderOption[] = [
  { value: 'static_openai', label: 'OpenAI-compatible', hint: 'Use any OpenAI-style VLM endpoint.' },
  { value: 'ollama', label: 'Ollama', hint: 'Local VLM via Ollama.' },
];

export function GuiAgentPanel() {
  const {
    config,
    status,
    loading,
    error,
    saveConfig,
    testConnection,
    startSidecar,
    stopSidecar,
    refreshStatus,
  } = useGuiAgentConfig();

  const [draft, setDraft] = useState<GuiAgentConfig | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; error?: string } | null>(null);

  useEffect(() => {
    if (config) {
      setDraft(config);
    }
  }, [config]);

  const statusBadge = useMemo(() => {
    if (!status) {
      return { label: 'Unknown', variant: 'neutral' as const };
    }
    if (status.isRunning && status.health) {
      return { label: 'Healthy', variant: 'success' as const };
    }
    if (status.isRunning) {
      return { label: 'Starting', variant: 'warning' as const };
    }
    return { label: 'Stopped', variant: 'neutral' as const };
  }, [status]);

  const updateDraft = <K extends keyof GuiAgentConfig>(key: K, value: GuiAgentConfig[K]) => {
    setDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const handleSave = async (syncVlm: boolean) => {
    if (!draft) return;
    setIsSaving(true);
    const result = await saveConfig(draft, { syncVlm });
    setIsSaving(false);
    if (!result.success) {
      setTestResult({ success: false, error: result.error || 'Failed to save settings' });
    } else if (syncVlm) {
      setTestResult({ success: true });
    }
  };

  const handleTestConnection = async () => {
    if (!draft) return;
    setIsTesting(true);
    const result = await testConnection(draft);
    setTestResult({ success: result.success, error: result.error });
    setIsTesting(false);
  };

  if (loading || !draft) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-neutral-600">Loading GUI Agent settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-lg border border-error-200 bg-error-50 px-4 py-3 text-sm text-error-600">
          {error}
        </div>
      )}

      {testResult && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            testResult.success
              ? 'border-success-200 bg-success-50 text-success-700'
              : 'border-error-200 bg-error-50 text-error-600'
          }`}
        >
          {testResult.success ? 'Connection check passed.' : `Connection failed: ${testResult.error || 'Unknown error'}`}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card variant="outline">
          <CardHeader className="flex items-center justify-between">
            <div>
              <CardTitle>Sidecar Runtime</CardTitle>
              <p className="text-sm text-neutral-500 mt-1">Manage the embedded GUI Agent service.</p>
            </div>
            <Badge variant={statusBadge.variant}>{statusBadge.label}</Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-neutral-700">Sidecar URL</label>
              <Input
                className="mt-2"
                value={draft.sidecarUrl}
                onChange={(event) => updateDraft('sidecarUrl', event.target.value)}
                placeholder="http://127.0.0.1:8787"
              />
              <p className="text-xs text-neutral-500 mt-2">
                Use a local URL for embedded runs or point to a remote sidecar.
              </p>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-neutral-200 px-4 py-3">
              <div>
                <p className="text-sm font-medium text-neutral-800">Auto-start sidecar</p>
                <p className="text-xs text-neutral-500">Launch the GUI Agent automatically with Miko.</p>
              </div>
              <Switch
                checked={draft.autoStartSidecar}
                onCheckedChange={(value) => updateDraft('autoStartSidecar', value)}
              />
            </div>

            <div className="rounded-lg border border-neutral-200 px-4 py-3 text-sm text-neutral-600 space-y-1">
              <div>Running: {status?.isRunning ? 'Yes' : 'No'}</div>
              <div>Health: {status?.health ? 'OK' : 'Unknown'}</div>
              <div>Port: {status?.port ?? draft.sidecarPort ?? '—'}</div>
            </div>
          </CardContent>
          <CardFooter className="flex flex-wrap gap-2">
            <Button variant="primary" onClick={startSidecar}>
              Start Sidecar
            </Button>
            <Button variant="outline" onClick={stopSidecar}>
              Stop
            </Button>
            <Button variant="ghost" onClick={refreshStatus}>
              Refresh Status
            </Button>
            <Button variant="outline" isLoading={isTesting} onClick={handleTestConnection}>
              Test Connection
            </Button>
          </CardFooter>
        </Card>

        <Card variant="outline">
          <CardHeader>
            <CardTitle>VLM Provider</CardTitle>
            <p className="text-sm text-neutral-500 mt-1">Configure the vision model used by the GUI Agent.</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-neutral-700">Provider</label>
              <select
                className="mt-2 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200"
                value={draft.vlmProvider}
                onChange={(event) => updateDraft('vlmProvider', event.target.value as GuiAgentConfig['vlmProvider'])}
              >
                {PROVIDER_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <p className="text-xs text-neutral-500 mt-2">
                {PROVIDER_OPTIONS.find((option) => option.value === draft.vlmProvider)?.hint}
              </p>
            </div>

            <div>
              <label className="text-sm font-medium text-neutral-700">Base URL</label>
              <Input
                className="mt-2"
                value={draft.vlmBaseUrl}
                onChange={(event) => updateDraft('vlmBaseUrl', event.target.value)}
                placeholder="https://api.openai.com/v1"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-neutral-700">Model</label>
              <Input
                className="mt-2"
                value={draft.vlmModel}
                onChange={(event) => updateDraft('vlmModel', event.target.value)}
                placeholder="gpt-4o-mini"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-neutral-700">API Key (optional)</label>
              <Input
                className="mt-2"
                type="password"
                value={draft.vlmApiKey || ''}
                onChange={(event) => updateDraft('vlmApiKey', event.target.value)}
                placeholder="sk-..."
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-wrap gap-2">
            <Button variant="primary" isLoading={isSaving} onClick={() => handleSave(false)}>
              Save Settings
            </Button>
            <Button variant="outline" isLoading={isSaving} onClick={() => handleSave(true)}>
              Save & Sync VLM
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
