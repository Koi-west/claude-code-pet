import * as childProcess from 'child_process';
import { WindowInfo, WindowSearchResult } from '../../types';

export class WindowIndexer {
  private windows: WindowInfo[] = [];
  private lastUpdateTime: number = 0;

  /**
   * 更新窗口列表
   */
  async updateWindows(): Promise<void> {
    this.windows = await this.fetchWindows();
    this.lastUpdateTime = Date.now();
  }

  /**
   * 获取当前所有窗口信息（ macOS 版本）
   * 使用 Quartz Window Services (CGWindowListCopyWindowInfo) 获取真实窗口 ID
   */
  private async fetchWindows(): Promise<WindowInfo[]> {
    const windows: WindowInfo[] = [];

    try {
      // 使用 AppleScript 调用 Quartz API 获取真实窗口 ID
      const script = `
        use framework "Foundation"
        use framework "AppKit"
        use scripting additions

        set windowList to ""
        set allWindows to (current application's CGWindowListCopyWindowInfo((current application's kCGWindowListOptionOnScreenOnly), 0)) as list

        repeat with w in allWindows
          try
            set wLayer to kCGWindowLayer of w
            -- 只获取普通窗口 (layer 0)，排除菜单栏、Dock 等
            if wLayer is 0 then
              set wID to kCGWindowNumber of w
              set wName to kCGWindowName of w
              if wName is missing value then set wName to ""
              set wOwner to kCGWindowOwnerName of w
              set wBounds to kCGWindowBounds of w
              set windowList to windowList & wID & "|||" & wName & "|||" & wOwner & "|||" & (X of wBounds) & "," & (Y of wBounds) & "," & (Width of wBounds) & "," & (Height of wBounds) & linefeed
            end if
          end try
        end repeat

        return windowList
      `;

      const result = childProcess.spawnSync('osascript', ['-e', script], {
        encoding: 'utf8',
        timeout: 5000
      });

      if (result.status === 0 && result.stdout) {
        const lines = result.stdout.trim().split('\n');

        for (const line of lines) {
          if (!line.trim()) continue;
          const [idStr, title, processName, boundsStr] = line.split('|||');
          const realWindowId = parseInt(idStr, 10);

          if (!isNaN(realWindowId)) {
            windows.push({
              id: realWindowId,  // 使用真实的 CGWindowID
              title: title || 'Untitled',
              processName: processName || 'Unknown',
              bounds: this.parseBounds(boundsStr || '')
            });
          }
        }
      }
    } catch (error) {
      console.error('Error getting windows:', error);
    }

    return windows;
  }

  /**
   * 解析 AppleScript 输出
   */
  private parseAppleScriptOutput(output: string): string[][] {
    // 简单的解析方法
    const lines = output.split(/[\r\n]+/).filter(line => line.trim());
    const windows: string[][] = [];

    for (const line of lines) {
      const parts = line.split(',');
      if (parts.length >= 2) {
        windows.push(parts.map(part => part.trim()));
      }
    }

    return windows;
  }

  /**
   * 解析窗口边界信息
   */
  private parseBounds(boundsStr: string): { x: number; y: number; width: number; height: number } {
    // 期望格式: x,y,w,h 或 {x,y,w,h}
    const cleanStr = boundsStr.replace(/[{}]/g, '');
    const numbers = cleanStr.split(',').map(Number);

    return {
      x: numbers[0] || 0,
      y: numbers[1] || 0,
      width: numbers[2] || 0,
      height: numbers[3] || 0
    };
  }

  /**
   * 搜索窗口
   */
  searchWindows(query: string): WindowSearchResult[] {
    if (!query || query.length < 2) {
      return [];
    }

    const lowerCaseQuery = query.toLowerCase();
    const results: WindowSearchResult[] = [];

    for (const window of this.windows) {
      let score = 0;

      if (window.title.toLowerCase().includes(lowerCaseQuery)) {
        score += 50;
        if (window.title.toLowerCase().startsWith(lowerCaseQuery)) {
          score += 30;
        }
      }

      if (window.processName.toLowerCase().includes(lowerCaseQuery)) {
        score += 20;
      }

      if (score > 0) {
        results.push({
          window,
          score
        });
      }
    }

    return results.sort((a, b) => b.score - a.score).slice(0, 10);
  }

  /**
   * 获取窗口列表
   */
  getWindows(): WindowInfo[] {
    return [...this.windows];
  }

  /**
   * 获取窗口总数
   */
  getWindowCount(): number {
    return this.windows.length;
  }
}

// 单例实例
let windowIndexerInstance: WindowIndexer | null = null;

export function getWindowIndexer(): WindowIndexer {
  if (!windowIndexerInstance) {
    windowIndexerInstance = new WindowIndexer();
  }
  return windowIndexerInstance;
}

export default WindowIndexer;
