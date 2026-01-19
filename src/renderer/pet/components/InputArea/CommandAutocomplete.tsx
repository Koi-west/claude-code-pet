import React, { useMemo } from 'react';

interface Command {
  id: string;
  label: string;
  description: string;
  value: string;
}

const commands: Command[] = [
  { id: 'help', label: 'Help', description: 'Show available commands', value: '/help' },
  { id: 'clear', label: 'Clear', description: 'Clear the conversation', value: '/clear' },
  { id: 'new', label: 'New Session', description: 'Start a fresh session', value: '/new' },
];

interface CommandAutocompleteProps {
  query: string;
  onSelect: (command: Command) => void;
}

export function CommandAutocomplete({ query, onSelect }: CommandAutocompleteProps) {
  const trimmed = query.trim();
  const show = trimmed.startsWith('/');

  const results = useMemo(() => {
    if (!show) return [];
    const search = trimmed.slice(1).toLowerCase();
    return commands.filter((command) =>
      command.label.toLowerCase().includes(search) ||
      command.id.includes(search)
    );
  }, [trimmed, show]);

  if (!show || results.length === 0) {
    return null;
  }

  return (
    <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-neutral-200 rounded-lg shadow-lg overflow-hidden">
      {results.map((command) => (
        <button
          key={command.id}
          onClick={() => onSelect(command)}
          className="w-full text-left px-3 py-2 hover:bg-neutral-50 transition-colors"
        >
          <div className="text-sm font-medium text-neutral-900">{command.label}</div>
          <div className="text-xs text-neutral-500">{command.description}</div>
        </button>
      ))}
    </div>
  );
}
