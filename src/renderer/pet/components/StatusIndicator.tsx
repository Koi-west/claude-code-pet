import React from 'react';
import { ConnectionStatusState } from '../hooks/useConnectionStatus';

interface StatusIndicatorProps {
  status: ConnectionStatusState;
}

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const map = {
    connected: { label: 'Connected', color: 'bg-success-500' },
    disconnected: { label: 'Disconnected', color: 'bg-neutral-400' },
    error: { label: 'Error', color: 'bg-error-500' },
  } as const;

  const current = map[status.status] || map.disconnected;
  const title = status.error
    ? status.error
    : !status.cliAvailable
      ? 'Claude Code CLI not found'
      : status.cliPath
        ? `CLI: ${status.cliPath}`
        : undefined;

  return (
    <div className="flex items-center gap-2 text-xs text-neutral-600" title={title}>
      <span className={`w-2 h-2 rounded-full ${current.color}`} />
      <span>{current.label}</span>
    </div>
  );
}
