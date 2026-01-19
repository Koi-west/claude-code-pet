import { app } from 'electron';
import * as fs from 'fs';
import * as path from 'path';

const ICON_FILE = 'miko-logo.png';

export function getAppIconPath(): string | null {
  const appPath = app.getAppPath();
  const candidates = [
    path.join(appPath, 'dist', 'renderer', 'assets', ICON_FILE),
    path.join(appPath, 'public', 'assets', ICON_FILE),
    path.join(process.cwd(), 'dist', 'renderer', 'assets', ICON_FILE),
    path.join(process.cwd(), 'public', 'assets', ICON_FILE),
  ];

  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return null;
}
