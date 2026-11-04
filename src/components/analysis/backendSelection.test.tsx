import { useState } from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { BackendContext } from '@/context/BackendContext';
import type { BackendState } from '@/hooks/useBackendStatus';
import { useEventLists } from '@/hooks/useEventLists';

const listEventLists = vi.fn();
vi.mock('@/api/dataApi', () => ({ dataApi: { listEventLists: (...args: unknown[]) => listEventLists(...args) } }));
import EventListSelector from './EventListSelector';

function Selection({ initial = '' }: { initial?: string }) {
  const [value, setValue] = useState(initial);
  const { data } = useEventLists();
  return <>
    <EventListSelector label="Dataset" value={value} onChange={setValue} />
    <output data-testid="selected">{value}</output>
    <output data-testid="catalog-ids">{data?.map((entry) => entry.dataset_id ?? 'unknown').join(',')}</output>
  </>;
}

function managed(client: QueryClient, generation: number, ready = true, initial = '') {
  const state: BackendState = { generation, phase: ready ? 'ready' : 'starting', isReady: ready, port: ready ? 50017 : null, error: null };
  return (
    <QueryClientProvider client={client}><MemoryRouter><BackendContext.Provider value={state}>
      <Selection initial={initial} />
    </BackendContext.Provider></MemoryRouter></QueryClientProvider>
  );
}

const response = (name: string) => ({ success: true, data: [{ name, n_events: 5 }], message: '', error: null });

beforeEach(() => listEventLists.mockReset());

