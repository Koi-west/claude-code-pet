import * as childProcess from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

export class WindowCapture {
  private tempDir: string;

  constructor() {
    // 创建临时目录
    this.tempDir = path.join(os.tmpdir(), 'miko-pet-screenshots');
    if (!fs.existsSync(this.tempDir)) {
      fs.mkdirSync(this.tempDir, { recursive: true });
    }
  }

  /**
   * 捕获指定窗口的截图（ macOS 版本）
   * windowId 应该是真实的 CGWindowID（由 windowIndexer 提供）
   */
  async captureWindow(windowId: number): Promise<string | null> {
    const tempFilePath = path.join(this.tempDir, `window-${Date.now()}.png`);

    try {
      // 直接使用传入的 windowId（现在是真实的 CGWindowID）
      console.log(`Capturing window with CGWindowID: ${windowId}`);

      const result = childProcess.spawnSync('screencapture', [
        '-l', windowId.toString(),  // -l <windowId> 使用真实的 CGWindowID
        '-x',  // 静音
        tempFilePath
      ]);

      if (result.status !== 0) {
        console.error('screencapture failed:', result.stderr?.toString());
        return null;
      }

      // 检查文件是否存在
      if (!fs.existsSync(tempFilePath)) {
        console.error('Screenshot file not created');
        return null;
      }

      // 读取并转换为 base64
      const imageBuffer = fs.readFileSync(tempFilePath);
      const base64Image = `data:image/png;base64,${imageBuffer.toString('base64')}`;

      console.log(`Window screenshot captured successfully (${imageBuffer.length} bytes)`);
      return base64Image;
    } catch (error) {
      console.error('Error capturing window:', error);
      return null;
    } finally {
      // 清理临时文件
      if (fs.existsSync(tempFilePath)) {
        fs.unlinkSync(tempFilePath);
      }
    }
  }

  /**
   * 获取窗口列表（ macOS 版本）
   */
  private async getWindowList(): Promise<Array<{ id: number; title: string }>> {
    return new Promise((resolve, reject) => {
      try {
        // 使用 AppleScript 获取窗口 ID 和标题
        const result = childProcess.spawnSync('osascript', [
          '-e', 'tell application "System Events"',
          '-e', 'set windowList to {}',
          '-e', 'repeat with p in every process',
          '-e', 'try',
          '-e', 'repeat with w in windows of p',
          '-e', 'try',
          '-e', 'set windowTitle to name of w',
          '-e', 'if windowTitle is not "" then',
          '-e', 'set windowId to id of w',
          '-e', 'set end of windowList to {windowId, windowTitle}',
          '-e', 'end if',
          '-e', 'on error',
          '-e', '-- 忽略无法访问的窗口',
          '-e', 'end try',
          '-e', 'end repeat',
          '-e', 'on error',
          '-e', '-- 忽略无法访问的进程',
          '-e', 'end try',
          '-e', 'end repeat',
          '-e', 'return windowList',
          '-e', 'end tell'
        ], { encoding: 'utf8' });

        if (result.status === 0 && result.stdout) {
          const windows = this.parseWindowOutput(result.stdout);
          resolve(windows);
        } else {
          reject(new Error('Failed to get window list'));
        }
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * 解析 AppleScript 输出的窗口信息
   */
  private parseWindowOutput(output: string): Array<{ id: number; title: string }> {
    const lines = output.split(/[\r\n]+/).filter(line => line.trim());
    const windows: Array<{ id: number; title: string }> = [];

    for (const line of lines) {
      const parts = line.split(',');
      if (parts.length >= 2) {
        const id = parseInt(parts[0].trim());
        if (!isNaN(id)) {
          windows.push({
            id,
            title: parts.slice(1).join(',').trim()
          });
        }
      }
    }

    return windows;
  }

  /**
   * 捕获整个屏幕截图
   */
  async captureScreen(): Promise<string | null> {
    const tempFilePath = path.join(this.tempDir, `screen-${Date.now()}.png`);

    try {
      const result = childProcess.spawnSync('screencapture', [
        '-x',
        tempFilePath
      ]);

      if (result.status === 0 && fs.existsSync(tempFilePath)) {
        const data = fs.readFileSync(tempFilePath);
        return `data:image/png;base64,${data.toString('base64')}`;
      }

      return null;
    } catch (error) {
      console.error('Error capturing screen:', error);
      return null;
    } finally {
      if (fs.existsSync(tempFilePath)) {
        fs.unlinkSync(tempFilePath);
      }
    }
  }

  /**
   * 清理临时目录
   */
  cleanup(): void {
    if (fs.existsSync(this.tempDir)) {
      try {
        const files = fs.readdirSync(this.tempDir);
        for (const file of files) {
          const filePath = path.join(this.tempDir, file);
          const stats = fs.statSync(filePath);
          if (Date.now() - stats.mtime.getTime() > 3600000) { // 删除超过 1 小时的文件
            fs.unlinkSync(filePath);
          }
        }
      } catch (error) {
        console.error('Error cleaning up temp directory:', error);
      }
    }
  }
}

// 单例实例
let windowCaptureInstance: WindowCapture | null = null;

export function getWindowCapture(): WindowCapture {
  if (!windowCaptureInstance) {
    windowCaptureInstance = new WindowCapture();
  }
  return windowCaptureInstance;
}

export default WindowCapture;