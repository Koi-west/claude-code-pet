import { BrowserWindow, screen, app } from 'electron';
import * as path from 'path';

let mainWindow: BrowserWindow | null = null;

export interface WindowConfig {
  width?: number;
  height?: number;
  x?: number;
  y?: number;
}

/**
 * Create the main pet window
 */
export function createWindow(config?: WindowConfig): BrowserWindow {
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

  // Default window size
  const windowWidth = config?.width || 500;
  const windowHeight = config?.height || 300;

  // Default position: center of screen (easier to see)
  const defaultX = Math.floor((screenWidth - windowWidth) / 2);
  const defaultY = Math.floor((screenHeight - windowHeight) / 2);

  mainWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x: config?.x ?? defaultX,
    y: config?.y ?? defaultY,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: false,  // Show in taskbar for easier access
    fullscreenable: false,
    type: process.platform === 'darwin' ? 'panel' : 'normal',
    backgroundColor: 'rgba(0, 0, 0, 0)',
    hasShadow: false,
  });

  // Set visible on all workspaces (needs to be done after creation)
  mainWindow.setVisibleOnAllWorkspaces(true);

  // macOS specific: highest floating level
  if (process.platform === 'darwin') {
    mainWindow.setAlwaysOnTop(true, 'floating', 1);
    mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  }

  // Maintain always-on-top on blur
  mainWindow.on('blur', () => {
    if (process.platform === 'darwin' && mainWindow) {
      mainWindow.setAlwaysOnTop(true, 'floating', 1);
    }
  });

  // Load the HTML file
  const htmlPath = path.join(__dirname, '..', '..', 'index.html');
  console.log('Loading HTML from:', htmlPath);
  console.log('HTML exists:', require('fs').existsSync(htmlPath));
  mainWindow.loadFile(htmlPath);

  // Log when page finishes loading
  mainWindow.webContents.on('did-finish-load', () => {
    console.log('Page loaded successfully');
  });

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Failed to load page:', errorCode, errorDescription);
  });

  // Development mode: reload on changes and open DevTools
  if (process.env.NODE_ENV === 'development') {
    // Open DevTools for debugging
    mainWindow.webContents.openDevTools({ mode: 'detach' });

    try {
      require('electron-reload')(path.join(__dirname, '..', '..'), {
        electron: path.join(__dirname, '..', '..', 'node_modules', '.bin', 'electron'),
        hardResetMethod: 'exit',
      });
    } catch (err) {
      console.log('Electron reload not available');
    }
  }

  return mainWindow;
}

/**
 * Get the main window instance
 */
export function getMainWindow(): BrowserWindow | null {
  return mainWindow;
}

/**
 * Close the main window
 */
export function closeWindow(): void {
  if (mainWindow) {
    mainWindow.close();
    mainWindow = null;
  }
}

/**
 * Minimize the main window
 */
export function minimizeWindow(): void {
  if (mainWindow) {
    mainWindow.minimize();
  }
}

/**
 * Show the main window
 */
export function showWindow(): void {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  }
}

/**
 * Hide the main window
 */
export function hideWindow(): void {
  if (mainWindow) {
    mainWindow.hide();
  }
}

/**
 * Set window position
 */
export function setWindowPosition(x: number, y: number): void {
  if (mainWindow) {
    mainWindow.setPosition(x, y);
  }
}

/**
 * Get window position
 */
export function getWindowPosition(): { x: number; y: number } | null {
  if (mainWindow) {
    const [x, y] = mainWindow.getPosition();
    return { x, y };
  }
  return null;
}

/**
 * Set window size
 */
export function setWindowSize(width: number, height: number): void {
  if (mainWindow) {
    mainWindow.setSize(width, height);
  }
}

export default {
  createWindow,
  getMainWindow,
  closeWindow,
  minimizeWindow,
  showWindow,
  hideWindow,
  setWindowPosition,
  getWindowPosition,
  setWindowSize,
};
