import { useCallback, useEffect, useState } from 'react';
import { ipcRenderer } from 'electron';
import type { CloudCodeConnection, CloudCodeSnapshot } from '@types';
import { IPC_CHANNELS } from '@types';

type ConnectionUpdates = {
  baseUrl: string;
  authToken: string;
  timeoutMs: string;
};

export function useCloudCode() {
  const [snapshot, setSnapshot] = useState<CloudCodeSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const result = await ipcRenderer.invoke(IPC_CHANNELS.CLOUD_CODE_GET_SNAPSHOT);
      setSnapshot(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load Cloud Code data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const saveConnection = useCallback(async (updates: ConnectionUpdates): Promise<CloudCodeConnection | null> => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.CLOUD_CODE_SAVE_CONNECTION, updates);
      setSnapshot((prev) => (prev ? { ...prev, connection: result } : prev));
      setError(null);
      return result as CloudCodeConnection;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save connection');
      return null;
    }
  }, []);

  const saveEnv = useCallback(async (envLines: string): Promise<CloudCodeConnection | null> => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.CLOUD_CODE_SAVE_ENV, { envLines });
      setSnapshot((prev) => (prev ? { ...prev, connection: result } : prev));
      setError(null);
      return result as CloudCodeConnection;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save environment');
      return null;
    }
  }, []);

  const setPluginEnabled = useCallback(async (pluginId: string, enabled: boolean): Promise<boolean> => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.CLOUD_CODE_SET_PLUGIN_ENABLED, { pluginId, enabled });
      if (result?.success) {
        setSnapshot((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            plugins: prev.plugins.map((plugin) =>
              plugin.id === pluginId ? { ...plugin, enabled } : plugin
            ),
            settingsLocalPath: result.settingsLocalPath ?? prev.settingsLocalPath,
          };
        });
        setError(null);
        return true;
      }
      setError(result?.error || 'Failed to update plugin');
      return false;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update plugin');
      return false;
    }
  }, []);

  const saveMcp = useCallback(async (raw: string): Promise<boolean> => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.CLOUD_CODE_SAVE_MCP, { raw });
      if (result?.success) {
        await refresh();
        return true;
      }
      setError(result?.error || 'Failed to save MCP config');
      return false;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save MCP config');
      return false;
    }
  }, [refresh]);

  return {
    snapshot,
    loading,
    error,
    refresh,
    saveConnection,
    saveEnv,
    setPluginEnabled,
    saveMcp,
  };
}
