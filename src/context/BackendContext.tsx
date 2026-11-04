import React, { createContext, useCallback, useContext, useLayoutEffect } from 'react';
import { QueryClientContext } from '@tanstack/react-query';
import { useBackendStatus, type BackendState } from '@/hooks/useBackendStatus';
import type { BackendStatusSource } from '@/types/backendStatus';
import { publishBackendEpoch } from '@/api/backendEpoch';

export const BackendContext = createContext<BackendState>({
  port: null,
  isReady: false,
  error: null,
  generation: null,
  phase: 'stopped',
});

export const useBackendContext = (): BackendState => useContext(BackendContext);

interface BackendStatusProviderProps {
  children: React.ReactNode;
  source?: BackendStatusSource;
}

export const BackendStatusProvider: React.FC<BackendStatusProviderProps> = ({
  children,
  source,
}) => {
  const queryClient = useContext(QueryClientContext);
  const clearPreviousBackend = useCallback((previous: BackendState, next: BackendState) => {
    const hadBackend = previous.generation !== null && previous.generation > 0;
    const lostBackend = hadBackend && (previous.generation !== next.generation ||
      (previous.isReady && !next.isReady));
    if (!lostBackend) {
      if (next.isReady && !previous.isReady) void queryClient?.invalidateQueries();
      return;
    }
    // Run before new-generation consumers can start their queries. Cancelling
    // also detaches promises whose query functions ignore AbortSignal.
    void queryClient?.cancelQueries();
    // Clearing the cache alone leaves mounted observers holding the last data
    // until something else rerenders them. Reset first to notify even consumers
    // which do not read BackendContext, then discard the old query objects.
    for (const query of queryClient?.getQueryCache().getAll() ?? []) query.reset();
    queryClient?.clear();
  }, [queryClient]);
  const backendState = useBackendStatus(source, clearPreviousBackend);
  const managedState = backendState.generation === null
    ? { ...backendState, generation: 0, phase: 'starting' as const }
    : backendState;
  useLayoutEffect(() => {
    // Block manual requests during the initial IPC handshake as well as queries
    // whose hooks already gate themselves on backend readiness.
    if (managedState.generation === 0) publishBackendEpoch(0, false);
  }, [managedState.generation]);
  return <BackendContext.Provider value={managedState}>{children}</BackendContext.Provider>;
};
