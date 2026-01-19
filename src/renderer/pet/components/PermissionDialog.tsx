import React from 'react';
import * as AlertDialog from '@radix-ui/react-alert-dialog';
import { Button } from '@renderer/shared/components';
import { PermissionDecision, PermissionRequest } from '@types';

interface PermissionDialogProps {
  request: PermissionRequest | null;
  onDecision: (decision: PermissionDecision) => void;
}

export function PermissionDialog({ request, onDecision }: PermissionDialogProps) {
  const open = !!request;

  return (
    <AlertDialog.Root open={open}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 bg-black/50" />
        <AlertDialog.Content className="fixed top-1/2 left-1/2 w-[calc(100vw-32px)] max-w-[520px] max-h-[calc(100vh-32px)] -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white shadow-xl border border-neutral-200 flex flex-col overflow-hidden">
          <div className="px-6 py-4 border-b border-neutral-200">
            <AlertDialog.Title className="text-lg font-semibold text-neutral-900">
              Permission Required
            </AlertDialog.Title>
            <AlertDialog.Description className="text-sm text-neutral-500 mt-1">
              Claude wants to use a tool. Review the request before continuing.
            </AlertDialog.Description>
          </div>

          <div className="px-6 py-4 space-y-4 overflow-y-auto">
            <div>
              <div className="text-xs uppercase tracking-wide text-neutral-500">Tool</div>
              <div className="text-sm font-medium text-neutral-900 mt-1">
                {request?.toolName}
              </div>
            </div>

            <div>
              <div className="text-xs uppercase tracking-wide text-neutral-500">Description</div>
              <div className="text-sm text-neutral-700 mt-1">
                {request?.description}
              </div>
            </div>

            <div>
              <div className="text-xs uppercase tracking-wide text-neutral-500">Parameters</div>
              <pre className="mt-2 text-xs bg-neutral-50 border border-neutral-200 rounded-lg p-3 max-h-40 overflow-auto text-neutral-700">
{request ? JSON.stringify(request.input, null, 2) : ''}
              </pre>
            </div>
          </div>

          <div className="px-6 py-4 border-t border-neutral-200 flex flex-wrap gap-2 justify-end">
            <Button variant="outline" onClick={() => onDecision('deny')}>Deny</Button>
            <Button variant="primary" onClick={() => onDecision('allow')}>Allow</Button>
            <Button variant="outline" onClick={() => onDecision('deny-always')}>Always Deny</Button>
            <Button variant="secondary" onClick={() => onDecision('allow-always')}>Always Allow</Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
