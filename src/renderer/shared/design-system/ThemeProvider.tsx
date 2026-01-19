import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { ipcRenderer } from 'electron';
import { lightTheme } from './themes/light';
import { darkTheme } from './themes/dark';
import { createCustomTheme, ThemeOverrides } from './themes/custom';
import type { DesignTokens } from './tokens';

export type ThemeName = 'light' | 'dark' | 'custom';

interface ThemeContextValue {
  theme: ThemeName;
  setTheme: (theme: ThemeName) => void;
  tokens: DesignTokens;
  customTheme: ThemeOverrides;
  setCustomTheme: (theme: ThemeOverrides) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const motionDurations: Record<string, string> = {
  instant: '0ms',
  fast: '140ms',
  normal: '220ms',
  slow: '360ms',
};

const applyTokensToRoot = (tokens: DesignTokens, theme: ThemeName) => {
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.style.colorScheme = theme === 'dark' ? 'dark' : 'light';

  Object.entries(tokens.colors).forEach(([family, scale]) => {
    Object.entries(scale).forEach(([shade, value]) => {
      root.style.setProperty(`--color-${family}-${shade}`, value as string);
    });
  });

  root.style.setProperty('--font-sans', tokens.typography.fontFamily.sans);
  root.style.setProperty('--font-mono', tokens.typography.fontFamily.mono);
  root.style.setProperty('--font-size-base', tokens.typography.fontSize.base);

  Object.entries(tokens.radius).forEach(([key, value]) => {
    root.style.setProperty(`--radius-${key}`, value);
  });

  Object.entries(tokens.shadows).forEach(([key, value]) => {
    root.style.setProperty(`--shadow-${key}`, value);
  });
};

export interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: ThemeName;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({
  children,
  defaultTheme = 'light',
}) => {
  const [theme, setTheme] = useState<ThemeName>(defaultTheme);
  const [customTheme, setCustomTheme] = useState<ThemeOverrides>({});

  useEffect(() => {
    let isMounted = true;

    const loadSettings = async () => {
      try {
        const settings = await ipcRenderer.invoke('settings:get');
        if (!isMounted || !settings) {
          return;
        }

        if (settings.theme) {
          setTheme(settings.theme);
        }

        if (settings.customTheme) {
          setCustomTheme(settings.customTheme);
        }

        if (settings.fontSize) {
          document.documentElement.style.fontSize = `${settings.fontSize}px`;
        }

        if (settings.animationSpeed) {
          document.documentElement.style.setProperty(
            '--motion-duration',
            motionDurations[settings.animationSpeed] || motionDurations.normal
          );
        }
      } catch (error) {
        console.warn('Failed to load settings for theme:', error);
      }
    };

    loadSettings();

    const handleSettingsUpdated = (_event: unknown, updatedSettings: any) => {
      if (!updatedSettings) {
        return;
      }

      if (updatedSettings.theme) {
        setTheme(updatedSettings.theme);
      }

      if (updatedSettings.customTheme) {
        setCustomTheme(updatedSettings.customTheme);
      }

      if (updatedSettings.fontSize) {
        document.documentElement.style.fontSize = `${updatedSettings.fontSize}px`;
      }

      if (updatedSettings.animationSpeed) {
        document.documentElement.style.setProperty(
          '--motion-duration',
          motionDurations[updatedSettings.animationSpeed] || motionDurations.normal
        );
      }
    };

    ipcRenderer.on('settings:updated', handleSettingsUpdated);

    return () => {
      isMounted = false;
      ipcRenderer.removeListener('settings:updated', handleSettingsUpdated);
    };
  }, []);

  const tokens = useMemo(() => {
    if (theme === 'dark') {
      return darkTheme.tokens;
    }

    if (theme === 'custom') {
      return createCustomTheme(customTheme).tokens;
    }

    return lightTheme.tokens;
  }, [theme, customTheme]);

  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }
    applyTokensToRoot(tokens, theme);
  }, [tokens, theme]);

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      tokens,
      customTheme,
      setCustomTheme,
    }),
    [theme, tokens, customTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export default ThemeProvider;