describe('backend-bound EventList selections', () => {
  it('clears a selected name even when the replacement backend has the same name', async () => {
    listEventLists.mockResolvedValue(response('same_name'));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
    const view = render(managed(client, 1, true, 'same_name'));
    await waitFor(() => expect(screen.getByTestId('catalog-ids')).toHaveTextContent('unknown'));
    expect(screen.getByTestId('selected')).toHaveTextContent('same_name');
    view.rerender(managed(client, 2, true, 'same_name'));
    await waitFor(() => expect(listEventLists).toHaveBeenCalledTimes(2));
    expect(screen.getByTestId('selected')).toBeEmptyDOMElement();
  });

  it('does not allow a late old list to populate the current generation', async () => {
    let resolveOld!: (value: ReturnType<typeof response>) => void;
    const old = new Promise<ReturnType<typeof response>>((resolve) => { resolveOld = resolve; });
    listEventLists.mockReturnValueOnce(old).mockResolvedValue(response('current'));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
    const view = render(managed(client, 1));
    await waitFor(() => expect(listEventLists).toHaveBeenCalledOnce());
    view.rerender(managed(client, 2));
    await screen.findByLabelText('Dataset');
    await act(async () => { resolveOld(response('obsolete')); await old; });
    const current = client.getQueriesData({ queryKey: ['eventLists', 2] });
    expect(current).toHaveLength(1);
    expect(current[0][1]).toEqual([{ name: 'current', n_events: 5 }]);
    expect(screen.queryByText(/obsolete/)).not.toBeInTheDocument();
  });

  it('does not fetch or retain a selection while the backend is unavailable', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(managed(client, 1, false, 'old'));
    expect(await screen.findByText(/Waiting for the backend/)).toBeInTheDocument();
    expect(listEventLists).not.toHaveBeenCalled();
    expect(screen.getByTestId('selected')).toBeEmptyDOMElement();
  });

  it('clears a selected name when its dataset identity changes within the same generation', async () => {
    const catalog = (id: string) => ({
      success: true, data: [{ name: 'same_name', dataset_id: id, n_events: 5 }],
      message: '', error: null,
    });
    listEventLists.mockResolvedValue(catalog('original-dataset'));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
    render(managed(client, 1, true, 'same_name'));
    await waitFor(() => expect(screen.getByTestId('catalog-ids')).toHaveTextContent('original-dataset'));
    expect(screen.getByTestId('selected')).toHaveTextContent('same_name');

    listEventLists.mockResolvedValue(catalog('replacement-dataset'));
    await act(async () => { await client.invalidateQueries({ queryKey: ['eventLists'] }); });
    await waitFor(() => expect(screen.getByTestId('selected')).toBeEmptyDOMElement());

    // The replacement is usable after an explicit new selection; it must not
    // inherit the original selection or immediately clear itself again.
    await userEvent.click(screen.getByLabelText('Dataset'));
    await userEvent.click(screen.getByRole('option', { name: /same_name/ }));
    expect(screen.getByTestId('selected')).toHaveTextContent('same_name');
    await act(async () => { await client.invalidateQueries({ queryKey: ['eventLists'] }); });
    expect(screen.getByTestId('selected')).toHaveTextContent('same_name');
  });

  it('does not confuse a deliberate selection of a different dataset with replacement', async () => {
    listEventLists.mockResolvedValue({ success: true, data: [
      { name: 'first', dataset_id: 'first-id', n_events: 5 },
      { name: 'second', dataset_id: 'second-id', n_events: 8 },
    ] });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
    render(managed(client, 1, true, 'first'));
    await userEvent.click(await screen.findByLabelText('Dataset'));
    await userEvent.click(screen.getByRole('option', { name: /second/ }));
    await act(async () => { await client.invalidateQueries({ queryKey: ['eventLists'] }); });
    expect(screen.getByTestId('selected')).toHaveTextContent('second');
  });

  it('keeps legacy selections without IDs but clears an identity that becomes unverifiable', async () => {
    listEventLists.mockResolvedValue(response('legacy'));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
    render(managed(client, 1, true, 'legacy'));
    await screen.findByLabelText('Dataset');
    await act(async () => { await client.invalidateQueries({ queryKey: ['eventLists'] }); });
    expect(screen.getByTestId('selected')).toHaveTextContent('legacy');
    listEventLists.mockResolvedValue({ success: true, data: [{ name: 'legacy', dataset_id: 'known-id', n_events: 5 }] });
    await act(async () => { await client.invalidateQueries({ queryKey: ['eventLists'] }); });
    await waitFor(() => expect(screen.getByTestId('catalog-ids')).toHaveTextContent('known-id'));
    expect(screen.getByTestId('selected')).toHaveTextContent('legacy');
    listEventLists.mockResolvedValue(response('legacy'));
    await act(async () => { await client.invalidateQueries({ queryKey: ['eventLists'] }); });
    await waitFor(() => expect(screen.getByTestId('selected')).toBeEmptyDOMElement());
  });

  it('pins the visible dataset when selecting during a background refresh', async () => {
    const identified = (id: string) => ({ success: true, data: [{ name: 'same_name', dataset_id: id, n_events: 5 }] });
    let resolveReplacement!: (value: ReturnType<typeof identified>) => void;
    const replacement = new Promise<ReturnType<typeof identified>>((resolve) => { resolveReplacement = resolve; });
    listEventLists.mockResolvedValueOnce(identified('visible-old-id')).mockReturnValueOnce(replacement);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
    render(managed(client, 1));
    await waitFor(() => expect(screen.getByTestId('catalog-ids')).toHaveTextContent('visible-old-id'));
    let refresh!: Promise<void>;
    act(() => { refresh = client.invalidateQueries({ queryKey: ['eventLists'] }); });
    await waitFor(() => expect(listEventLists).toHaveBeenCalledTimes(2));
    await userEvent.click(screen.getByLabelText('Dataset'));
    await userEvent.click(screen.getByRole('option', { name: /same_name/ }));
    expect(screen.getByTestId('selected')).toHaveTextContent('same_name');
    await act(async () => { resolveReplacement(identified('replacement-id')); await refresh; });
    await waitFor(() => expect(screen.getByTestId('selected')).toBeEmptyDOMElement());
  });
});
