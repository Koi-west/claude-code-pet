import React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { cn } from '../utils/cva';
import { motion, AnimatePresence } from 'framer-motion';

export interface DialogProps extends React.HTMLAttributes<HTMLDivElement> {
  open?: boolean;
  isOpen?: boolean;
  onClose: () => void;
}

const Dialog: React.FC<DialogProps> = ({
  className,
  open,
  isOpen,
  onClose,
  children,
  ...props
}) => {
  const resolvedOpen = open ?? isOpen ?? false;

  return (
    <DialogPrimitive.Root
      open={resolvedOpen}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          onClose();
        }
      }}
    >
      <DialogPrimitive.Portal>
        <AnimatePresence>
          {resolvedOpen && (
            <DialogPrimitive.Overlay asChild>
              <motion.div
                className={cn(
                  'fixed inset-0 z-50 flex items-center justify-center bg-black/50',
                  className
                )}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                {...props}
              >
                <DialogPrimitive.Content asChild>
                  <motion.div
                    className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4"
                    initial={{ scale: 0.95, opacity: 0, y: 20 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    exit={{ scale: 0.95, opacity: 0, y: 20 }}
                    transition={{ duration: 0.2 }}
                  >
                    {children}
                  </motion.div>
                </DialogPrimitive.Content>
              </motion.div>
            </DialogPrimitive.Overlay>
          )}
        </AnimatePresence>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
};

export interface DialogHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}

export const DialogHeader: React.FC<DialogHeaderProps> = ({
  className,
  children,
  ...props
}) => {
  return (
    <div
      className={cn('px-6 py-4 border-b border-neutral-200', className)}
      {...props}
    >
      {children}
    </div>
  );
};

export interface DialogTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}

export const DialogTitle: React.FC<DialogTitleProps> = ({
  className,
  children,
  ...props
}) => {
  return (
    <h3
      className={cn('text-lg font-semibold text-neutral-900', className)}
      {...props}
    >
      {children}
    </h3>
  );
};

export interface DialogContentProps extends React.HTMLAttributes<HTMLDivElement> {}

export const DialogContent: React.FC<DialogContentProps> = ({
  className,
  children,
  ...props
}) => {
  return (
    <div
      className={cn('px-6 py-4', className)}
      {...props}
    >
      {children}
    </div>
  );
};

export interface DialogFooterProps extends React.HTMLAttributes<HTMLDivElement> {}

export const DialogFooter: React.FC<DialogFooterProps> = ({
  className,
  children,
  ...props
}) => {
  return (
    <div
      className={cn('px-6 py-4 border-t border-neutral-200 flex justify-end gap-2', className)}
      {...props}
    >
      {children}
    </div>
  );
};

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
}

export const Progress: React.FC<ProgressProps> = ({
  className,
  value,
  max = 100,
  ...props
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div
      className={cn('w-full bg-neutral-200 rounded-full h-2.5', className)}
      {...props}
    >
      <div
        className="bg-primary-500 h-2.5 rounded-full transition-all duration-300"
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
};

export default Dialog;
