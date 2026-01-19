import { useCallback, useEffect, useMemo, useState } from 'react';
import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '@types';
import { v4 as uuidv4 } from 'uuid';

export interface FileAttachment {
  id: string;
  path: string;
  name: string;
  size: number;
  type?: string;
}

const RECENT_FILES_KEY = 'miko:recent-files';

const normalizeFile = (file: File, overrides: Partial<FileAttachment> = {}): FileAttachment => ({
  id: uuidv4(),
  path: overrides.path ?? (file as any).path ?? '',
  name: overrides.name ?? file.name,
  size: overrides.size ?? file.size ?? 0,
  type: overrides.type ?? file.type ?? '',
});

export function useFileAttachments() {
  const [attachedFiles, setAttachedFiles] = useState<FileAttachment[]>([]);
  const [recentFiles, setRecentFiles] = useState<FileAttachment[]>([]);

  useEffect(() => {
    const stored = localStorage.getItem(RECENT_FILES_KEY);
    if (stored) {
      try {
        setRecentFiles(JSON.parse(stored));
      } catch (error) {
        console.warn('Failed to parse recent files cache', error);
      }
    }
  }, []);

  const persistRecentFiles = useCallback((files: FileAttachment[]) => {
    localStorage.setItem(RECENT_FILES_KEY, JSON.stringify(files));
  }, []);

  const addToRecentFiles = useCallback((file: FileAttachment) => {
    setRecentFiles((prev) => {
      const filtered = prev.filter((item) => item.path !== file.path);
      const next = [file, ...filtered].slice(0, 10);
      persistRecentFiles(next);
      return next;
    });
  }, [persistRecentFiles]);

  const addFiles = useCallback((files: File[]) => {
    const normalized = files
      .filter((file) => (file as any).path)
      .map((file) => normalizeFile(file));

    if (normalized.length === 0) {
      return;
    }

    setAttachedFiles((prev) => {
      const existing = new Set(prev.map((item) => item.path));
      const merged = [...prev, ...normalized.filter((item) => !existing.has(item.path))];
      normalized.forEach(addToRecentFiles);
      return merged;
    });
  }, [addToRecentFiles]);

  const addFileFromDialog = useCallback(async () => {
    const result = await ipcRenderer.invoke(IPC_CHANNELS.SELECT_FILE);
    if (!result || !result.success) {
      return;
    }

    const files = Array.isArray(result.files) ? result.files : [result];
    const attachments = files.map((file: any) => ({
      id: uuidv4(),
      path: file.path,
      name: file.displayName,
      size: file.size ?? 0,
      type: file.type,
    }));

    setAttachedFiles((prev) => {
      const existing = new Set(prev.map((item) => item.path));
      return [...prev, ...attachments.filter((item) => !existing.has(item.path))];
    });

    attachments.forEach(addToRecentFiles);
  }, [addToRecentFiles]);

  const attachRecentFile = useCallback((file: FileAttachment) => {
    setAttachedFiles((prev) => {
      if (prev.some((item) => item.path === file.path)) {
        return prev;
      }
      return [...prev, { ...file, id: uuidv4() }];
    });
    addToRecentFiles(file);
  }, [addToRecentFiles]);

  const removeFile = useCallback((path: string) => {
    setAttachedFiles((prev) => prev.filter((file) => file.path !== path));
  }, []);

  const clearFiles = useCallback(() => {
    setAttachedFiles([]);
  }, []);

  const hasFiles = useMemo(() => attachedFiles.length > 0, [attachedFiles]);

  return {
    attachedFiles,
    recentFiles,
    hasFiles,
    addFiles,
    addFileFromDialog,
    attachRecentFile,
    removeFile,
    clearFiles,
  };
}
