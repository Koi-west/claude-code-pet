import { tokens } from '../tokens';
import { colors as baseColors, ColorScale } from '../tokens/colors';

const darkNeutral: ColorScale = {
  0: 'oklch(0.1200 0 0)',
  50: 'oklch(0.1600 0 0)',
  100: 'oklch(0.2000 0 0)',
  200: 'oklch(0.2600 0 0)',
  300: 'oklch(0.3200 0 0)',
  400: 'oklch(0.4000 0 0)',
  500: 'oklch(0.5200 0 0)',
  600: 'oklch(0.6400 0 0)',
  700: 'oklch(0.7600 0 0)',
  800: 'oklch(0.8600 0 0)',
  900: 'oklch(0.9400 0 0)',
  950: 'oklch(0.9800 0 0)',
};

const darkColors = {
  ...baseColors,
  neutral: darkNeutral,
};

export const darkTheme = {
  name: 'dark' as const,
  tokens: {
    ...tokens,
    colors: darkColors,
  },
};

export type DarkTheme = typeof darkTheme;
