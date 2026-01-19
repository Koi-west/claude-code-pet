import { app } from 'electron';
import * as childProcess from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export class SidecarLauncher {
  private process: childProcess.ChildProcess | null = null;
  private port: number | null = null;
  private isRunning: boolean = false;

  /**
   * 启动 Python sidecar 进程
   */
  async start(): Promise<number> {
    if (this.isRunning && this.process) {
      return this.port!;
    }

    // 找到可用端口
    this.port = await this.findAvailablePort();

    // 构建 Python 命令
    const pythonPath = this.findPythonExecutable();
    const sidecarPath = this.resolveSidecarEntrypoint();

    console.log('Starting sidecar at port:', this.port);
    console.log('Python path:', pythonPath);
    console.log('Sidecar path:', sidecarPath);

    return new Promise((resolve, reject) => {
      try {
        const env = {
          ...process.env,
          TIP_SIDECAR_HOST: '127.0.0.1',
          TIP_SIDECAR_PORT: String(this.port),
        };

        // 启动 Python 进程
        this.process = childProcess.spawn(pythonPath, [sidecarPath], {
          cwd: path.dirname(sidecarPath),
          stdio: 'pipe',
          env,
        });

        this.isRunning = true;

        // 监听输出
        this.process.stdout?.on('data', (data) => {
          const output = data.toString().trim();
          if (output) {
            console.log('Sidecar stdout:', output);
          }
        });

        this.process.stderr?.on('data', (data) => {
          const error = data.toString().trim();
          console.error('Sidecar stderr:', error);
        });

        this.process.on('close', (code) => {
          console.log(`Sidecar process closed with code ${code}`);
          this.isRunning = false;
          this.process = null;
        });

        this.process.on('error', (error) => {
          console.error('Sidecar process error:', error);
          this.isRunning = false;
          this.process = null;
          reject(error);
        });

        // 超时处理
        this.waitForHealthy(30000)
          .then(() => resolve(this.port!))
          .catch((error) => reject(error));

      } catch (error) {
        console.error('Failed to start sidecar:', error);
        reject(error);
      }
    });
  }

  /**
   * 停止 Python sidecar 进程
   */
  stop(): void {
    if (this.process && this.isRunning) {
      try {
        // 尝试优雅关闭
        this.process.kill('SIGTERM');

        // 强制终止超时
        setTimeout(() => {
          if (this.process && this.isRunning) {
            this.process.kill('SIGKILL');
          }
        }, 5000);
      } catch (error) {
        console.error('Failed to stop sidecar:', error);
      }
    }
  }

  /**
   * 检查进程是否正在运行
   */
  isSidecarRunning(): boolean {
    return this.isRunning;
  }

  /**
   * 获取当前端口
   */
  getPort(): number | null {
    return this.port;
  }

  /**
   * 查找可用端口
   */
  private async findAvailablePort(): Promise<number> {
    return new Promise((resolve) => {
      const net = require('net');
      const server = net.createServer();

      server.listen(0, () => {
        const address = server.address() as any;
        const port = address.port;
        server.close(() => resolve(port));
      });
    });
  }

  /**
   * 查找 Python 可执行文件
   */
  private findPythonExecutable(): string {
    // Prefer a local virtualenv to keep sidecar deps isolated
    const venvCandidates = [
      path.join(process.cwd(), 'sidecar', 'python', '.venv312', 'bin', 'python3'),
      path.join(process.cwd(), 'sidecar', 'python', '.venv312', 'bin', 'python'),
      path.join(process.cwd(), 'sidecar', 'python', '.venv', 'bin', 'python3'),
      path.join(process.cwd(), 'sidecar', 'python', '.venv', 'bin', 'python'),
      path.join(app.getAppPath(), 'sidecar', 'python', '.venv312', 'bin', 'python3'),
      path.join(app.getAppPath(), 'sidecar', 'python', '.venv312', 'bin', 'python'),
      path.join(app.getAppPath(), 'sidecar', 'python', '.venv', 'bin', 'python3'),
      path.join(app.getAppPath(), 'sidecar', 'python', '.venv', 'bin', 'python'),
      path.join(process.resourcesPath || '', 'sidecar', 'python', '.venv312', 'bin', 'python3'),
      path.join(process.resourcesPath || '', 'sidecar', 'python', '.venv312', 'bin', 'python'),
      path.join(process.resourcesPath || '', 'sidecar', 'python', '.venv', 'bin', 'python3'),
      path.join(process.resourcesPath || '', 'sidecar', 'python', '.venv', 'bin', 'python'),
    ];

    for (const pythonPath of venvCandidates) {
      if (pythonPath && fs.existsSync(pythonPath)) {
        try {
          const result = childProcess.spawnSync(pythonPath, ['--version'], {
            encoding: 'utf8'
          });
          if (result.status === 0) {
            console.log('Found Python (venv):', pythonPath);
            return pythonPath;
          }
        } catch {
          // Ignore and fall back to system paths
        }
      }
    }

    // 尝试常见的 Python 可执行文件路径
    const possiblePaths = [
      '/usr/bin/python3',
      '/usr/local/bin/python3',
      '/opt/homebrew/bin/python3',
      '/usr/bin/python',
      '/usr/local/bin/python',
      '/opt/homebrew/bin/python'
    ];

    for (const pythonPath of possiblePaths) {
      if (fs.existsSync(pythonPath)) {
        try {
          // 验证 Python 可执行文件是否能正常工作
          const result = childProcess.spawnSync(pythonPath, ['--version'], {
            encoding: 'utf8'
          });
          if (result.status === 0) {
            console.log('Found Python:', pythonPath);
            return pythonPath;
          }
        } catch (error) {
          // 忽略错误，尝试下一个路径
        }
      }
    }

    // 如果没有找到，抛出错误
    throw new Error('Python 3 not found. Please install Python 3 or check your PATH.');
  }

  /**
   * 定位 sidecar 入口脚本
   */
  private resolveSidecarEntrypoint(): string {
    const appPath = app.getAppPath();
    const candidates = [
      path.join(appPath, 'sidecar', 'python', 'run_sidecar.py'),
      path.join(process.cwd(), 'sidecar', 'python', 'run_sidecar.py'),
      path.join(process.resourcesPath || '', 'sidecar', 'python', 'run_sidecar.py'),
    ];

    for (const candidate of candidates) {
      if (candidate && fs.existsSync(candidate)) {
        return candidate;
      }
    }

    throw new Error('Sidecar entrypoint not found. Ensure sidecar/python/run_sidecar.py is packaged with the app.');
  }

  private async waitForHealthy(timeoutMs: number): Promise<void> {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (!this.port) {
        break;
      }
      try {
        const response = await fetch(`http://127.0.0.1:${this.port}/health`);
        if (response.ok) {
          return;
        }
      } catch {
        // Ignore until timeout
      }
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    throw new Error('Sidecar startup timed out');
  }

  /**
   * 检查 sidecar 健康状态
   */
  async checkHealth(): Promise<boolean> {
    if (!this.isRunning || !this.port) {
      return false;
    }

    try {
      const response = await fetch(`http://127.0.0.1:${this.port}/health`);
      return response.ok;
    } catch (error) {
      return false;
    }
  }
}

// 单例实例
let sidecarLauncherInstance: SidecarLauncher | null = null;

export function getSidecarLauncher(): SidecarLauncher {
  if (!sidecarLauncherInstance) {
    sidecarLauncherInstance = new SidecarLauncher();
  }
  return sidecarLauncherInstance;
}

export default SidecarLauncher;
