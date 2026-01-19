import React, { useState, useRef } from 'react';
import { Paperclip, Send, Square, Clock } from 'lucide-react';
import { Dropdown, DropdownContent, DropdownItem, DropdownTrigger } from '@renderer/shared/components';
import { FileAttachment } from '../../hooks/useFileAttachments';
import { CommandAutocomplete } from './CommandAutocomplete';

interface ChatInputProps {
  onSend: (content: string) => void;
  onAttach: () => void;
  onRecentSelect: (file: FileAttachment) => void;
  recentFiles: FileAttachment[];
  isStreaming: boolean;
  onInterrupt: () => void;
}

export function ChatInput({
  onSend,
  onAttach,
  onRecentSelect,
  recentFiles,
  isStreaming,
  onInterrupt,
}: ChatInputProps) {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (inputValue.trim()) {
        onSend(inputValue.trim());
        setInputValue('');
      }
      return;
    }

    if (event.key === '@') {
      event.preventDefault();
      onAttach();
      return;
    }
  };

  const handleSend = () => {
    if (inputValue.trim()) {
      onSend(inputValue.trim());
      setInputValue('');
    }
  };

  const handleCommandSelect = (command: { value: string }) => {
    setInputValue(command.value);
    inputRef.current?.focus();
  };

  return (
    <div className="flex items-end gap-2 p-4 border-t border-neutral-200 no-drag">
      <div className="flex-1 relative">
        <CommandAutocomplete query={inputValue} onSelect={handleCommandSelect} />
        <textarea
          ref={inputRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (press @ to attach files)"
          className="w-full resize-none p-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          rows={1}
        />
      </div>

      <div className="flex gap-2 items-center">
        {recentFiles.length > 0 && (
          <Dropdown>
            <DropdownTrigger asChild>
              <button
                className="p-3 border border-neutral-300 rounded-lg hover:bg-neutral-50 transition-colors"
                title="Recent files"
              >
                <Clock className="w-4 h-4" />
              </button>
            </DropdownTrigger>
            <DropdownContent>
              {recentFiles.map((file) => (
                <DropdownItem
                  key={file.path}
                  onSelect={() => onRecentSelect(file)}
                >
                  {file.name}
                </DropdownItem>
              ))}
            </DropdownContent>
          </Dropdown>
        )}

        <button
          onClick={onAttach}
          className="p-3 border border-neutral-300 rounded-lg hover:bg-neutral-50 transition-colors"
          title="Attach file"
        >
          <Paperclip className="w-4 h-4" />
        </button>

        {isStreaming && (
          <button
            onClick={onInterrupt}
            className="p-3 bg-error-500 text-white rounded-lg hover:bg-error-600 transition-colors"
            title="Stop"
          >
            <Square className="w-4 h-4" />
          </button>
        )}

        <button
          onClick={handleSend}
          className="p-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          title="Send message"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
