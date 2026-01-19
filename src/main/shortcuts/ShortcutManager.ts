import { globalShortcut } from 'electron';
import { AppSettings } from '../storage/SettingsStore';
import { windowManager } from '../windows/WindowManager';

export class ShortcutManager {
  // Cache current shortcut values to avoid redundant re-registration
  private currentShowDashboard: string | null = null;
  private currentToggleChat: string | null = null;
  private currentRegisteredDashboard: string | null = null;
  private currentRegisteredToggleChat: string | null = null;

  registerShortcuts(settings: AppSettings): void {
    const showDashboard = (settings.showDashboardShortcut || '').trim();
    const toggleChat = (settings.toggleChatShortcut || '').trim();

    // Skip if shortcuts haven't changed
    if (showDashboard === this.currentShowDashboard &&
        toggleChat === this.currentToggleChat) {
      return;
    }

    if (this.currentRegisteredDashboard) {
      globalShortcut.unregister(this.currentRegisteredDashboard);
    }
    if (this.currentRegisteredToggleChat) {
      globalShortcut.unregister(this.currentRegisteredToggleChat);
    }

    let registeredDashboard: string | null = null;
    if (showDashboard) {
      try {
        const registered = globalShortcut.register(showDashboard, () => {
          windowManager.toggleWindow('dashboard');
        });
        if (!registered) {
          const fallback = 'CommandOrControl+Shift+K';
          if (globalShortcut.register(fallback, () => windowManager.toggleWindow('dashboard'))) {
            registeredDashboard = fallback;
          }
        } else {
          registeredDashboard = showDashboard;
        }
      } catch (error) {
        console.warn('Failed to register dashboard shortcut, falling back:', error);
        try {
          const fallback = 'CommandOrControl+Shift+K';
          if (globalShortcut.register(fallback, () => windowManager.toggleWindow('dashboard'))) {
            registeredDashboard = fallback;
          }
        } catch (fallbackError) {
          console.warn('Failed to register fallback dashboard shortcut:', fallbackError);
        }
      }
    }

    let registeredToggleChat: string | null = null;
    if (toggleChat) {
      try {
        const registered = globalShortcut.register(toggleChat, () => {
          windowManager.toggleWindow('pet');
        });
        if (registered) {
          registeredToggleChat = toggleChat;
        }
      } catch (error) {
        console.warn('Failed to register toggle chat shortcut:', error);
      }
    }

    this.currentShowDashboard = showDashboard;
    this.currentToggleChat = toggleChat;
    this.currentRegisteredDashboard = registeredDashboard;
    this.currentRegisteredToggleChat = registeredToggleChat;
  }

  unregisterAll(): void {
    globalShortcut.unregisterAll();
  }
}

export const shortcutManager = new ShortcutManager();
