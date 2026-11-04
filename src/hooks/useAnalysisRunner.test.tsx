import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useAnalysisRunner } from './useAnalysisRunner';
import { useUIStore } from '@/store/uiStore';
import { publishBackendEpoch } from '@/api/backendEpoch';
import { BackendContext } from '@/context/BackendContext';
import type { BackendState } from './useBackendStatus';

describe('useAnalysisRunner', () => {
  beforeEach(() => {
    useUIStore.setState({ notifications: [], unreadNotificationCount: 0 });
  });

  it('stores the result and pushes a success notification', async () => {
    const { result } = renderHook(() => useAnalysisRunner<{ v: number }>('Test Op'));
    await act(async () => {
      await result.current.run(async () => ({
        success: true,
        data: { v: 42 },
        message: 'computed',
        error: null,
      }));
    });
    expect(result.current.result?.v).toBe(42);
    expect(result.current.running).toBe(false);
    expect(result.current.error).toBeNull();
    const notes = useUIStore.getState().notifications;
    expect(notes[0].type).toBe('success');
    expect(notes[0].title).toBe('Test Op');
  });

  it('captures success:false as an error and keeps the previous result', async () => {
    const { result } = renderHook(() => useAnalysisRunner<{ v: number }>('Test Op'));
    await act(async () => {
      await result.current.run(async () => ({
        success: true,
        data: { v: 1 },
        message: '',
        error: null,
      }));
    });
    await act(async () => {
      await result.current.run(async () => ({
        success: false,
        data: null,
        message: 'bad dt',
        error: 'bad dt',
        warnings: ['Approximate conversion was not performed.'],
      }));
    });
    expect(result.current.error).toBe('bad dt');
    expect(result.current.result?.v).toBe(1);
    expect(result.current.warnings).toEqual(['Approximate conversion was not performed.']);
    expect(useUIStore.getState().notifications[0].type).toBe('error');
  });

  it('reset clears result, error, and running', async () => {
    const { result } = renderHook(() => useAnalysisRunner<{ v: number }>('Test Op'));
    await act(async () => {
      await result.current.run(async () => ({
        success: true,
        data: { v: 7 },
        message: '',
        error: null,
      }));
    });
    act(() => {
      result.current.reset();
    });
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.running).toBe(false);
    expect(result.current.warnings).toEqual([]);
  });

  it('captures thrown errors (network failures)', async () => {
    const { result } = renderHook(() => useAnalysisRunner('Test Op'));
    await act(async () => {
      await result.current.run(async () => {
        throw new Error('connection refused');
      });
    });
    expect(result.current.error).toBe('connection refused');
  });
});

// These tests use real deferred promises so a lifecycle transition can happen
// between submission and completion, independently of React's render timing.
function deferredResult<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function success<T>(data: T) {
  return { success: true, data, message: 'done', error: null };
}

