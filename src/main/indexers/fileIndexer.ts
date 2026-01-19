import * as fs from 'fs';
import * as path from 'path';
import { FileSearchResult } from '../../types';

export class FileIndexer {
  private indexedFiles: string[] = [];
  private isIndexing: boolean = false;

  /**
   * 开始索引文件系统
   */
  async indexFiles(directories?: string[]): Promise<void> {
    if (this.isIndexing) {
      return;
    }

    this.isIndexing = true;
    const start = Date.now();

    try {
      // 默认索引常用目录
      const defaultDirs = directories || [
        process.env.HOME || '',
        path.join(process.env.HOME || '', 'Documents'),
        path.join(process.env.HOME || '', 'Downloads'),
        path.join(process.env.HOME || '', 'Desktop')
      ].filter(Boolean);

      this.indexedFiles = [];

      for (const dir of defaultDirs) {
        await this.indexDirectory(dir);
      }

      const duration = Date.now() - start;
      console.log(`Indexed ${this.indexedFiles.length} files in ${duration}ms`);
    } catch (error) {
      console.error('Error indexing files:', error);
    } finally {
      this.isIndexing = false;
    }
  }

  /**
   * 索引单个目录
   */
  private async indexDirectory(dirPath: string): Promise<void> {
    try {
      // 忽略某些目录以提高性能和隐私
      const ignoredDirs = ['node_modules', '.git', '.DS_Store', '.Trash', 'Library'];

      const entries = fs.readdirSync(dirPath, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);

        if (entry.isDirectory()) {
          if (!ignoredDirs.includes(entry.name) && entry.name[0] !== '.') {
            // 递归索引子目录
            try {
              await this.indexDirectory(fullPath);
            } catch (error) {
              // 忽略无权限访问的目录
            }
          }
        } else {
          // 只索引常见的文本文件
          const validExtensions = ['.txt', '.md', '.json', '.js', '.ts', '.html', '.css', '.py', '.java', '.cpp', '.c'];
          const ext = path.extname(fullPath).toLowerCase();

          if (validExtensions.includes(ext) || ext === '') {
            this.indexedFiles.push(fullPath);
          }
        }
      }
    } catch (error) {
      // 忽略无法访问的目录
    }
  }

  /**
   * 搜索文件
   */
  searchFiles(query: string): FileSearchResult[] {
    if (!query || query.length < 2) {
      return [];
    }

    const lowerCaseQuery = query.toLowerCase();
    const results: FileSearchResult[] = [];

    for (const filePath of this.indexedFiles) {
      const fileName = path.basename(filePath).toLowerCase();
      const dirName = path.dirname(filePath).toLowerCase();

      // 计算匹配分数
      let score = 0;

      if (fileName.includes(lowerCaseQuery)) {
        score += 50;
        // 精确匹配文件名开头
        if (fileName.startsWith(lowerCaseQuery)) {
          score += 30;
        }
      }

      if (dirName.includes(lowerCaseQuery)) {
        score += 20;
      }

      if (score > 0) {
        results.push({
          path: filePath,
          displayName: path.basename(filePath),
          score: score
        });
      }
    }

    // 按分数降序排序
    return results.sort((a, b) => b.score - a.score).slice(0, 20);
  }

  /**
   * 获取索引的文件总数
   */
  getFileCount(): number {
    return this.indexedFiles.length;
  }

  /**
   * 重置索引
   */
  reset(): void {
    this.indexedFiles = [];
    this.isIndexing = false;
  }
}

// 单例实例
let fileIndexerInstance: FileIndexer | null = null;

export function getFileIndexer(): FileIndexer {
  if (!fileIndexerInstance) {
    fileIndexerInstance = new FileIndexer();
  }
  return fileIndexerInstance;
}

export default FileIndexer;