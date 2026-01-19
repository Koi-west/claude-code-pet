import { useState, useEffect } from 'react';
import { ipcRenderer } from 'electron';
import type { ThemeOverrides } from '@renderer/shared/design-system';

export interface AppSettings {
  // Claude Settings
  apiKey: string;
  model: 'sonnet' | 'opus' | 'haiku';
  temperature: number;
  maxThinkingTokens: number;
  systemPrompt: string;

  // Appearance Settings
  theme: 'light' | 'dark' | 'custom';
  fontSize: number;
  animationSpeed: 'instant' | 'fast' | 'normal' | 'slow';
  alwaysOnTop: boolean;
  customTheme: ThemeOverrides;

  // Window Settings
  windowX: number;
  windowY: number;
  windowWidth: number;
  windowHeight: number;

  // Shortcuts
  showDashboardShortcut: string;
  toggleChatShortcut: string;
}

const defaultSettings: AppSettings = {
  // Claude Settings
  apiKey: '',
  model: 'sonnet',
  temperature: 0.7,
  maxThinkingTokens: 1024,
  systemPrompt: 'You are Miko, a friendly desktop pet with access to various tools.',

  // Appearance Settings
  theme: 'light',
  fontSize: 14,
  animationSpeed: 'normal',
  alwaysOnTop: true,
  customTheme: {},

  // Window Settings
  windowX: -1,
  windowY: -1,
  windowWidth: 520,
  windowHeight: 320,

  // Shortcuts
  showDashboardShortcut: 'CmdOrCtrl+Shift+K',
  toggleChatShortcut: 'CmdOrCtrl+Shift+C',
};

export function useSettings() {
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Load initial settings
    const loadSettings = async () => {
      try {
        setLoading(true);
        const loadedSettings = await ipcRenderer.invoke('settings:get');
        setSettings(loadedSettings);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load settings');
        console.error('Error loading settings:', err);
      } finally {
        setLoading(false);
      }
    };

    loadSettings();
  }, []);

  const updateSettings = async (newSettings: Partial<AppSettings>) => {
    try {
      const updatedSettings = await ipcRenderer.invoke('settings:update', newSettings);
      setSettings(updatedSettings);
      setError(null);
      return updatedSettings;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update settings');
      console.error('Error updating settings:', err);
      return settings;
    }
  };

  const saveSettings = async () => {
    try {
      await ipcRenderer.invoke('settings:save', settings);
      setError(null);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
      console.error('Error saving settings:', err);
      return false;
    }
  };

  const resetSettings = async () => {
    try {
      const resetSettings = await ipcRenderer.invoke('settings:reset');
      setSettings(resetSettings);
      setError(null);
      return resetSettings;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset settings');
      console.error('Error resetting settings:', err);
      return settings;
    }
  };

  const setSetting = async <T extends keyof AppSettings>(key: T, value: AppSettings[T]) => {
    try {
      const updatedSettings = await ipcRenderer.invoke('settings:set', key, value);
      setSettings(updatedSettings);
      setError(null);
      return updatedSettings;
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to set ${key}`);
      console.error(`Error setting ${key}:`, err);
      return settings;
    }
  };

  return {
    settings,
    loading,
    error,
    updateSettings,
    saveSettings,
    resetSettings,
    setSetting,
  };
}
