import React, { useEffect, useMemo, useState } from 'react';
import { Badge, Button, Card, CardContent, CardFooter, CardHeader, CardTitle, Input, Switch } from '@renderer/shared/components';
import { useCloudCode } from '../../hooks/useCloudCode';

const EMPTY_MCP_JSON = '{\n  \"mcpServers\": {}\n}\n';
const ENV_PLACEHOLDER = 'ANTHROPIC_BASE_URL=http://127.0.0.1:5000\nANTHROPIC_AUTH_TOKEN=sk-...\nAPI_TIMEOUT_MS=300000';

function parsePort(value: string): string {
  if (!value) return '';
  try {
    const parsed = new URL(value);
    return parsed.port || '';
  } catch {
    return '';
  }
}

function applyPort(baseUrl: string, port: string): string {
  if (!baseUrl) return baseUrl;
  if (!port.trim()) return baseUrl;
  try {
    const parsed = new URL(baseUrl);
    parsed.port = port.trim();
    return parsed.toString().replace(/\/$/, '');
  } catch {
    return baseUrl;
  }
}

function formatEnvLines(env: Record<string, string>): string {
  const entries = Object.entries(env).filter(([key]) => key.trim().length > 0);
  entries.sort(([a], [b]) => a.localeCompare(b));
  return entries.map(([key, value]) => `${key}=${value}`).join('\n');
}

