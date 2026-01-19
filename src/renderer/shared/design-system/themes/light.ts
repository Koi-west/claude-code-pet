import { tokens } from '../tokens';

export const lightTheme = {
  name: 'light' as const,
  tokens,
};

export type LightTheme = typeof lightTheme;
