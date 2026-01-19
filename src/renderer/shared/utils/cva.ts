import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type VariantProps<T> = T extends {
  variant?: infer V;
  size?: infer S;
} ? { variant?: V; size?: S } : T extends { variant?: infer V } ? { variant?: V } : T extends { size?: infer S } ? { size?: S } : {};

type ColorVariant = 'primary' | 'success' | 'error' | 'warning' | 'neutral';
type SizeVariant = 'sm' | 'base' | 'lg' | 'xl';
type VariantTypes = {
  variant?: ColorVariant;
  size?: SizeVariant;
};

type ComponentProps<T extends keyof JSX.IntrinsicElements> = JSX.IntrinsicElements[T] & {
  className?: string;
};

export type ButtonProps = ComponentProps<'button'> & {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  size?: SizeVariant;
};

export type InputProps = ComponentProps<'input'> & {
  variant?: 'default' | 'outline' | 'ghost';
  size?: SizeVariant;
};

export type CardProps = ComponentProps<'div'> & {
  variant?: 'default' | 'elevated' | 'outline';
};

export type BadgeProps = ComponentProps<'span'> & {
  variant?: ColorVariant;
  size?: 'sm' | 'base' | 'lg';
};

export type DialogProps = ComponentProps<'div'> & {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
};