describe('analysis result identity and request lifetime', () => {
  beforeEach(() => {
    useUIStore.setState({ notifications: [], unreadNotificationCount: 0 });
    publishBackendEpoch(null, true);
  });

  it('freezes a detached submitted snapshot before a pending calculation completes', async () => {
    const pending = deferredResult<ReturnType<typeof success<{ value: number }>>>();
    const inputs = { event_list_name: 'original', frequency_range: [0.1, 2], settings: { dt: 0.125 } };
    const { result } = renderHook(() => useAnalysisRunner<{ value: number }>('Spectrum'));
    let completion!: Promise<void>;
    act(() => { completion = result.current.run(() => pending.promise, inputs); });
    inputs.event_list_name = 'edited';
    inputs.frequency_range[0] = 99;
    inputs.settings.dt = 1;
    await act(async () => { pending.resolve(success({ value: 7 })); await completion; });
    expect(result.current.resultInputs).toEqual({
      event_list_name: 'original', frequency_range: [0.1, 2], settings: { dt: 0.125 },
    });
    expect(Object.isFrozen(result.current.resultInputs)).toBe(true);
    expect(Object.isFrozen(result.current.resultInputs?.frequency_range)).toBe(true);
    expect(Object.isFrozen(result.current.resultInputs?.settings)).toBe(true);
    expect(result.current.resultStatus).toBe('current');
  });

  it('keeps the successful inputs and identity when a later rerun fails', async () => {
    const { result } = renderHook(() => useAnalysisRunner('Spectrum'));
    await act(async () => { await result.current.run(async () => success({ result_id: 'spectrum-1', backend_session_id: 'session-1' }), { dt: 0.125 }); });
    const identity = result.current.resultIdentity;
    await act(async () => { await result.current.run(async () => ({ success: false, data: null, message: 'Rejected', error: null }), { dt: 0 }); });
    expect(result.current.resultInputs).toEqual({ dt: 0.125 });
    expect(result.current.resultIdentity).toBe(identity);
    expect(identity?.resultId).toBe('spectrum-1');
    expect(identity?.backendSessionId).toBe('session-1');
    expect(result.current.resultStatus).toBe('previous');
  });

  it('falls back to a detached backend provenance snapshot when no inputs are supplied', async () => {
    const provenance = { input_source: { name: 'original' }, parameters: { dt: 0.125 } };
    const { result } = renderHook(() => useAnalysisRunner('Utility'));
    await act(async () => { await result.current.run(async () => success({ provenance })); });
    provenance.parameters.dt = 99;
    provenance.input_source.name = 'reused';
    expect(result.current.resultInputs).toEqual({ input_source: { name: 'original' }, parameters: { dt: 0.125 } });
  });

  it('ignores an older overlapping response and its error notification', async () => {
    const older = deferredResult<ReturnType<typeof success<{ value: number }>>>();
    const newer = deferredResult<ReturnType<typeof success<{ value: number }>>>();
    const { result } = renderHook(() => useAnalysisRunner<{ value: number }>('Spectrum'));
    let first!: Promise<void>;
    let second!: Promise<void>;
    act(() => {
      first = result.current.run(() => older.promise, { dt: 1 });
      second = result.current.run(() => newer.promise, { dt: 2 });
    });
    await act(async () => { newer.resolve(success({ value: 2 })); await second; });
    await act(async () => { older.reject(new Error('Old failure')); await first; });
    expect(result.current.result).toEqual({ value: 2 });
    expect(result.current.resultInputs).toEqual({ dt: 2 });
    expect(result.current.error).toBeNull();
    expect(useUIStore.getState().notifications).toHaveLength(1);
  });

  it('does not resurrect a result after reset or unmount', async () => {
    const pending = deferredResult<ReturnType<typeof success<{ value: number }>>>();
    const { result, unmount } = renderHook(() => useAnalysisRunner<{ value: number }>('Spectrum'));
    let completion!: Promise<void>;
    act(() => { completion = result.current.run(() => pending.promise, { dt: 1 }); });
    act(() => result.current.reset());
    await act(async () => { pending.resolve(success({ value: 1 })); await completion; });
    expect(result.current.result).toBeNull();
    expect(result.current.resultStatus).toBe('empty');
    const abandoned = deferredResult<ReturnType<typeof success<{ value: number }>>>();
    act(() => { completion = result.current.run(() => abandoned.promise); });
    unmount();
    await act(async () => { abandoned.reject(new Error('After unmount')); await completion; });
    expect(useUIStore.getState().notifications).toHaveLength(0);
  });

  it('keeps old results stale through a same-port restart and rejects old pending work before rerender', async () => {
    let backend: BackendState = { generation: 1, phase: 'ready', port: 50001, isReady: true, error: null };
    publishBackendEpoch(1, true);
    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <BackendContext.Provider value={backend}>{children}</BackendContext.Provider>
    );
    const { result, rerender } = renderHook(() => useAnalysisRunner('Spectrum'), { wrapper });
    await act(async () => { await result.current.run(async () => success({ result_id: 'first' }), { dt: 1 }); });
    const pending = deferredResult<ReturnType<typeof success<{ result_id: string }>>>();
    let completion!: Promise<void>;
    act(() => { completion = result.current.run(() => pending.promise, { dt: 2 }); });
    useUIStore.setState({ notifications: [] });
    // IPC listener invalidates synchronously, before React receives new context.
    publishBackendEpoch(2, false);
    publishBackendEpoch(2, true);
    await act(async () => { pending.resolve(success({ result_id: 'old-pending' })); await completion; });
    expect(result.current.result).toEqual({ result_id: 'first' });
    expect(useUIStore.getState().notifications).toHaveLength(0);
    backend = { ...backend, generation: 2 };
    rerender();
    expect(result.current.resultStale).toBe(true);
    expect(result.current.resultStatus).toBe('stale');
    expect(result.current.running).toBe(false);
    expect(result.current.resultInputs).toEqual({ dt: 1 });
    await act(async () => { await result.current.run(async () => success({ result_id: 'new' }), { dt: 3 }); });
    expect(result.current.resultStale).toBe(false);
    expect(result.current.resultIdentity?.backendGeneration).toBe(2);
    expect(result.current.resultInputs).toEqual({ dt: 3 });
  });

  it('clears pending state when the starting event was missed and no earlier result exists', async () => {
    let backend: BackendState = { generation: 1, phase: 'ready', port: 50001, isReady: true, error: null };
    publishBackendEpoch(1, true);
    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <BackendContext.Provider value={backend}>{children}</BackendContext.Provider>
    );
    const { result, rerender } = renderHook(() => useAnalysisRunner('Spectrum'), { wrapper });
    const pending = deferredResult<ReturnType<typeof success<{ value: number }>>>();
    let completion!: Promise<void>;
    act(() => { completion = result.current.run(() => pending.promise); });
    publishBackendEpoch(2, true);
    backend = { ...backend, generation: 2 };
    rerender();
    expect(result.current.running).toBe(false);
    await act(async () => { pending.resolve(success({ value: 1 })); await completion; });
    expect(result.current.result).toBeNull();
    expect(useUIStore.getState().notifications).toHaveLength(0);
  });

  it('blocks calculations while a managed backend is not ready', async () => {
    const backend: BackendState = { generation: 0, phase: 'starting', port: null, isReady: false, error: null };
    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <BackendContext.Provider value={backend}>{children}</BackendContext.Provider>
    );
    const call = vi.fn(async () => success({ value: 1 }));
    const { result } = renderHook(() => useAnalysisRunner('Spectrum'), { wrapper });
    await act(async () => { await result.current.run(call); });
    expect(call).not.toHaveBeenCalled();
    expect(result.current.backendAvailable).toBe(false);
    expect(result.current.error).toMatch(/not ready/);
  });
});

