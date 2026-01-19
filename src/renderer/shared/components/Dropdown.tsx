import React from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { cn } from '../utils/cva';

export const Dropdown = DropdownMenu.Root;
export const DropdownTrigger = DropdownMenu.Trigger;

export const DropdownContent = React.forwardRef<
  React.ElementRef<typeof DropdownMenu.Content>,
  React.ComponentPropsWithoutRef<typeof DropdownMenu.Content>
>(({ className, sideOffset = 6, ...props }, ref) => (
  <DropdownMenu.Portal>
    <DropdownMenu.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        'z-50 min-w-[160px] overflow-hidden rounded-lg border border-neutral-200 bg-white p-1 shadow-md',
        className
      )}
      {...props}
    />
  </DropdownMenu.Portal>
));
DropdownContent.displayName = DropdownMenu.Content.displayName;

export const DropdownItem = React.forwardRef<
  React.ElementRef<typeof DropdownMenu.Item>,
  React.ComponentPropsWithoutRef<typeof DropdownMenu.Item>
>(({ className, ...props }, ref) => (
  <DropdownMenu.Item
    ref={ref}
    className={cn(
      'flex cursor-pointer select-none items-center rounded-md px-3 py-2 text-sm text-neutral-700 outline-none transition-colors focus:bg-neutral-100',
      className
    )}
    {...props}
  />
));
DropdownItem.displayName = DropdownMenu.Item.displayName;

export const DropdownSeparator = React.forwardRef<
  React.ElementRef<typeof DropdownMenu.Separator>,
  React.ComponentPropsWithoutRef<typeof DropdownMenu.Separator>
>(({ className, ...props }, ref) => (
  <DropdownMenu.Separator
    ref={ref}
    className={cn('my-1 h-px bg-neutral-200', className)}
    {...props}
  />
));
DropdownSeparator.displayName = DropdownMenu.Separator.displayName;
