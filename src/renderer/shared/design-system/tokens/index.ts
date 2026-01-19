import { colors } from './colors';
import { typography } from './typography';
import { spacing } from './spacing';
import { radius } from './radius';
import { shadows } from './shadows';

export { colors } from './colors';
export type { Colors, ColorScale } from './colors';
export { typography } from './typography';
export type { TypographyTokens } from './typography';
export { spacing } from './spacing';
export type { SpacingTokens } from './spacing';
export { radius } from './radius';
export type { RadiusTokens } from './radius';
export { shadows } from './shadows';
export type { ShadowTokens } from './shadows';

export const tokens = {
  colors,
  typography,
  spacing,
  radius,
  shadows,
};

export type DesignTokens = typeof tokens;
