import { useCallback, useEffect, useState } from 'react';
import { ipcRenderer } from 'electron';
import { IPC_CHANNELS, GuiAgentConfig, SidecarStatus } from '@types';

interface ConnectionTestResult {
  success: boolean;
  error?: string;
  health?: any;
}

interface SaveResult {
  success: boolean;
  error?: string;
}

export function useGuiAgentConfig() {
  const [config, setConfig] = useState<GuiAgentConfig | null>(null);
  const [status, setStatus] = useState<SidecarStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadConfig = useCallback(async () => {
    try {
      setLoading(true);
      const result = await ipcRenderer.invoke(IPC_CHANNELS.GUI_AGENT_GET_CONFIG);
      if (result?.config) {
        setConfig(result.config as GuiAgentConfig);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load GUI Agent config');
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SIDECAR_GET_STATUS);
      if (result?.status) {
        setStatus(result.status as SidecarStatus);
      }
    } catch (err) {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    loadConfig();
    refreshStatus();
  }, [loadConfig, refreshStatus]);

  useEffect(() => {
    const handleStatus = (_event: unknown, payload: SidecarStatus) => {
      if (payload) {
        setStatus(payload);
      }
    };

    ipcRenderer.on(IPC_CHANNELS.SIDECAR_STATUS, handleStatus);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.SIDECAR_STATUS, handleStatus);
    };
  }, []);

  const saveConfig = useCallback(async (nextConfig: GuiAgentConfig, options?: { syncVlm?: boolean }): Promise<SaveResult> => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.GUI_AGENT_SET_CONFIG, nextConfig, options);
      if (result?.success) {
        await loadConfig();
        setError(null);
        return { success: true };
      }
      const message = result?.error || 'Failed to save GUI Agent config';
      setError(message);
      return { success: false, error: message };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save GUI Agent config';
      setError(message);
      return { success: false, error: message };
    }
  }, []);

  const testConnection = useCallback(async (override?: GuiAgentConfig): Promise<ConnectionTestResult> => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.GUI_AGENT_TEST_CONNECTION, override);
      return result as ConnectionTestResult;
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : 'Failed to test connection' };
    }
  }, []);

  const startSidecar = useCallback(async () => {
    const result = await ipcRenderer.invoke(IPC_CHANNELS.SIDECAR_START);
    if (result?.status) {
      setStatus(result.status as SidecarStatus);
    }
    return result;
  }, []);

  const stopSidecar = useCallback(async () => {
    const result = await ipcRenderer.invoke(IPC_CHANNELS.SIDECAR_STOP);
    if (result?.status) {
      setStatus(result.status as SidecarStatus);
    }
    return result;
  }, []);

  return {
    config,
    status,
    loading,
    error,
    reload: loadConfig,
    refreshStatus,
    saveConfig,
    testConnection,
    startSidecar,
    stopSidecar,
  };
}
