import React, { useState, useEffect, useMemo } from 'react';
import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '@types';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  FileCode,
  FileImage,
  FileArchive,
  FileAudio,
  FileVideo,
  X,
} from 'lucide-react';
import { formatFileSize } from '@renderer/shared/utils';
import { FileAttachment } from '../../hooks/useFileAttachments';

interface FilePreview {
  type: 'text' | 'image' | 'binary';
  content: string;
  mime?: string;
  truncated?: boolean;
}

interface FileChipProps {
  file: FileAttachment;
  onRemove: () => void;
}

const getFileIcon = (fileName: string) => {
  const lower = fileName.toLowerCase();
  if (/(\.png|\.jpg|\.jpeg|\.gif|\.webp|\.svg)$/.test(lower)) {
    return FileImage;
  }
  if (/(\.mp3|\.wav|\.flac|\.aac)$/.test(lower)) {
    return FileAudio;
  }
  if (/(\.mp4|\.mov|\.mkv|\.webm)$/.test(lower)) {
    return FileVideo;
  }
  if (/(\.zip|\.tar|\.gz|\.7z|\.rar)$/.test(lower)) {
    return FileArchive;
  }
  if (/(\.js|\.ts|\.tsx|\.py|\.json|\.md|\.yaml|\.yml|\.go|\.rs|\.java)$/.test(lower)) {
    return FileCode;
  }
  return FileText;
};

export function FileChip({ file, onRemove }: FileChipProps) {
  const [preview, setPreview] = useState<FilePreview | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const Icon = useMemo(() => getFileIcon(file.name), [file.name]);

  useEffect(() => {
    const loadPreview = async () => {
      try {
        const result = await ipcRenderer.invoke(IPC_CHANNELS.READ_FILE, file.path);
        if (result?.success && result.preview) {
          setPreview(result.preview);
        }
      } catch (error) {
        console.error('Failed to load file preview:', error);
      }
    };

    loadPreview();
  }, [file.path]);

  return (
    <motion.div
      className="inline-flex items-center gap-2 px-3 py-1 bg-neutral-100 rounded-full text-sm border border-neutral-200 relative"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.2 }}
      onMouseEnter={() => setShowPreview(true)}
      onMouseLeave={() => setShowPreview(false)}
    >
      <Icon className="w-4 h-4 text-neutral-500" />
      <span className="max-w-[160px] truncate" title={file.path}>{file.name}</span>
      <span className="text-xs text-neutral-500">{formatFileSize(file.size)}</span>
      <button
        onClick={onRemove}
        className="p-0.5 text-neutral-500 hover:text-error-500 transition-colors"
        title="Remove file"
      >
        <X className="w-3 h-3" />
      </button>

      <AnimatePresence>
        {showPreview && preview && (
          <motion.div
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-white border border-neutral-200 rounded-lg shadow-lg p-3 max-w-[320px] z-10"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.2 }}
          >
            <div className="text-xs font-medium text-neutral-500 mb-1">{file.name}</div>
            {preview.type === 'image' ? (
              <img
                src={`data:${preview.mime || 'image/png'};base64,${preview.content}`}
                alt={file.name}
                className="max-h-40 rounded border"
              />
            ) : (
              <pre className="text-xs text-neutral-700 bg-neutral-50 p-2 rounded max-h-40 overflow-auto">
                {preview.content}
                {preview.truncated ? '\n...' : ''}
              </pre>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

interface FileChipsProps {
  files: FileAttachment[];
  onRemove: (path: string) => void;
}

export function FileChips({ files, onRemove }: FileChipsProps) {
  if (files.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 p-4 border-t border-neutral-200">
      <AnimatePresence>
        {files.map((file) => (
          <FileChip
            key={file.id}
            file={file}
            onRemove={() => onRemove(file.path)}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}
