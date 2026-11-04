import type { BackendStatus } from '../src/types/backendStatus';

export type BackendStatusTransition =
  | { phase: 'starting' }
  | { phase: 'ready'; port: number }
  | { phase: 'error'; error: string }
  | { phase: 'stopped' };

type BackendStatusListener = (status: BackendStatus) => void;

/** Main-process owner for the renderer-visible backend lifecycle snapshot. */
export class BackendStatusStore {
  private status: BackendStatus = {
    revision: 0,
    generation: 0,
    phase: 'stopped',
    port: null,
    error: null,
  };

  constructor(private readonly notify: BackendStatusListener) {}

  getSnapshot(): BackendStatus {
    return { ...this.status };
  }

  publish(transition: BackendStatusTransition): BackendStatus {
    const revision = this.status.revision + 1;
    const generation = transition.phase === 'starting' && this.status.phase !== 'starting'
      ? this.status.generation + 1
      : transition.phase === 'ready' && this.status.generation === 0
        ? 1
        : this.status.generation;

    switch (transition.phase) {
      case 'ready':
        this.status = {
          revision,
          generation,
          phase: 'ready',
          port: transition.port,
          error: null,
        };
        break;
      case 'error':
        this.status = {
          revision,
          generation,
          phase: 'error',
          port: null,
          error: transition.error,
        };
        break;
      case 'starting':
      case 'stopped':
        this.status = {
          revision,
          generation,
          phase: transition.phase,
          port: null,
          error: null,
        };
        break;
    }

    const snapshot = this.getSnapshot();
    this.notify(snapshot);
    return snapshot;
  }
}

/** Coalesce overlapping launch requests before changing the managed process. */
export class BackendOperationGate {
  private pending: Promise<void> | null = null;

  run(operation: () => Promise<void>): Promise<void> {
    if (this.pending) return this.pending;

    // Schedule the operation after installing the gate. Even a synchronously
    // issued second IPC request then observes the same in-flight launch.
    const completion = Promise.resolve().then(operation).finally(() => {
      if (this.pending === completion) this.pending = null;
    });
    this.pending = completion;
    return completion;
  }
}
