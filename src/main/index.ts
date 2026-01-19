import { app } from 'electron';
import { windowManager } from './windows/WindowManager';
import { initializeIPC, cleanupIPC } from './ipc';
import { shortcutManager } from './shortcuts/ShortcutManager';
import { settingsStore } from './storage/SettingsStore';

/**
 * Desktop Pet with Claude Code Integration
 * Main process entry point
 */

// Handle single instance lock
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    // Focus the pet window if a second instance is attempted
    const petWindow = windowManager.getWindow('pet');
    if (petWindow) {
      if (petWindow.isMinimized()) {
        petWindow.restore();
      }
      petWindow.focus();
    }
  });

  // App ready
  app.whenReady().then(async () => {
    // Show dock icon for debugging (normally hidden for desktop pet)
    // if (process.platform === 'darwin') {
    //   app.dock.hide();
    // }

    // Initialize IPC handlers with current working directory
    await initializeIPC(process.cwd());

    // Create the pet window
    windowManager.createWindow('pet');

    // Register global shortcuts
    shortcutManager.registerShortcuts(settingsStore.getSettings());

    // macOS: re-create window when dock icon is clicked
    app.on('activate', () => {
      if (windowManager.getAllWindows().length === 0) {
        windowManager.createWindow('pet');
      }
    });
  });

  // Prevent app from quitting when all windows are closed on macOS
  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      app.quit();
    }
  });

  // Cleanup before quitting
  app.on('before-quit', () => {
    shortcutManager.unregisterAll();
    cleanupIPC();
  });

  // Handle keyboard shortcuts globally
  app.on('browser-window-focus', () => {
    const petWindow = windowManager.getWindow('pet');
    if (petWindow) {
      petWindow.webContents.on('before-input-event', (_event, input) => {
        // Cmd/Ctrl+Q to quit
        const isCmdOrCtrl = process.platform === 'darwin' ? input.meta : input.control;
        if (isCmdOrCtrl && input.key.toLowerCase() === 'q') {
          app.quit();
        }

        // Escape to close window (optional)
        // if (input.key === 'Escape') {
        //   petWindow.close();
        // }
      });
    }
  });
}

// Log startup information
console.log('Desktop Pet starting...');
console.log(`Platform: ${process.platform}`);
console.log(`Node version: ${process.version}`);
console.log(`Electron version: ${process.versions.electron}`);
