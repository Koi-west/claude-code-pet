import Store from 'electron-store';

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
  customTheme: Record<string, unknown>;

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

const DEFAULT_SHOW_DASHBOARD_SHORTCUT = 'CmdOrCtrl+Shift+K';
const DEFAULT_TOGGLE_CHAT_SHORTCUT = 'CmdOrCtrl+Shift+C';

export class SettingsStore {
  private store: Store<AppSettings>;

  constructor() {
    this.store = new Store<AppSettings>({
      defaults: defaultSettings,
      name: 'settings',
    });
  }

  private normalizeSettings(settings: AppSettings): AppSettings {
    let normalized = settings;
    let changed = false;

    const model = settings.model as string;
    const modelMap: Record<string, AppSettings['model']> = {
      'sonnet-4.5': 'sonnet',
      'opus-4.5': 'opus',
      sonnet: 'sonnet',
      opus: 'opus',
      haiku: 'haiku',
    };
    const nextModel = modelMap[model] || 'sonnet';
    if (nextModel !== settings.model) {
      normalized = { ...normalized, model: nextModel };
      changed = true;
    }

    const showDashboardShortcut = (normalized.showDashboardShortcut || '').trim();
    const toggleChatShortcut = (normalized.toggleChatShortcut || '').trim();
    let nextShowDashboard = showDashboardShortcut || DEFAULT_SHOW_DASHBOARD_SHORTCUT;
    let nextToggleChat = toggleChatShortcut || DEFAULT_TOGGLE_CHAT_SHORTCUT;
    if (nextShowDashboard === 'Shift+Control') {
      nextShowDashboard = DEFAULT_SHOW_DASHBOARD_SHORTCUT;
    }
    if (nextToggleChat === nextShowDashboard) {
      nextToggleChat = nextShowDashboard === DEFAULT_SHOW_DASHBOARD_SHORTCUT
        ? DEFAULT_TOGGLE_CHAT_SHORTCUT
        : DEFAULT_SHOW_DASHBOARD_SHORTCUT;
    }
    if (nextShowDashboard !== normalized.showDashboardShortcut ||
      nextToggleChat !== normalized.toggleChatShortcut) {
      normalized = {
        ...normalized,
        showDashboardShortcut: nextShowDashboard,
        toggleChatShortcut: nextToggleChat,
      };
      changed = true;
    }

    const minWidth = 520;
    const minHeight = 320;
    if (normalized.windowWidth < minWidth || normalized.windowHeight < minHeight) {
      normalized = {
        ...normalized,
        windowWidth: Math.max(minWidth, normalized.windowWidth),
        windowHeight: Math.max(minHeight, normalized.windowHeight),
      };
      changed = true;
    }

    if (normalized.maxThinkingTokens < 1024) {
      normalized = { ...normalized, maxThinkingTokens: 1024 };
      changed = true;
    }

    return changed ? normalized : settings;
  }

  // Get all settings
  getSettings(): AppSettings {
    const settings = this.normalizeSettings(this.store.store);
    if (settings !== this.store.store) {
      this.store.set(settings);
    }
    return settings;
  }

  // Get a specific setting
  get<T extends keyof AppSettings>(key: T): AppSettings[T] {
    return this.store.get(key, defaultSettings[key]);
  }

  // Update settings
  updateSettings(settings: Partial<AppSettings>): AppSettings {
    const currentSettings = this.getSettings();
    const newSettings = this.normalizeSettings({ ...currentSettings, ...settings });
    this.store.set(newSettings);
    return newSettings;
  }

  // Update a specific setting
  set<T extends keyof AppSettings>(key: T, value: AppSettings[T]): AppSettings {
    const currentSettings = this.getSettings();
    const nextSettings = this.normalizeSettings({ ...currentSettings, [key]: value });
    this.store.set(nextSettings);
    return nextSettings;
  }

  // Reset to default settings
  resetSettings(): AppSettings {
    this.store.reset();
    return this.getSettings();
  }

  // Save settings (for compatibility)
  saveSettings(settings: AppSettings): void {
    this.store.set(settings);
  }
}

// Singleton instance
export const settingsStore = new SettingsStore();
