import { useCallback, useEffect, useInsertionEffect, useRef, useState } from 'react';
import { rememberAnalysis, forgetAnalysis, restoredAnalysis, onProjectRestored } from '@/api/projectResults';
import { ApiResponse } from '@/api/client';
import { captureBackendEpoch, isBackendEpochCurrent } from '@/api/backendEpoch';
import { useBackendContext } from '@/context/BackendContext';
import { useUIStore } from '@/store/uiStore';

export type AnalysisResultStatus = 'empty' | 'current' | 'previous' | 'stale';

export interface AnalysisResultIdentity {
  resultId: string | null;
  backendGeneration: number | null;
  backendSessionId: string | null;
  completedAt: string;
}

interface AnalysisRunnerState<T> {
  result: T | null;
  resultInputs: Readonly<Record<string, unknown>> | null;
  resultIdentity: Readonly<AnalysisResultIdentity> | null;
  resultEpoch: ReturnType<typeof captureBackendEpoch> | null;
  running: boolean;
  error: string | null;
  warnings: string[];
  previous: boolean;
  stale: boolean;
}

function emptyState<T>(): AnalysisRunnerState<T> {
  return {
    result: null,
    resultInputs: null,
    resultIdentity: null,
    resultEpoch: null,
    running: false,
    error: null,
    warnings: [],
    previous: false,
    stale: false,
  };
}

function dataWarnings(value: unknown): string[] {
  if (typeof value !== 'object' || value === null || !('warnings' in value)) return [];
  const warnings = (value as { warnings?: unknown }).warnings;
  return Array.isArray(warnings)
    ? warnings.filter((warning): warning is string => typeof warning === 'string')
    : [];
}

function freezeSnapshot<T>(value: T): T {
  if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
    for (const child of Object.values(value)) freezeSnapshot(child);
    Object.freeze(value);
  }
  return value;
}

function originalInputs(inputs?: Record<string, unknown>): Readonly<Record<string, unknown>> | null {
  return inputs === undefined ? null : freezeSnapshot(structuredClone(inputs));
}

function resultField(value: unknown, key: string): string | null {
  if (value === null || typeof value !== 'object') return null;
  const record = value as Record<string, unknown>;
  if (typeof record[key] === 'string') return record[key];
  for (const nested of ['identity', 'provenance']) {
    const block = record[nested];
    if (block !== null && typeof block === 'object' &&
        typeof (block as Record<string, unknown>)[key] === 'string') {
      return (block as Record<string, string>)[key];
    }
  }
  return null;
}

function provenanceInputs(value: unknown): Readonly<Record<string, unknown>> | null {
  if (value === null || typeof value !== 'object' || !('provenance' in value)) return null;
  const provenance = (value as { provenance: unknown }).provenance;
  return provenance !== null && typeof provenance === 'object' && !Array.isArray(provenance)
    ? originalInputs(provenance as Record<string, unknown>)
    : null;
}

