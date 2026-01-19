import { BrowserWindow, screen, app } from 'electron';
import * as path from 'path';
import { AppSettings } from '../storage/SettingsStore';
import { getAppIconPath } from '../utils/appIcon';

export interface DashboardWindowOverrides {
  width?: number;
  height?: number;
  x?: number;
  y?: number;
}

export class DashboardWindow {
  private settings: AppSettings;

  constructor(settings: AppSettings) {
    this.settings = settings;
  }

  create(overrides: DashboardWindowOverrides = {}): BrowserWindow {
    const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

    const windowWidth = overrides.width ?? 940;
    const windowHeight = overrides.height ?? 720;

    const defaultX = Math.floor((screenWidth - windowWidth) / 2);
    const defaultY = Math.floor((screenHeight - windowHeight) / 2);
    const iconPath = getAppIconPath();

    const win = new BrowserWindow({
      width: windowWidth,
      height: windowHeight,
      x: overrides.x ?? defaultX,
      y: overrides.y ?? defaultY,
      title: 'Kohaku Dashboard',
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false,
      },
      transparent: false,
      frame: true,
      resizable: true,
      fullscreenable: true,
      backgroundColor: '#f6f7f9',
      show: true,
      icon: iconPath ?? undefined,
    });

    const appRoot = app.getAppPath();
    const htmlPath = path.join(appRoot, 'dist', 'renderer', 'dashboard', 'index.html');
    win.loadFile(htmlPath);

    win.webContents.on('did-finish-load', () => {
      console.log('dashboard window loaded successfully');
    });

    win.webContents.on('did-fail-load', (_event, errorCode, errorDescription) => {
      console.error('Failed to load dashboard window:', errorCode, errorDescription);
    });

    return win;
  }
}
