import React from 'react';
import { useDragAndDrop } from '../../hooks/useDragAndDrop';

interface FileDropZoneProps {
  onFilesDrop: (files: File[]) => void;
  children: React.ReactNode;
}

export function FileDropZone({ onFilesDrop, children }: FileDropZoneProps) {
  const {
    isDragging,
    handleDragOver,
    handleDragLeave,
    handleDrop,
  } = useDragAndDrop(onFilesDrop);

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`relative ${isDragging ? 'border-2 border-primary-500 bg-primary-50' : ''}`}
    >
      {isDragging && (
        <div className="absolute inset-0 bg-primary-50/80 flex items-center justify-center z-10">
          <div className="text-center">
            <svg className="w-12 h-12 text-primary-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-sm text-primary-600">Drop files to attach</p>
          </div>
        </div>
      )}

      {children}
    </div>
  );
}