/** Keep each successful result attached to the inputs and backend that created it. */
export function useAnalysisRunner<T>(label: string) {
  const addNotification = useUIStore((s) => s.addNotification);
  const backend = useBackendContext();
  const latestBackend = useRef(backend);
  useInsertionEffect(() => {
    latestBackend.current = backend;
  });
  const sequence = useRef(0);
  const mounted = useRef(true);
  const inFlight = useRef<{
    generation: number;
    epoch: ReturnType<typeof captureBackendEpoch>;
  } | null>(null);
  const currentEpoch = captureBackendEpoch();
  const loadProjectResult = (): AnalysisRunnerState<T> => {
    const saved = restoredAnalysis(label);
    return saved ? { ...emptyState<T>(), ...saved, result: saved.result as T,
      resultEpoch: captureBackendEpoch() } : emptyState<T>();
  };
  const [state, setState] = useState<AnalysisRunnerState<T>>(loadProjectResult);
  useEffect(() => onProjectRestored(() => {
    sequence.current += 1;
    inFlight.current = null;
    setState(loadProjectResult());
  // Project restoration is an explicit workspace operation.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [label]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      sequence.current += 1;
      inFlight.current = null;
    };
  }, []);

  useEffect(() => {
    const currentBackend = latestBackend.current;
    if (currentBackend.generation === null) return;
    const invalidRequest = inFlight.current !== null && (
      !currentBackend.isReady ||
      inFlight.current.generation !== currentBackend.generation ||
      !isBackendEpochCurrent(inFlight.current.epoch)
    );
    if (invalidRequest) {
      sequence.current += 1;
      inFlight.current = null;
    }
    setState((current) => {
      // A caller may already have started valid new-generation work in a
      // layout effect. Mark the previous result stale without cancelling it.
      const invalidResult = current.result !== null && (
        !currentBackend.isReady ||
        current.resultIdentity?.backendGeneration !== currentBackend.generation ||
        (current.resultEpoch !== null && !isBackendEpochCurrent(current.resultEpoch))
      );
      if (!invalidRequest && (!invalidResult || current.stale)) return current;
      return {
        ...current,
        running: invalidRequest ? false : current.running,
        error: invalidRequest ? null : current.error,
        stale: current.stale || invalidResult,
      };
    });
  }, [backend.generation, backend.isReady, currentEpoch.version, state.resultIdentity]);

  const run = useCallback(async (
    call: () => Promise<ApiResponse<T>>,
    inputs?: Record<string, unknown>
  ): Promise<void> => {
    const request = ++sequence.current;
    const source = latestBackend.current;
    const epoch = captureBackendEpoch();
    const managed = source.generation !== null;
    const available = !managed || (source.isReady && epoch.isReady &&
      (epoch.generation === null || epoch.generation === source.generation));
    if (!available) {
      inFlight.current = null;
      setState((current) => ({
        ...current,
        running: false,
        error: 'The backend is not ready. Wait for it to reconnect before running an analysis.',
        previous: current.result !== null,
      }));
      return;
    }
    inFlight.current = managed && source.generation !== null
      ? { generation: source.generation, epoch }
      : null;
    const isCurrent = (): boolean => {
      const current = latestBackend.current;
      return mounted.current && request === sequence.current &&
        (!managed || (current.isReady && current.generation === source.generation &&
          isBackendEpochCurrent(epoch)));
    };
    setState((current) => ({ ...current, running: true, error: null, warnings: [] }));
    try {
      // Snapshot before calling user code: nested arrays may otherwise be
      // edited while the backend is still computing this request.
      const submittedInputs = originalInputs(inputs);
      const response = await call();
      if (!isCurrent()) return;
      inFlight.current = null;
      if (response.success && response.data != null) {
        // Own the response snapshot as well: callers may reuse a response
        // object, but that must not rewrite a displayed result's provenance.
        // Numerical arrays remain unfrozen for plotting libraries.
        const acceptedData = structuredClone(response.data);
        const embeddedWarnings = dataWarnings(acceptedData);
        const identity = Object.freeze({
          resultId: resultField(acceptedData, 'result_id') ?? crypto.randomUUID(),
          backendGeneration: source.generation,
          backendSessionId: resultField(acceptedData, 'backend_session_id'),
          completedAt: resultField(acceptedData, 'created_at') ?? new Date().toISOString(),
        });
        rememberAnalysis(label, {
          result: acceptedData, resultInputs: submittedInputs ?? provenanceInputs(acceptedData),
          resultIdentity: identity, warnings: response.warnings ?? [], stale: false,
        });
        setState({
          result: acceptedData,
          resultInputs: submittedInputs ?? provenanceInputs(acceptedData),
          resultIdentity: identity,
          resultEpoch: epoch,
          running: false,
          error: null,
          previous: false,
          stale: false,
          warnings: (response.warnings ?? []).filter((warning) => !embeddedWarnings.includes(warning)),
        });
        addNotification({ type: 'success', title: label, message: response.message || 'Done' });
      } else {
        const message = response.error || response.message || 'Operation failed';
        setState((current) => ({
          ...current,
          running: false,
          error: message,
          previous: current.result !== null,
          warnings: response.warnings ?? [],
        }));
        addNotification({ type: 'error', title: label, message });
      }
    } catch (error) {
      if (!isCurrent()) return;
      inFlight.current = null;
      const message = error instanceof Error ? error.message : String(error);
      setState((current) => ({
        ...current,
        running: false,
        error: message,
        warnings: [],
        previous: current.result !== null,
      }));
      addNotification({ type: 'error', title: label, message });
    }
  }, [label, addNotification]);

  const reset = useCallback((): void => {
    sequence.current += 1;
    inFlight.current = null;
    forgetAnalysis(label);
    setState(emptyState<T>());
  }, [label]);

  const epoch = captureBackendEpoch();
  const backendAvailable = backend.generation === null || (backend.isReady && epoch.isReady &&
    (epoch.generation === null || epoch.generation === backend.generation));
  const resultStale = state.result !== null && (state.stale ||
    (state.resultIdentity?.backendGeneration !== null &&
      (!backend.isReady || state.resultIdentity?.backendGeneration !== backend.generation ||
        (state.resultEpoch !== null && !isBackendEpochCurrent(state.resultEpoch)))));
  const resultStatus: AnalysisResultStatus = state.result === null ? 'empty'
    : resultStale ? 'stale' : state.previous ? 'previous' : 'current';

  return {
    result: state.result,
    resultInputs: state.resultInputs,
    resultIdentity: state.resultIdentity,
    resultStatus,
    resultStale,
    stale: resultStale,
    backendAvailable,
    running: state.running,
    error: state.error,
    warnings: state.warnings,
    run,
    reset,
  };
}
