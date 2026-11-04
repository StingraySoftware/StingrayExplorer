import { act, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { BackendStatusProvider, useBackendContext } from './BackendContext';
import { captureBackendEpoch, publishBackendEpoch } from '@/api/backendEpoch';
import type { BackendStatus, BackendStatusSource } from '@/types/backendStatus';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((yes) => { resolve = yes; });
  return { promise, resolve };
}

class Source implements BackendStatusSource {
  snapshot: BackendStatus = { revision: 1, generation: 1, phase: 'ready', port: 50001, error: null };
  listeners = new Set<(status: BackendStatus) => void>();
  getBackendStatus = async () => this.snapshot;
  onBackendStatus = (callback: (status: BackendStatus) => void) => {
    this.listeners.add(callback);
    return () => { this.listeners.delete(callback); };
  };
  emit(status: BackendStatus) {
    this.snapshot = status;
    for (const callback of this.listeners) callback(status);
  }
}

function Consumer({ query }: { query: () => Promise<string[]> }) {
  const backend = useBackendContext();
  const objects = useQuery({
    // A static key deliberately exercises the cache lifetime independently of
    // callers which additionally namespace their queries by generation.
    queryKey: ['scientific-objects'],
    queryFn: query,
    enabled: backend.isReady,
    retry: false,
  });
  return <span>{backend.generation}:{objects.data?.join(',') ?? 'loading'}</span>;
}

function setup(source: Source, query: () => Promise<string[]>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(
    <QueryClientProvider client={client}>
      <BackendStatusProvider source={source}>
        <Consumer query={query} />
      </BackendStatusProvider>
    </QueryClientProvider>
  );
  return client;
}

beforeEach(() => publishBackendEpoch(null, true));

describe('managed backend query lifetime', () => {
  it('clears old objects before same-port replacement and refetches on the new generation', async () => {
    const source = new Source();
    const fresh = deferred<string[]>();
    const query = vi.fn().mockResolvedValueOnce(['old-object']).mockImplementationOnce(() => fresh.promise);
    const client = setup(source, query);
    expect(await screen.findByText('1:old-object')).toBeInTheDocument();

    act(() => {
      source.emit({ revision: 5, generation: 2, phase: 'ready', port: 50001, error: null });
      expect(client.getQueryData(['scientific-objects'])).toBeUndefined();
      expect(captureBackendEpoch().generation).toBe(2);
    });
    expect(screen.queryByText('1:old-object')).not.toBeInTheDocument();
    expect(await screen.findByText('2:loading')).toBeInTheDocument();
    await waitFor(() => expect(query).toHaveBeenCalledTimes(2));
    await act(async () => { fresh.resolve(['new-object']); await fresh.promise; });
    expect(await screen.findByText('2:new-object')).toBeInTheDocument();
  });

  it('discards a late old-generation query even when it ignores AbortSignal', async () => {
    const source = new Source();
    const abandoned = deferred<string[]>();
    const fresh = deferred<string[]>();
    const query = vi.fn().mockImplementationOnce(() => abandoned.promise).mockImplementationOnce(() => fresh.promise);
    const client = setup(source, query);
    await waitFor(() => expect(query).toHaveBeenCalledTimes(1));
    act(() => source.emit({ revision: 4, generation: 2, phase: 'ready', port: 50001, error: null }));
    await waitFor(() => expect(query).toHaveBeenCalledTimes(2));
    await act(async () => { fresh.resolve(['new-object']); await fresh.promise; });
    expect(await screen.findByText('2:new-object')).toBeInTheDocument();
    await act(async () => { abandoned.resolve(['old-object']); await abandoned.promise; });
    expect(client.getQueryData(['scientific-objects'])).toEqual(['new-object']);
    expect(screen.queryByText(/old-object/)).not.toBeInTheDocument();
  });

  it('clears loaded objects on an unexpected exit and stays empty until ready', async () => {
    const source = new Source();
    const query = vi.fn().mockResolvedValueOnce(['old-object']).mockResolvedValueOnce([]);
    const client = setup(source, query);
    await screen.findByText('1:old-object');
    act(() => source.emit({ revision: 2, generation: 1, phase: 'error', port: null, error: 'Exited' }));
    expect(client.getQueryData(['scientific-objects'])).toBeUndefined();
    expect(screen.queryByText(/old-object/)).not.toBeInTheDocument();
    expect(query).toHaveBeenCalledTimes(1);
    act(() => source.emit({ revision: 3, generation: 2, phase: 'ready', port: 50001, error: null }));
    await waitFor(() => expect(query).toHaveBeenCalledTimes(2));
    expect(screen.queryByText(/old-object/)).not.toBeInTheDocument();
  });
});

it('notifies mounted query observers that do not consume backend context', async () => {
  const source = new Source();
  const fresh = deferred<string[]>();
  const query = vi.fn().mockResolvedValueOnce(['old-object']).mockImplementation(() => fresh.promise);
  function IndependentQueryConsumer() {
    const objects = useQuery({ queryKey: ['independent-objects'], queryFn: query, retry: false });
    return <span>{objects.data?.join(',') ?? 'independent-loading'}</span>;
  }
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(
    <QueryClientProvider client={client}>
      <BackendStatusProvider source={source}><IndependentQueryConsumer /></BackendStatusProvider>
    </QueryClientProvider>
  );
  await screen.findByText('old-object');
  act(() => source.emit({ revision: 2, generation: 2, phase: 'starting', port: null, error: null }));
  await waitFor(() => expect(screen.queryByText('old-object')).not.toBeInTheDocument());
  act(() => source.emit({ revision: 3, generation: 2, phase: 'ready', port: 50001, error: null }));
  await act(async () => { fresh.resolve(['new-object']); await fresh.promise; });
  expect(await screen.findByText('new-object')).toBeInTheDocument();
  expect(client.getQueryData(['independent-objects'])).toEqual(['new-object']);
});