it('owns a detached response so caller mutations cannot rewrite original result parameters', async () => {
  const response = { result_id: 'original-id', power: [1, 2], parameters: { dt: 0.125 } };
  const { result } = renderHook(() => useAnalysisRunner<typeof response>('Spectrum'));
  await act(async () => { await result.current.run(async () => success(response), { dt: 0.125 }); });
  response.parameters.dt = 99;
  response.power[0] = 999;
  expect(result.current.result?.parameters.dt).toBe(0.125);
  expect(result.current.result?.power).toEqual([1, 2]);
  expect(Object.isFrozen(result.current.result?.power)).toBe(false);
});

it('does not cancel new-generation work started in a layout effect while retaining an older result', async () => {
  useUIStore.setState({ notifications: [], unreadNotificationCount: 0 });
  let backend: BackendState = { generation: 1, phase: 'ready', port: 50001, isReady: true, error: null };
  publishBackendEpoch(1, true);
  const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <BackendContext.Provider value={backend}>{children}</BackendContext.Provider>
  );
  const pending = deferredResult<ReturnType<typeof success<{ result_id: string }>>>();
  let completion!: Promise<void>;
  const { result, rerender } = renderHook(() => {
    const runner = useAnalysisRunner<{ result_id: string }>('Spectrum');
    const { run } = runner;
    const generation = backend.generation;
    React.useLayoutEffect(() => {
      if (generation === 2) completion = run(() => pending.promise, { dt: 2 });
    }, [generation, run]);
    return runner;
  }, { wrapper });
  await act(async () => { await result.current.run(async () => success({ result_id: 'old' }), { dt: 1 }); });
  publishBackendEpoch(2, true);
  backend = { ...backend, generation: 2 };
  rerender();
  expect(result.current.running).toBe(true);
  expect(result.current.resultStatus).toBe('stale');
  await act(async () => { pending.resolve(success({ result_id: 'new' })); await completion; });
  expect(result.current.result).toEqual({ result_id: 'new' });
  expect(result.current.resultInputs).toEqual({ dt: 2 });
  expect(result.current.resultIdentity?.backendGeneration).toBe(2);
  expect(result.current.resultStatus).toBe('current');
});
