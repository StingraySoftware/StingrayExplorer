import React from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { BackendContext } from '@/context/BackendContext';
import { publishBackendEpoch } from '@/api/backendEpoch';
import { jobApi } from '@/api/jobApi';
import { useJobStore } from '@/store/jobStore';
import { useUIStore } from '@/store/uiStore';
import type { BackendState } from './useBackendStatus';
import type { Job, JobStreamEvent } from '@/types/job';
import { useJobStream } from './useJobStream';

function eventStream() {
  const queue: Array<JobStreamEvent | null> = [];
  let resume: ((event: JobStreamEvent | null) => void) | null = null;
  return {
    push(event: JobStreamEvent | null) {
      if (resume) { const complete = resume; resume = null; complete(event); }
      else queue.push(event);
    },
    async *events(): AsyncGenerator<JobStreamEvent> {
      while (true) {
        const event = queue.length ? queue.shift()! : await new Promise<JobStreamEvent | null>((resolve) => { resume = resolve; });
        if (event === null) return;
        yield event;
      }
    },
  };
}

function job(id: string, status: Job['status']): Job {
  return { id, status, type: 'load_event_list', progress: 1, progress_message: '', total_items: 1, completed_items: 1,
    created_at: '2026-10-29T00:00:00Z', started_at: null, completed_at: null, result: null, error: null, display_name: id };
}

afterEach(() => {
  publishBackendEpoch(null, true);
  vi.restoreAllMocks();
  useJobStore.setState({ jobs: {}, isConnected: false, connectionError: null, reconnectAttempts: 0 });
  useUIStore.setState({ notifications: [], unreadNotificationCount: 0 });
});

describe('job streams across backend generations', () => {
  it('reconnects on same-port restart and ignores late events from the old stream', async () => {
    const streams: ReturnType<typeof eventStream>[] = [];
    vi.spyOn(jobApi, 'streamJobUpdates').mockImplementation(() => {
      const stream = eventStream(); streams.push(stream); return stream.events();
    });
    useJobStore.setState({ jobs: {}, reconnectAttempts: 0 });
    useUIStore.setState({ notifications: [], unreadNotificationCount: 0 });
    publishBackendEpoch(1, true);
    let backend: BackendState = { generation: 1, phase: 'ready', port: 50017, isReady: true, error: null };
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const Wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={client}><BackendContext.Provider value={backend}>{children}</BackendContext.Provider></QueryClientProvider>
    );
    const view = renderHook(() => useJobStream(), { wrapper: Wrapper });
    await waitFor(() => expect(streams).toHaveLength(1));
    await act(async () => { streams[0].push({ type: 'job_created', timestamp: '2026-10-29T00:00:00Z', job: job('old', 'pending') }); });
    await waitFor(() => expect(useJobStore.getState().jobs.old).toBeDefined());

    publishBackendEpoch(2, true);
    backend = { ...backend, generation: 2 };
    view.rerender();
    await waitFor(() => expect(streams).toHaveLength(2));
    expect(useJobStore.getState().jobs).toEqual({});
    await act(async () => { streams[0].push({ type: 'job_completed', timestamp: '2026-10-29T00:00:00Z', job: job('old', 'completed') }); });
    expect(useJobStore.getState().jobs).toEqual({});
    expect(useUIStore.getState().notifications).toHaveLength(0);

    await act(async () => { streams[1].push({ type: 'job_completed', timestamp: '2026-10-29T00:00:00Z', job: job('new', 'completed') }); });
    await waitFor(() => expect(useJobStore.getState().jobs.new?.status).toBe('completed'));
    expect(useUIStore.getState().notifications).toHaveLength(1);
    expect(streams).toHaveLength(2);
    view.unmount();
    streams.forEach((stream) => stream.push(null));
  });
});
