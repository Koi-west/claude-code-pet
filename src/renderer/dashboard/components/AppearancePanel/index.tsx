import React, { useState } from 'react';
import { Button } from '@renderer/shared/components';
import { Switch } from '@renderer/shared/components';
import { ThemeSelector } from './ThemeSelector';
import { FontSizeControl } from './FontSizeControl';
import { AnimationSpeedControl } from './AnimationSpeedControl';
import { useSettings } from '../../hooks/useSettings';

type Theme = 'light' | 'dark' | 'custom';
type AnimationSpeed = 'instant' | 'fast' | 'normal' | 'slow';

export function AppearancePanel() {
  const { settings, updateSettings, saveSettings, resetSettings } = useSettings();

  const [theme, setTheme] = useState<Theme>(settings.theme as Theme);
  const [fontSize, setFontSize] = useState(settings.fontSize);
  const [animationSpeed, setAnimationSpeed] = useState<AnimationSpeed>(settings.animationSpeed as AnimationSpeed);
  const [alwaysOnTop, setAlwaysOnTop] = useState(settings.alwaysOnTop);

  const handleSave = () => {
    updateSettings({
      theme,
      fontSize,
      animationSpeed,
      alwaysOnTop,
    });
    saveSettings();
  };

  const handleReset = async () => {
    const defaultSettings = await resetSettings();
    setTheme(defaultSettings.theme as Theme);
    setFontSize(defaultSettings.fontSize);
    setAnimationSpeed(defaultSettings.animationSpeed as AnimationSpeed);
    setAlwaysOnTop(defaultSettings.alwaysOnTop);
  };

  return (
    <div className="space-y-8">
      <ThemeSelector
        selectedTheme={theme}
        onThemeChange={setTheme}
      />

      <FontSizeControl
        fontSize={fontSize}
        onFontSizeChange={setFontSize}
      />

      <AnimationSpeedControl
        speed={animationSpeed}
        onSpeedChange={setAnimationSpeed}
      />

      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-neutral-900">Window Behavior</h3>

        <div className="bg-neutral-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="block text-sm font-medium text-neutral-700">
                Always on Top
              </label>
              <p className="text-xs text-neutral-500">
                Keep the pet window always visible on top of other windows.
              </p>
            </div>
            <Switch
              checked={alwaysOnTop}
              onCheckedChange={setAlwaysOnTop}
            />
          </div>
        </div>
      </div>

      <div className="flex gap-2">
        <Button variant="primary" onClick={handleSave}>
          Save Appearance Settings
        </Button>
        <Button variant="outline" onClick={handleReset}>
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}
