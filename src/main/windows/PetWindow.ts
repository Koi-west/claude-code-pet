import { BrowserWindow, screen, app } from 'electron';
import * as path from 'path';
import { AppSettings } from '../storage/SettingsStore';
import { getAppIconPath } from '../utils/appIcon';

export interface PetWindowOverrides {
  width?: number;
  height?: number;
  x?: number;
  y?: number;
}

export class PetWindow {
  private settings: AppSettings;

  constructor(settings: AppSettings) {
    this.settings = settings;
  }

  create(overrides: PetWindowOverrides = {}): BrowserWindow {
    const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

    const minWidth = 520;
    const minHeight = 320;
    const windowWidth = Math.max(minWidth, overrides.width ?? this.settings.windowWidth ?? minWidth);
    const windowHeight = Math.max(minHeight, overrides.height ?? this.settings.windowHeight ?? minHeight);

    const margin = 24;
    const defaultX = Math.max(margin, screenWidth - windowWidth - margin);
    const defaultY = Math.max(margin, screenHeight - windowHeight - margin);

    const storedX = typeof this.settings.windowX === 'number' ? this.settings.windowX : null;
    const storedY = typeof this.settings.windowY === 'number' ? this.settings.windowY : null;
    const iconPath = getAppIconPath();

    const win = new BrowserWindow({
      width: windowWidth,
      height: windowHeight,
      x: overrides.x ?? (storedX !== null && storedX >= 0 ? storedX : defaultX),
      y: overrides.y ?? (storedY !== null && storedY >= 0 ? storedY : defaultY),
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false,
      },
      transparent: true,
      frame: false,
      alwaysOnTop: this.settings.alwaysOnTop ?? true,
      resizable: false,
      skipTaskbar: true,
      fullscreenable: false,
      type: process.platform === 'darwin' ? 'panel' : 'normal',
      backgroundColor: 'rgba(0, 0, 0, 0)',
      hasShadow: false,
      icon: iconPath ?? undefined,
    });

    // Load pet window HTML
    const appRoot = app.getAppPath();
    const htmlPath = path.join(appRoot, 'dist', 'renderer', 'pet', 'index.html');
    win.loadFile(htmlPath);

    // macOS specific configurations
    if (process.platform === 'darwin') {
      win.setVisibleOnAllWorkspaces(true);
      win.setAlwaysOnTop(this.settings.alwaysOnTop ?? true, 'floating', 1);
      win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

      win.on('blur', () => {
        win.setAlwaysOnTop(this.settings.alwaysOnTop ?? true, 'floating', 1);
      });
    }

    win.webContents.on('did-finish-load', () => {
      console.log('pet window loaded successfully');
    });

    win.webContents.on('did-fail-load', (_event, errorCode, errorDescription) => {
      console.error('Failed to load pet window:', errorCode, errorDescription);
    });

    return win;
  }
}
