import React from 'react';
import { Sun, Moon, Palette } from 'lucide-react';

type Theme = 'light' | 'dark' | 'custom';

const themes = [
  {
    id: 'light' as const,
    name: 'Light Theme',
    description: 'Clean and bright interface',
    icon: Sun,
  },
  {
    id: 'dark' as const,
    name: 'Dark Theme',
    description: 'Reduced eye strain for night use',
    icon: Moon,
  },
  {
    id: 'custom' as const,
    name: 'Custom Theme',
    description: 'Create your own color scheme',
    icon: Palette,
  },
];

interface ThemeSelectorProps {
  selectedTheme: Theme;
  onThemeChange: (theme: Theme) => void;
}

export function ThemeSelector({ selectedTheme, onThemeChange }: ThemeSelectorProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-neutral-900">Theme</h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {themes.map((theme) => (
          <button
            key={theme.id}
            onClick={() => onThemeChange(theme.id)}
            className={`p-4 rounded-lg border-2 transition-all text-left ${
              selectedTheme === theme.id
                ? 'border-primary-500 bg-primary-50'
                : 'border-neutral-200 hover:border-neutral-300'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <theme.icon className="w-5 h-5 text-primary-600" />
              <span className="font-semibold text-neutral-900">{theme.name}</span>
            </div>
            <p className="text-sm text-neutral-600">{theme.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
