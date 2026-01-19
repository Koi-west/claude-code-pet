import { BrowserWindow, app } from 'electron';
import * as path from 'path';
import { settingsStore, AppSettings } from '../storage/SettingsStore';
import { PetWindow, PetWindowOverrides } from './PetWindow';
import { DashboardWindow, DashboardWindowOverrides } from './DashboardWindow';

export type WindowType = 'pet' | 'dashboard';

export type WindowOverrides = PetWindowOverrides & DashboardWindowOverrides;

interface WindowManagerState {
  [key: string]: BrowserWindow | null;
}

export class WindowManager {
  private static instance: WindowManager;
  private windows: WindowManagerState = {};
  private settingsSaveTimer: NodeJS.Timeout | null = null;
  private lastSavedBounds: { x: number; y: number; width: number; height: number } | null = null;

  private constructor() {}

  public static getInstance(): WindowManager {
    if (!WindowManager.instance) {
      WindowManager.instance = new WindowManager();
    }
    return WindowManager.instance;
  }

  public createWindow(type: WindowType, overrides?: WindowOverrides): BrowserWindow {
    const settings = settingsStore.getSettings();
    const win = type === 'pet'
      ? new PetWindow(settings).create(overrides)
      : new DashboardWindow(settings).create(overrides);

    this.attachWindowEvents(type, win);
    this.applyDevTools(win);

    this.windows[type] = win;

    win.on('closed', () => {
      this.windows[type] = null;
    });

    return win;
  }

  public applySettings(settings: AppSettings): void {
    const petWindow = this.getWindow('pet');
    if (petWindow) {
      const currentBounds = petWindow.getBounds();

      if (typeof settings.alwaysOnTop === 'boolean') {
        petWindow.setAlwaysOnTop(settings.alwaysOnTop, 'floating', 1);
      }

      if (typeof settings.windowWidth === 'number' && typeof settings.windowHeight === 'number') {
        const minWidth = 520;
        const minHeight = 320;
        const nextWidth = Math.max(minWidth, settings.windowWidth);
        const nextHeight = Math.max(minHeight, settings.windowHeight);
        if (currentBounds.width !== nextWidth || currentBounds.height !== nextHeight) {
          petWindow.setSize(nextWidth, nextHeight);
        }
      }

      if (
        typeof settings.windowX === 'number' &&
        typeof settings.windowY === 'number' &&
        settings.windowX >= 0 &&
        settings.windowY >= 0
      ) {
        if (currentBounds.x !== settings.windowX || currentBounds.y !== settings.windowY) {
          petWindow.setPosition(settings.windowX, settings.windowY);
        }
      }
    }
  }

  private attachWindowEvents(type: WindowType, win: BrowserWindow): void {
    if (type !== 'pet') {
      return;
    }

    const saveBounds = () => {
      if (this.settingsSaveTimer) {
        clearTimeout(this.settingsSaveTimer);
      }

      this.settingsSaveTimer = setTimeout(() => {
        const bounds = win.getBounds();
        if (this.lastSavedBounds &&
          this.lastSavedBounds.x === bounds.x &&
          this.lastSavedBounds.y === bounds.y &&
          this.lastSavedBounds.width === bounds.width &&
          this.lastSavedBounds.height === bounds.height) {
          return;
        }
        settingsStore.updateSettings({
          windowX: bounds.x,
          windowY: bounds.y,
          windowWidth: bounds.width,
          windowHeight: bounds.height,
        });
        this.lastSavedBounds = bounds;
      }, 300);
    };

    win.on('move', saveBounds);
    win.on('resize', saveBounds);
  }

  private applyDevTools(win: BrowserWindow): void {
    if (process.env.NODE_ENV !== 'development') {
      return;
    }

    win.webContents.openDevTools({ mode: 'detach' });

    try {
      const appRoot = app.getAppPath();
      const electronPath = path.join(appRoot, 'node_modules', '.bin', 'electron');
      require('electron-reload')(appRoot, {
        electron: electronPath,
        hardResetMethod: 'exit',
      });
    } catch (error) {
      console.log('Electron reload not available');
    }
  }

  public getWindow(type: WindowType): BrowserWindow | null {
    return this.windows[type] || null;
  }

  public getAllWindows(): BrowserWindow[] {
    return Object.values(this.windows).filter(win => win !== null) as BrowserWindow[];
  }

  public isWindowOpen(type: WindowType): boolean {
    return !!this.windows[type];
  }

  public showWindow(type: WindowType): void {
    const win = this.getWindow(type);
    if (win) {
      if (win.isMinimized()) {
        win.restore();
      }
      win.show();
      win.focus();
    } else {
      this.createWindow(type);
    }
  }

  public hideWindow(type: WindowType): void {
    const win = this.getWindow(type);
    if (win && win.isVisible()) {
      win.hide();
    }
  }

  public toggleWindow(type: WindowType): void {
    const win = this.getWindow(type);
    if (win && win.isVisible()) {
      this.hideWindow(type);
    } else {
      this.showWindow(type);
    }
  }

  public closeWindow(type: WindowType): void {
    const win = this.getWindow(type);
    if (win) {
      win.close();
    }
  }

  public closeAllWindows(): void {
    Object.keys(this.windows).forEach(type => {
      const win = this.getWindow(type as WindowType);
      if (win) {
        win.close();
      }
    });
  }
}

export const windowManager = WindowManager.getInstance();
