import { describe, expect, it, vi } from 'vitest';
import { BackendOperationGate, BackendStatusStore } from '../../electron/backendStatus';

describe('BackendStatusStore', () => {
  it('owns an atomic, monotonically revisioned lifecycle snapshot', () => {
    const notify = vi.fn();
    const store = new BackendStatusStore(notify);

    expect(store.getSnapshot()).toEqual({
      revision: 0,
      generation: 0,
      phase: 'stopped',
      port: null,
      error: null,
    });

    expect(store.publish({ phase: 'starting' })).toEqual({
      revision: 1,
      generation: 1,
      phase: 'starting',
      port: null,
      error: null,
    });
    expect(store.publish({ phase: 'ready', port: 54321 })).toEqual({
      revision: 2,
      generation: 1,
      phase: 'ready',
      port: 54321,
      error: null,
    });
    expect(store.publish({ phase: 'error', error: 'backend failed' })).toEqual({
      revision: 3,
      generation: 1,
      phase: 'error',
      port: null,
      error: 'backend failed',
    });

    expect(notify).toHaveBeenCalledTimes(3);
    expect(notify).toHaveBeenLastCalledWith(store.getSnapshot());
  });

  it('does not expose its stored snapshot for external mutation', () => {
    const store = new BackendStatusStore(() => undefined);
    const snapshot = store.publish({ phase: 'ready', port: 49152 });
    snapshot.phase = 'stopped';
    snapshot.port = null;

    expect(store.getSnapshot()).toEqual({
      revision: 1,
      generation: 1,
      phase: 'ready',
      port: 49152,
      error: null,
    });
  });

  it('changes generation for a new launch even when the same port is reused', () => {
    const store = new BackendStatusStore(() => undefined);
    store.publish({ phase: 'starting' });
    const first = store.publish({ phase: 'ready', port: 54321 });
    store.publish({ phase: 'starting' });
    const replacement = store.publish({ phase: 'ready', port: 54321 });

    expect(first.generation).toBe(1);
    expect(replacement.generation).toBe(2);
    expect(first.port).toBe(replacement.port);
    expect(replacement.revision).toBeGreaterThan(first.revision);
  });

  it('keeps one generation across duplicate starting, ready, and terminal notifications', () => {
    const store = new BackendStatusStore(() => undefined);
    store.publish({ phase: 'starting' });
    expect(store.publish({ phase: 'starting' }).generation).toBe(1);
    expect(store.publish({ phase: 'ready', port: 54321 }).generation).toBe(1);
    expect(store.publish({ phase: 'ready', port: 54321 }).generation).toBe(1);
    expect(store.publish({ phase: 'error', error: 'lost process' }).generation).toBe(1);
    expect(store.publish({ phase: 'stopped' }).generation).toBe(1);
    expect(store.publish({ phase: 'starting' }).generation).toBe(2);
  });

  it('does not expose its generation for mutation through returned snapshots', () => {
    const store = new BackendStatusStore(() => undefined);
    const snapshot = store.publish({ phase: 'starting' });
    snapshot.generation = 99;
    expect(store.getSnapshot().generation).toBe(1);
  });
});

describe('BackendOperationGate', () => {
  it('coalesces concurrent initialization and restart into one launch', async () => {
    const gate = new BackendOperationGate();
    let finish!: () => void;
    const initialization = vi.fn(() => new Promise<void>((resolve) => { finish = resolve; }));
    const restart = vi.fn(async () => undefined);

    const initial = gate.run(initialization);
    const duplicateInitial = gate.run(initialization);
    const duringStartup = gate.run(restart);
    await Promise.resolve();

    expect(initialization).toHaveBeenCalledOnce();
    expect(restart).not.toHaveBeenCalled();
    expect(initial).toBe(duplicateInitial);
    expect(initial).toBe(duringStartup);
    finish();
    await initial;

    await gate.run(restart);
    expect(restart).toHaveBeenCalledOnce();
  });

  it('releases the gate after a failed operation so a new launch can retry', async () => {
    const gate = new BackendOperationGate();
    const failure = new Error('failed to launch');
    const first = gate.run(async () => { throw failure; });
    expect(gate.run(async () => undefined)).toBe(first);
    await expect(first).rejects.toBe(failure);

    const retry = vi.fn(async () => undefined);
    await gate.run(retry);
    expect(retry).toHaveBeenCalledOnce();
  });
});
