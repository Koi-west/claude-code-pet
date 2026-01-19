import * as childProcess from 'child_process';
import { IPC_CHANNELS, TextSelection } from '../../types';
import { windowManager } from '../windows/WindowManager';

export class TextSelectionListener {
  private intervalId: NodeJS.Timeout | null = null;
  private lastSelectedText: string = '';
  private isListening: boolean = false;

  /**
   * 开始监听文本选择
   */
  startListening(): void {
    if (this.isListening) {
      return;
    }

    this.isListening = true;
    console.log('Text selection listener started');

    // 定期检查选中的文本（ macOS 上）
    this.intervalId = setInterval(() => {
      this.checkSelectedText();
    }, 1000);
  }

  /**
   * 停止监听文本选择
   */
  stopListening(): void {
    if (!this.isListening) {
      return;
    }

    this.isListening = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    console.log('Text selection listener stopped');
  }

  /**
   * 获取当前选中的文本（公开方法）
   */
  getCurrentSelection(): TextSelection | null {
    const selectedText = this.getSelectedText();
    if (!selectedText || selectedText.trim().length === 0) {
      return null;
    }

    this.lastSelectedText = selectedText;
    return {
      text: selectedText,
      application: this.getFrontApplicationName(),
      windowTitle: this.getFrontWindowTitle()
    };
  }

  /**
   * 清除当前选中的文本
   */
  clearSelection(): void {
    this.lastSelectedText = '';
  }

  /**
   * 检查当前选中的文本
   */
  private checkSelectedText(): void {
    const selectedText = this.getSelectedText();
    if (selectedText && selectedText !== this.lastSelectedText && selectedText.trim().length > 0) {
      this.lastSelectedText = selectedText;
      this.notifyRenderer(selectedText);
    }
  }

  /**
   * 获取当前选中的文本（ macOS 版本）
   * 使用剪贴板方式：模拟 Cmd+C 复制，然后读取剪贴板
   * 这是最可靠的跨应用获取选中文字的方式
   */
  private getSelectedText(): string {
    try {
      // 使用 AppleScript 通过剪贴板获取选中文本
      const script = `
        -- 保存当前剪贴板内容
        set oldClipboard to the clipboard as text

        -- 模拟 Cmd+C 复制
        tell application "System Events"
          keystroke "c" using command down
        end tell

        delay 0.1

        -- 获取新的剪贴板内容
        set newClipboard to the clipboard as text

        -- 恢复原剪贴板（如果内容变化了）
        if newClipboard is not equal to oldClipboard then
          set the clipboard to oldClipboard
          return newClipboard
        else
          return ""
        end if
      `;

      const result = childProcess.spawnSync('osascript', ['-e', script], {
        encoding: 'utf8',
        timeout: 2000
      });

      if (result.status === 0 && result.stdout) {
        return result.stdout.trim();
      }
    } catch (error) {
      console.error('Error getting selected text:', error);
    }

    return '';
  }

  /**
   * 通知渲染进程选中的文本
   */
  private notifyRenderer(text: string): void {
    // Use getMainWindow() instead of getFocusedWindow() so we can notify
    // when user selects text in other applications (like WeChat, Chrome, etc.)
    const petWindow = windowManager.getWindow('pet');
    if (petWindow) {
      const selection: TextSelection = {
        text,
        application: this.getFrontApplicationName(),
        windowTitle: this.getFrontWindowTitle()
      };

      petWindow.webContents.send(IPC_CHANNELS.TEXT_SELECTION, selection);
    }
  }

  /**
   * 获取当前前端应用程序的名称
   */
  private getFrontApplicationName(): string {
    try {
      const result = childProcess.spawnSync('osascript', [
        '-e', 'tell application "System Events"',
        '-e', 'set frontApp to first application process whose frontmost is true',
        '-e', 'return name of frontApp',
        '-e', 'end tell'
      ], { encoding: 'utf8' });

      if (result.status === 0 && result.stdout) {
        return result.stdout.trim();
      }
    } catch (error) {
      console.error('Error getting front application name:', error);
    }

    return 'Unknown';
  }

  /**
   * 获取当前前端窗口的标题
   */
  private getFrontWindowTitle(): string {
    try {
      const result = childProcess.spawnSync('osascript', [
        '-e', 'tell application "System Events"',
        '-e', 'set frontApp to first application process whose frontmost is true',
        '-e', 'set frontWindow to front window of frontApp',
        '-e', 'return name of frontWindow',
        '-e', 'end tell'
      ], { encoding: 'utf8' });

      if (result.status === 0 && result.stdout) {
        return result.stdout.trim();
      }
    } catch (error) {
      console.error('Error getting front window title:', error);
    }

    return 'Unknown';
  }
}

// 单例实例
let textSelectionListenerInstance: TextSelectionListener | null = null;

export function getTextSelectionListener(): TextSelectionListener {
  if (!textSelectionListenerInstance) {
    textSelectionListenerInstance = new TextSelectionListener();
  }
  return textSelectionListenerInstance;
}

export default TextSelectionListener;
