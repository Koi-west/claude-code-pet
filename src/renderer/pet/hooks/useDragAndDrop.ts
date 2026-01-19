import { useCallback, useState } from 'react';

export function useDragAndDrop(onFilesDrop: (files: File[]) => void) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(false);

    const files = Array.from(event.dataTransfer.files);
    if (files.length > 0) {
      onFilesDrop(files);
    }
  }, [onFilesDrop]);

  return {
    isDragging,
    handleDragOver,
    handleDragLeave,
    handleDrop,
  };
}
