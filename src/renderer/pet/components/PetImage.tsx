import React from 'react';

interface PetImageProps {
  onToggleChat?: () => void;
}

export function PetImage({ onToggleChat }: PetImageProps) {
  return (
    <div className="w-[120px] h-[120px] flex items-center justify-center">
      <img
        src="../assets/pet up-down.gif"
        alt="Miko pet"
        className="w-full h-full object-contain select-none cursor-move"
        draggable={false}
        onDoubleClick={onToggleChat}
      />
    </div>
  );
}