export function CloudCodePanel() {
  const { snapshot, loading, error, refresh, saveConnection, saveEnv, setPluginEnabled, saveMcp } = useCloudCode();
  const [connectionDraft, setConnectionDraft] = useState({ baseUrl: '', authToken: '', timeoutMs: '' });
  const [portDraft, setPortDraft] = useState('');
  const [envDraft, setEnvDraft] = useState('');
  const [mcpDraft, setMcpDraft] = useState(EMPTY_MCP_JSON);
  const [isEditingMcp, setIsEditingMcp] = useState(false);
  const [savingConnection, setSavingConnection] = useState(false);
  const [savingEnv, setSavingEnv] = useState(false);
  const [savingMcp, setSavingMcp] = useState(false);

  useEffect(() => {
    if (!snapshot) return;
    setConnectionDraft({
      baseUrl: snapshot.connection.baseUrl || '',
      authToken: snapshot.connection.authToken || '',
      timeoutMs: snapshot.connection.timeoutMs || '',
    });
    setPortDraft(parsePort(snapshot.connection.baseUrl || ''));
    setEnvDraft(formatEnvLines(snapshot.connection.env || {}));
    setMcpDraft(snapshot.mcp.raw || EMPTY_MCP_JSON);
  }, [snapshot]);

  const pluginGroups = useMemo(() => {
    if (!snapshot?.plugins) return { user: [], project: [], local: [] };
    return {
      user: snapshot.plugins.filter((plugin) => plugin.scope === 'user'),
      project: snapshot.plugins.filter((plugin) => plugin.scope === 'project'),
      local: snapshot.plugins.filter((plugin) => plugin.scope === 'local'),
    };
  }, [snapshot?.plugins]);

  const handleConnectionSave = async () => {
    setSavingConnection(true);
    const nextBaseUrl = applyPort(connectionDraft.baseUrl.trim(), portDraft);
    const result = await saveConnection({
      baseUrl: nextBaseUrl,
      authToken: connectionDraft.authToken,
      timeoutMs: connectionDraft.timeoutMs,
    });
    if (result) {
      setConnectionDraft({
        baseUrl: result.baseUrl || '',
        authToken: result.authToken || '',
        timeoutMs: result.timeoutMs || '',
      });
      setPortDraft(parsePort(result.baseUrl || ''));
      setEnvDraft(formatEnvLines(result.env || {}));
    }
    setSavingConnection(false);
  };

  const handleEnvSave = async () => {
    setSavingEnv(true);
    const result = await saveEnv(envDraft);
    if (result) {
      setConnectionDraft({
        baseUrl: result.baseUrl || '',
        authToken: result.authToken || '',
        timeoutMs: result.timeoutMs || '',
      });
      setPortDraft(parsePort(result.baseUrl || ''));
      setEnvDraft(formatEnvLines(result.env || {}));
    }
    setSavingEnv(false);
  };

  const handleMcpSave = async () => {
    setSavingMcp(true);
    const success = await saveMcp(mcpDraft);
    if (success) {
      setIsEditingMcp(false);
    }
    setSavingMcp(false);
  };

  if (loading || !snapshot) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-neutral-600">Loading Cloud Code settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-neutral-900">Cloud Code</h3>
          <p className="text-sm text-neutral-500">
            Sync settings with Claude Code and view local skills, plugins, and MCP servers.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refresh}>
          Refresh
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-error-200 bg-error-50 px-4 py-3 text-sm text-error-600">
          {error}
        </div>
      )}

      <Card variant="outline" className="rounded-2xl">
        <CardHeader className="flex flex-wrap items-start justify-between gap-3 border-neutral-100">
          <div>
            <CardTitle>Environment</CardTitle>
            <p className="text-sm text-neutral-500 mt-1">
              Stored in <span className="font-mono text-xs">{snapshot.connection.settingsPath}</span>
            </p>
          </div>
          <Badge variant="neutral" size="sm">
            {snapshot.connection.source === 'project' ? 'Project' : 'Home'}
          </Badge>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_280px]">
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700">Custom variables</label>
              <textarea
                value={envDraft}
                onChange={(event) => setEnvDraft(event.target.value)}
                className="w-full min-h-[160px] rounded-xl border border-neutral-200 bg-white p-3 text-xs font-mono"
                placeholder={ENV_PLACEHOLDER}
              />
              <p className="text-xs text-neutral-400">KEY=VALUE format, one per line.</p>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-neutral-700">Base URL</label>
                <Input
                  className="mt-2"
                  value={connectionDraft.baseUrl}
                  onChange={(event) => setConnectionDraft((prev) => ({ ...prev, baseUrl: event.target.value }))}
                  placeholder="http://127.0.0.1:5000"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-neutral-700">Port</label>
                <Input
                  className="mt-2"
                  value={portDraft}
                  onChange={(event) => setPortDraft(event.target.value)}
                  placeholder="5000"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-neutral-700">API Timeout (ms)</label>
                <Input
                  className="mt-2"
                  value={connectionDraft.timeoutMs}
                  onChange={(event) => setConnectionDraft((prev) => ({ ...prev, timeoutMs: event.target.value }))}
                  placeholder="300000"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-neutral-700">Auth Token / API Key</label>
                <Input
                  className="mt-2"
                  type="password"
                  value={connectionDraft.authToken}
                  onChange={(event) => setConnectionDraft((prev) => ({ ...prev, authToken: event.target.value }))}
                  placeholder="sk-..."
                />
              </div>
            </div>
          </div>
        </CardContent>
        <CardFooter className="flex flex-wrap gap-2 border-neutral-100">
          <Button variant="primary" isLoading={savingEnv} onClick={handleEnvSave}>
            Save Environment
          </Button>
          <Button variant="outline" isLoading={savingConnection} onClick={handleConnectionSave}>
            Save Connection
          </Button>
        </CardFooter>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card variant="outline" className="rounded-2xl">
          <CardHeader className="border-neutral-100">
            <CardTitle>Skills</CardTitle>
            <p className="text-sm text-neutral-500 mt-1">
              {snapshot.skills.length} skill{snapshot.skills.length === 1 ? '' : 's'} found in{' '}
              <span className="font-mono text-xs">{snapshot.skillsPath}</span>
            </p>
          </CardHeader>
          <CardContent className="space-y-3 max-h-[360px] overflow-y-auto">
            {snapshot.skills.length === 0 && (
              <div className="text-sm text-neutral-500">No skills found.</div>
            )}
            {snapshot.skills.map((skill) => (
              <div key={skill.id} className="rounded-xl border border-neutral-200 p-3 space-y-1 bg-white">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium text-neutral-900">{skill.name}</div>
                  <Badge variant="neutral" size="sm">User</Badge>
                </div>
                {skill.description && (
                  <div className="text-xs text-neutral-600">{skill.description}</div>
                )}
                <div className="text-[11px] text-neutral-400 font-mono break-all">{skill.path}</div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card variant="outline" className="rounded-2xl">
          <CardHeader className="border-neutral-100 flex items-start justify-between gap-3">
            <div>
              <CardTitle>Plugins</CardTitle>
              <p className="text-sm text-neutral-500 mt-1">
                Enabled plugins stored in <span className="font-mono text-xs">{snapshot.settingsLocalPath}</span>
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={refresh}>
              Refresh
            </Button>
          </CardHeader>
          <CardContent className="space-y-4 max-h-[360px] overflow-y-auto">
            {snapshot.plugins.length === 0 && (
              <div className="text-sm text-neutral-500">No Claude Code plugins installed.</div>
            )}

            {(['project', 'local', 'user'] as const).map((scope) => (
              <div key={scope} className="space-y-2">
                {pluginGroups[scope].length > 0 && (
                  <div className="text-xs uppercase tracking-wide text-neutral-400">{scope} plugins</div>
                )}
                {pluginGroups[scope].map((plugin) => {
                  const statusColor = plugin.status === 'available'
                    ? (plugin.enabled ? 'bg-success-500' : 'bg-neutral-300')
                    : 'bg-warning-500';
                  return (
                    <div key={plugin.id} className="rounded-xl border border-neutral-200 p-3 space-y-2 bg-white">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <span className={`mt-1 w-2.5 h-2.5 rounded-full ${statusColor}`} />
                          <div>
                            <div className="text-sm font-medium text-neutral-900">{plugin.name}</div>
                            <div className="text-xs text-neutral-500">{plugin.description || plugin.id}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {plugin.status !== 'available' && (
                            <Badge variant="warning" size="sm">{plugin.status}</Badge>
                          )}
                          <Switch
                            checked={plugin.enabled}
                            onCheckedChange={(value) => setPluginEnabled(plugin.id, value)}
                            disabled={plugin.status !== 'available'}
                          />
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 text-[11px] text-neutral-400 font-mono">
                        <span>{plugin.version || 'unknown'}</span>
                        <span>{plugin.scope}</span>
                        <span className="break-all">{plugin.installPath}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card variant="outline" className="rounded-2xl">
        <CardHeader className="flex items-start justify-between gap-3 border-neutral-100">
          <div>
            <CardTitle>MCP Servers</CardTitle>
            <p className="text-sm text-neutral-500 mt-1">
              Project file: <span className="font-mono text-xs">{snapshot.mcp.path}</span>
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setIsEditingMcp((prev) => !prev)}>
            {isEditingMcp ? 'Hide Editor' : 'Edit JSON'}
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {snapshot.mcp.servers.length === 0 ? (
            <div className="text-sm text-neutral-500">No MCP servers configured.</div>
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {snapshot.mcp.servers.map((server) => (
                <div key={server.name} className="rounded-xl border border-neutral-200 p-3 space-y-1 bg-white">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-medium text-neutral-900">{server.name}</div>
                    <Badge variant="neutral" size="sm">{server.type}</Badge>
                  </div>
                  <div className="text-xs text-neutral-600 break-all">{server.summary}</div>
                </div>
              ))}
            </div>
          )}

          {isEditingMcp && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700">MCP JSON</label>
              <textarea
                value={mcpDraft}
                onChange={(event) => setMcpDraft(event.target.value)}
                className="w-full min-h-[220px] rounded-xl border border-neutral-200 p-3 text-xs font-mono"
              />
              <div className="flex flex-wrap gap-2">
                <Button variant="primary" isLoading={savingMcp} onClick={handleMcpSave}>
                  Save MCP JSON
                </Button>
                <Button variant="outline" onClick={() => setMcpDraft(snapshot.mcp.raw || EMPTY_MCP_JSON)}>
                  Reset
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

    </div>
  );
}
