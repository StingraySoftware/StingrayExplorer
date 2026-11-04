import { useEffect, useInsertionEffect, useRef, useState } from 'react';
import type { BackendPhase, BackendStatus, BackendStatusSource } from '@/types/backendStatus';
import { publishBackendEpoch } from '@/api/backendEpoch';

export interface BackendState {
  port: number | null;
  isReady: boolean;
  error: string | null;
  /** Null is reserved for consumers outside a managed backend provider. */
  generation: number | null;
  phase: BackendPhase;
}

export const initialBackendState: BackendState = {
  port: null,
  isReady: false,
  error: null,
  generation: null,
  phase: 'stopped',
};

type BackendTransitionListener = (previous: BackendState, next: BackendState) => void;

export function backendStateFromStatus(status: BackendStatus): BackendState {
  const generation = Number.isSafeInteger(status.generation) && status.generation >= 0
    ? status.generation
    : 0;
  const common = { generation, phase: status.phase };
  switch (status.phase) {
    case 'ready':
      if (status.port === null || generation === 0) {
        return {
          ...common,
          phase: 'error',
          port: null,
          isReady: false,
          error: 'The backend reported readiness without a valid launch generation or port.',
        };
      }
      return { ...common, port: status.port, isReady: true, error: null };
    case 'error':
      return {
        ...common,
        port: null,
        isReady: false,
        error: status.error ?? 'The Python backend failed to start.',
      };
    case 'starting':
    case 'stopped':
      return { ...initialBackendState, ...common };
  }
}

function getDefaultSource(): BackendStatusSource | null {
  if (typeof window === 'undefined' || !window.electronAPI) return null;
  return window.electronAPI;
}

export function useBackendStatus(
  source?: BackendStatusSource,
  onTransition?: BackendTransitionListener
): BackendState {
  const statusSource = source ?? getDefaultSource();
  const [backendState, setBackendState] = useState<BackendState>(() => statusSource
    ? { ...initialBackendState, generation: 0, phase: 'starting' }
    : initialBackendState);
  const currentState = useRef(backendState);
  const transitionListener = useRef(onTransition);
  useInsertionEffect(() => {
    transitionListener.current = onTransition;
  });

  useEffect(() => {
    if (!statusSource) return;

    let active = true;
    let greatestRevision = -1;
    let greatestGeneration = 0;
    let unsubscribe = (): void => undefined;

    const applyStatus = (status: BackendStatus): void => {
      if (!active || status.revision <= greatestRevision) return;
      if (status.generation < greatestGeneration) return;
      greatestRevision = status.revision;
      greatestGeneration = Math.max(greatestGeneration, status.generation ?? 0);
      const next = backendStateFromStatus(status);
      // Invalidate requests before React can batch starting/ready transitions.
      // Port reuse must not make a response from the previous process current.
      publishBackendEpoch(next.generation, next.isReady);
      transitionListener.current?.(currentState.current, next);
      currentState.current = next;
      setBackendState(next);
    };

    // Subscribe before reading the snapshot so a transition that occurs during
    // the IPC round trip cannot be lost. Revisions keep a delayed snapshot from
    // overwriting a newer event.
    try {
      unsubscribe = statusSource.onBackendStatus(applyStatus);
    } catch {
      // The atomic snapshot can still reconcile a recoverable subscription
      // failure. A later mount or renderer reload will try the handshake again.
    }

    try {
      void statusSource.getBackendStatus().then(applyStatus, () => undefined);
    } catch {
      // Treat a synchronous bridge failure like a rejected IPC request. Keeping
      // the last known state is safer than manufacturing a backend error.
    }

    return () => {
      active = false;
      unsubscribe();
    };
  }, [statusSource]);

  return backendState;
}
