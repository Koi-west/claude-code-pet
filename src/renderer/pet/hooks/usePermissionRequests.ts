import { useEffect, useState, useCallback } from 'react';
import { ipcRenderer } from 'electron';
import { IPC_CHANNELS, PermissionRequest, PermissionDecision } from '@types';

export function usePermissionRequests() {
  const [request, setRequest] = useState<PermissionRequest | null>(null);

  useEffect(() => {
    const handleRequest = (_event: unknown, payload: PermissionRequest) => {
      setRequest(payload);
    };

    ipcRenderer.on(IPC_CHANNELS.PERMISSION_REQUEST, handleRequest);

    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.PERMISSION_REQUEST, handleRequest);
    };
  }, []);

  const respond = useCallback(async (decision: PermissionDecision) => {
    if (!request) {
      return;
    }
    await ipcRenderer.invoke(IPC_CHANNELS.PERMISSION_RESPONSE, request.id, decision);
    setRequest(null);
  }, [request]);

  return {
    request,
    respond,
  };
}
