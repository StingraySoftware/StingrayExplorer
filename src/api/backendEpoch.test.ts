import { afterEach, describe, expect, it, vi } from 'vitest';
import { waitFor } from '@testing-library/react';
import { apiClient } from './client';
import { captureBackendEpoch, isBackendEpochCurrent, publishBackendEpoch } from './backendEpoch';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((complete) => { resolve = complete; });
  return { promise, resolve };
}

afterEach(() => {
  publishBackendEpoch(null, true);
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('managed backend request lifetime', () => {
  it('invalidates an old request even when loss and recovery share a generation', () => {
    publishBackendEpoch(1, true);
    const before = captureBackendEpoch();
    publishBackendEpoch(1, false);
    publishBackendEpoch(1, true);
    expect(isBackendEpochCurrent(before)).toBe(false);
    expect(isBackendEpochCurrent(captureBackendEpoch())).toBe(true);
  });

  it('discards a response from a replaced backend even when its URL is reused', async () => {
    publishBackendEpoch(1, true);
    const oldResponse = deferred<Response>();
    const fetchMock = vi.fn().mockReturnValue(oldResponse.promise);
    vi.stubGlobal('fetch', fetchMock);
    const request = apiClient.get('/api/spectrum/');
    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());

    publishBackendEpoch(2, true);
    oldResponse.resolve(new Response(JSON.stringify({ success: true, data: [{ name: 'old' }] })));
    const result = await request;
    expect(result.success).toBe(false);
    expect(result.data).toBeNull();
    expect(result.error).toBe('backend_session_changed');
  });

  it('checks the epoch again after asynchronous JSON decoding', async () => {
    publishBackendEpoch(3, true);
    const body = deferred<unknown>();
    const decode = vi.fn().mockReturnValue(body.promise);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: decode }));
    const request = apiClient.get('/api/data/event-lists');
    await waitFor(() => expect(decode).toHaveBeenCalledOnce());

    publishBackendEpoch(3, false);
    publishBackendEpoch(3, true);
    body.resolve({ success: true, data: [{ name: 'old' }] });
    expect((await request).error).toBe('backend_session_changed');
  });

  it('does not dispatch new requests while the managed backend is unavailable', async () => {
    publishBackendEpoch(4, false);
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const result = await apiClient.post('/api/utilities/io/export', {});
    expect(result.error).toBe('backend_unavailable');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('does not treat an unchanged readiness announcement as a new process', () => {
    publishBackendEpoch(5, true);
    const before = captureBackendEpoch();
    publishBackendEpoch(5, true);
    expect(isBackendEpochCurrent(before)).toBe(true);
  });

  it('discards and closes an obsolete event stream without yielding its events', async () => {
    publishBackendEpoch(6, true);
    let streamController!: ReadableStreamDefaultController<Uint8Array>;
    const cancelled = vi.fn();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      body: new ReadableStream<Uint8Array>({
        start(controller) { streamController = controller; },
        cancel: cancelled,
      }),
    }));
    const iterator = apiClient.stream('/api/jobs/stream');
    const next = iterator.next();
    await waitFor(() => expect(streamController).toBeDefined());
    publishBackendEpoch(7, true);
    streamController.enqueue(new TextEncoder().encode('data: {"type":"old"}\n\n'));
    expect(await next).toEqual({ done: true, value: undefined });
    expect(cancelled).toHaveBeenCalledOnce();
  });
});
