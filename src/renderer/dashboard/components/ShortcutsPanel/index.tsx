import React, { useMemo, useState, useEffect } from 'react';
import { Button } from '@renderer/shared/components';
import { Input } from '@renderer/shared/components';
import { useSettings } from '../../hooks/useSettings';

interface Shortcut {
  id: string;
  name: string;
  description: string;
  defaultKey: string;
  settingKey?: 'showDashboardShortcut' | 'toggleChatShortcut';
  isEditable: boolean;
}

const shortcuts: Shortcut[] = [
  {
    id: 'showDashboard',
    name: 'Show Dashboard',
    description: 'Open the Kohaku dashboard',
    defaultKey: 'CmdOrCtrl+Shift+K',
    settingKey: 'showDashboardShortcut',
    isEditable: true,
  },
  {
    id: 'toggleChat',
    name: 'Toggle Chat',
    description: 'Show or hide the pet window',
    defaultKey: 'CmdOrCtrl+Shift+C',
    settingKey: 'toggleChatShortcut',
    isEditable: true,
  },
  {
    id: 'clearChat',
    name: 'Clear Chat',
    description: 'Clear all chat messages (coming soon)',
    defaultKey: 'CmdOrCtrl+Shift+X',
    isEditable: false,
  },
  {
    id: 'newSession',
    name: 'New Session',
    description: 'Start a new conversation session (coming soon)',
    defaultKey: 'CmdOrCtrl+Shift+N',
    isEditable: false,
  },
  {
    id: 'toggleAlwaysOnTop',
    name: 'Toggle Always on Top',
    description: 'Keep pet window always visible (coming soon)',
    defaultKey: 'CmdOrCtrl+Shift+T',
    isEditable: false,
  },
];

const buildShortcut = (event: React.KeyboardEvent<HTMLInputElement>) => {
  const keys: string[] = [];
  const isCmdOrCtrl = event.metaKey || event.ctrlKey;

  if (isCmdOrCtrl) keys.push('CmdOrCtrl');
  if (event.altKey) keys.push('Alt');
  if (event.shiftKey) keys.push('Shift');

  const key = event.key;
  if (!['Control', 'Shift', 'Alt', 'Meta'].includes(key)) {
    keys.push(key.length === 1 ? key.toUpperCase() : key);
  }

  return keys.join('+');
};

export function ShortcutsPanel() {
  const { settings, updateSettings, saveSettings } = useSettings();
  const [editingShortcut, setEditingShortcut] = useState<string | null>(null);
  const [shortcutKeys, setShortcutKeys] = useState<Record<string, string>>({});

  useEffect(() => {
    const initialKeys = shortcuts.reduce((acc, shortcut) => {
      if (shortcut.settingKey) {
        acc[shortcut.id] = settings[shortcut.settingKey] as string;
      } else {
        acc[shortcut.id] = shortcut.defaultKey;
      }
      return acc;
    }, {} as Record<string, string>);
    setShortcutKeys(initialKeys);
  }, [settings]);

  const conflicts = useMemo(() => {
    const used = new Map<string, string[]>();
    Object.entries(shortcutKeys).forEach(([id, value]) => {
      if (!value) return;
      const current = used.get(value) || [];
      used.set(value, [...current, id]);
    });

    const conflictSet = new Set<string>();
    used.forEach((ids) => {
      if (ids.length > 1) {
        ids.forEach((id) => conflictSet.add(id));
      }
    });

    return conflictSet;
  }, [shortcutKeys]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, shortcutId: string) => {
    e.preventDefault();
    const shortcut = buildShortcut(e);
    if (!shortcut) {
      return;
    }

    setShortcutKeys((prev) => ({
      ...prev,
      [shortcutId]: shortcut,
    }));
  };

  const handleSave = () => {
    if (conflicts.size > 0) {
      return;
    }

    updateSettings({
      showDashboardShortcut: shortcutKeys.showDashboard,
      toggleChatShortcut: shortcutKeys.toggleChat,
    });
    saveSettings();
    setEditingShortcut(null);
  };

  const handleReset = () => {
    const defaultKeys = shortcuts.reduce((acc, shortcut) => {
      acc[shortcut.id] = shortcut.defaultKey;
      return acc;
    }, {} as Record<string, string>);

    setShortcutKeys(defaultKeys);

    updateSettings({
      showDashboardShortcut: defaultKeys.showDashboard,
      toggleChatShortcut: defaultKeys.toggleChat,
    });
    saveSettings();
    setEditingShortcut(null);
  };

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold text-neutral-900 mb-2">Keyboard Shortcuts</h3>
        <p className="text-neutral-600 text-sm">
          Customize keyboard shortcuts for quick access to frequently used features.
        </p>
      </div>

      <div className="bg-neutral-50 rounded-lg p-6 space-y-6">
        {shortcuts.map((shortcut) => {
          const hasConflict = conflicts.has(shortcut.id);
          return (
            <div
              key={shortcut.id}
              className="flex items-center justify-between p-4 bg-white rounded-lg border border-neutral-200"
            >
              <div className="flex-1">
                <h4 className="font-medium text-neutral-900 mb-1">{shortcut.name}</h4>
                <p className="text-sm text-neutral-600">{shortcut.description}</p>
                {hasConflict && (
                  <p className="text-xs text-error-500 mt-1">Shortcut conflict detected</p>
                )}
              </div>

              <div className="flex items-center gap-3">
                {editingShortcut === shortcut.id ? (
                  <div className="flex items-center gap-2">
                    <Input
                      type="text"
                      value={shortcutKeys[shortcut.id]}
                      onKeyDown={(e) => handleKeyDown(e, shortcut.id)}
                      placeholder="Press keys..."
                      className="w-40 text-center font-mono"
                      autoFocus
                      onBlur={() => setEditingShortcut(null)}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEditingShortcut(null)}
                    >
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <div className="px-3 py-1 bg-neutral-100 rounded font-mono text-sm font-medium">
                      {shortcutKeys[shortcut.id]}
                    </div>
                    {shortcut.isEditable && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setEditingShortcut(shortcut.id)}
                      >
                        Edit
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex gap-2">
        <Button variant="primary" onClick={handleSave} disabled={conflicts.size > 0}>
          Save Shortcuts
        </Button>
        <Button variant="outline" onClick={handleReset}>
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}
