export type BackendPhase = 'starting' | 'ready' | 'error' | 'stopped';

export interface BackendStatus {
  revision: number;
  /** Main-process launch identity; stable across status updates for one backend. */
  generation: number;
  phase: BackendPhase;
  port: number | null;
  error: string | null;
}

export interface BackendStatusSource {
  getBackendStatus: () => Promise<BackendStatus>;
  onBackendStatus: (callback: (status: BackendStatus) => void) => () => void;
}
