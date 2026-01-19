import { useEffect, useState } from 'react';
import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '@types';

export interface ConnectionStatusState {
  status: 'connected' | 'disconnected' | 'error';
  cliAvailable: boolean;
  cliPath: string | null;
  sdkLoaded: boolean;
  error?: string;
}

const defaultStatus: ConnectionStatusState = {
  status: 'disconnected',
  cliAvailable: false,
  cliPath: null,
  sdkLoaded: false,
};

export function useConnectionStatus() {
  const [status, setStatus] = useState<ConnectionStatusState>(defaultStatus);

  useEffect(() => {
    const handleStatus = (_event: unknown, payload: ConnectionStatusState) => {
      if (payload) {
        setStatus(payload);
      }
    };

    ipcRenderer.on(IPC_CHANNELS.CONNECTION_STATUS, handleStatus);

    ipcRenderer.invoke(IPC_CHANNELS.GET_CONNECTION_STATUS)
      .then((result) => {
        if (result) {
          setStatus(result);
        }
      })
      .catch(() => {
        setStatus(defaultStatus);
      });

    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.CONNECTION_STATUS, handleStatus);
    };
  }, []);

  return status;
}
