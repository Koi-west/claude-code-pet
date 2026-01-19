import { tokens, DesignTokens } from '../tokens';
import { Colors, ColorScale } from '../tokens/colors';

export type ThemeOverrides = Partial<Omit<DesignTokens, 'colors'>> & {
  colors?: Partial<{
    [K in keyof Colors]: Partial<ColorScale>;
  }>;
};

const mergeScale = (base: ColorScale, override?: Partial<ColorScale>) => ({
  ...base,
  ...(override || {}),
});

const mergeColors = (base: Colors, override?: ThemeOverrides['colors']): Colors => {
  if (!override) {
    return base;
  }

  return {
    primary: mergeScale(base.primary, override.primary),
    secondary: mergeScale(base.secondary, override.secondary),
    success: mergeScale(base.success, override.success),
    error: mergeScale(base.error, override.error),
    warning: mergeScale(base.warning, override.warning),
    neutral: mergeScale(base.neutral, override.neutral),
  };
};

export const createCustomTheme = (overrides: ThemeOverrides = {}) => {
  return {
    name: 'custom' as const,
    tokens: {
      ...tokens,
      ...overrides,
      colors: mergeColors(tokens.colors, overrides.colors),
    },
  };
};
