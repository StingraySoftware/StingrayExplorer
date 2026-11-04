import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BackendContext } from '@/context/BackendContext';
import type { BackendState } from '@/hooks/useBackendStatus';

const { createPowerSpectrum, rebinSpectrum, listSpectra, chartProps } = vi.hoisted(() => ({
  createPowerSpectrum: vi.fn(), rebinSpectrum: vi.fn(), listSpectra: vi.fn(), chartProps: vi.fn(),
}));
vi.mock('@/api/dataApi', () => ({ dataApi: { listEventLists: async () => ({
  success: true, data: [{ name: 'obs1', n_events: 1000 }, { name: 'obs2', n_events: 2000 }],
}) } }));
vi.mock('@/api/spectrumApi', () => ({ spectrumApi: { createPowerSpectrum, rebinSpectrum, listSpectra } }));
vi.mock('@/components/plots/PlotlyChart', () => ({ default: (props: unknown) => {
  chartProps(props); return <div data-testid="spectrum-chart" />;
} }));
import PowerSpectrumPage from './index';

const firstId = '11111111-1111-4111-8111-111111111111';
const secondId = '22222222-2222-4222-8222-222222222222';
const ready = (generation = 1): BackendState => ({
  generation, phase: 'ready', port: 54321, isReady: true, error: null,
});
const original = {
  name: 'saved_psd', result_id: firstId, backend_session_id: 'backend-1',
  freq: [1, 2], power: [5, 7], power_phase: null, n_freq: 2, norm: 'leahy', df: 1,
  inputs: [{ name: 'obs1', dataset_id: 'events-1' }], parameters: { dt: 0.0625, norm: 'leahy' },
};
let catalog: Array<{ name: string; result_id: string; type: string; n_freq: number }>;

function renderPage(backend = ready()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  const page = (value: BackendState) => (
    <QueryClientProvider client={client}><MemoryRouter>
      <BackendContext.Provider value={value}><PowerSpectrumPage /></BackendContext.Provider>
    </MemoryRouter></QueryClientProvider>
  );
  const view = render(page(backend));
  return { ...view, client, setBackend: (value: BackendState) => view.rerender(page(value)) };
}

async function computeStored() {
  await userEvent.click(await screen.findByLabelText('Event list'));
  await userEvent.click(await screen.findByRole('option', { name: /obs1/ }));
  await userEvent.type(screen.getByLabelText('Store as (optional)'), 'saved_psd');
  await userEvent.click(screen.getByRole('button', { name: 'Compute' }));
  await screen.findByTestId('spectrum-chart');
  await waitFor(() => expect(screen.getByRole('button', { name: 'Rebin' })).toBeEnabled());
}

describe('PowerSpectrum result identity', () => {
  beforeEach(() => {
    catalog = [];
    chartProps.mockClear(); createPowerSpectrum.mockReset(); rebinSpectrum.mockReset(); listSpectra.mockReset();
    createPowerSpectrum.mockImplementation(async () => {
      catalog = [{ name: original.name, result_id: firstId, type: 'Powerspectrum', n_freq: 2 }];
      return { success: true, data: original, message: 'computed', error: null };
    });
    listSpectra.mockImplementation(async () => ({ success: true, data: catalog, message: '', error: null }));
    rebinSpectrum.mockImplementation(async (params) => {
      const data = { ...original, name: params.output_name, result_id: secondId, freq: [1.5], power: [6], n_freq: 1, df: 2 };
      catalog = [...catalog, { name: data.name, result_id: secondId, type: 'Powerspectrum', n_freq: 1 }];
      return { success: true, data, message: 'rebinned', error: null };
    });
  });

  it('retains original inputs and normalization after edits and a failed rerun', async () => {
    renderPage();
    await computeStored();
    await userEvent.click(screen.getByLabelText('Normalization'));
    await userEvent.click(screen.getByRole('option', { name: 'frac' }));
    expect(screen.getByText('Inputs have changed since this result.')).toBeInTheDocument();
    expect(screen.getByText('norm: leahy')).toBeInTheDocument();
    const panel = screen.getByRole('region', { name: 'Result identity' });
    await userEvent.click(within(panel).getByRole('button', { name: 'Original calculation inputs' }));
    expect(within(panel).getByText('leahy')).toBeVisible();
    createPowerSpectrum.mockResolvedValueOnce({ success: false, data: null, message: 'Calculation rejected', error: null });
    await userEvent.click(screen.getByRole('button', { name: 'Compute' }));
    expect(await screen.findByText(/The latest request failed/)).toBeInTheDocument();
    expect(within(panel).getByText('Result ID: ' + firstId)).toBeInTheDocument();
    expect(screen.getByText('norm: leahy')).toBeInTheDocument();
  });

  it('stores each rebinned derivative and uses the displayed source identity', async () => {
    renderPage();
    await computeStored();
    await userEvent.clear(screen.getByLabelText('Store rebinned as'));
    await userEvent.type(screen.getByLabelText('Store rebinned as'), 'rebinned_psd');
    await userEvent.click(screen.getByRole('button', { name: 'Rebin' }));
    await waitFor(() => expect(rebinSpectrum).toHaveBeenCalledWith({
      name: 'saved_psd', expected_result_id: firstId, rebin_factor: 0.02, log: true, output_name: 'rebinned_psd',
    }));
    expect(await screen.findByText('Stored result: rebinned_psd')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Rebin' })).toBeEnabled());
    await userEvent.click(screen.getByRole('button', { name: 'Rebin' }));
    await waitFor(() => expect(rebinSpectrum.mock.calls[1][0]).toMatchObject({ name: 'rebinned_psd', expected_result_id: secondId }));
  });

  it('keeps the plot read-only after a same-port backend restart', async () => {
    const view = renderPage();
    await computeStored();
    view.setBackend({ generation: 2, phase: 'starting', port: null, isReady: false, error: null });
    expect(await screen.findByText(/previous backend session and is read-only/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Rebin' })).toBeDisabled();
    view.setBackend(ready(2));
    expect(screen.getByRole('button', { name: 'Rebin' })).toBeDisabled();
    expect(screen.getByTestId('spectrum-chart')).toBeInTheDocument();
    expect(rebinSpectrum).not.toHaveBeenCalled();
  });

  it.each([
    { label: 'per-bin widths', df: [0.5, 1.5] },
    { label: 'no scalar width', df: undefined },
  ])('renders a logarithmic rebin with $label without scalar formatting', async ({ df }) => {
    rebinSpectrum.mockImplementationOnce(async (params) => {
      const data = { ...original, name: params.output_name, result_id: secondId, df };
      catalog = [...catalog, { name: data.name, result_id: secondId, type: 'Powerspectrum', n_freq: 2 }];
      return { success: true, data, message: 'rebinned', error: null };
    });
    renderPage();
    await computeStored();
    await userEvent.click(screen.getByRole('button', { name: 'Rebin' }));
    expect(await screen.findByText('Variable frequency bin widths')).toBeInTheDocument();
    expect(screen.getByTestId('spectrum-chart')).toBeInTheDocument();
  });

  it('refuses follow-up operations after the stored name is reused for another result', async () => {
    const view = renderPage();
    await computeStored();
    catalog = [{ name: original.name, result_id: secondId, type: 'Powerspectrum', n_freq: 2 }];
    await act(async () => { await view.client.invalidateQueries({ queryKey: ['spectra'] }); });
    expect(await screen.findByText(/stored spectrum was deleted or replaced/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Rebin' })).toBeDisabled();
    expect(rebinSpectrum).not.toHaveBeenCalled();
  });
});

it('reopens the selected input, unsent edits and axes without relabelling the saved spectrum', async () => {
  const { publishBackendEpoch } = await import('@/api/backendEpoch');
  const { workspaceSession, restoreWorkspaceSession } = await import('@/api/workspaceSession');
  const { savedAnalyses, restoreAnalyses } = await import('@/api/projectResults');
  publishBackendEpoch(1, true);
  catalog = [];
  createPowerSpectrum.mockResolvedValue({ success: true, data: original, message: '', error: null });
  listSpectra.mockImplementation(async () => ({ success: true, data: [{ name: original.name, result_id: firstId }], message: '', error: null }));
  const view = renderPage();
  await computeStored();
  const dt = screen.getByLabelText(/Time bin/);
  await userEvent.clear(dt);
  await userEvent.type(dt, '0.125');
  await userEvent.click(screen.getByLabelText('log f'));
  const rebinName = screen.getByLabelText('Store rebinned as');
  await userEvent.clear(rebinName);
  await userEvent.type(rebinName, 'unsent_derived');
  const workspace = workspaceSession(), renderer = savedAnalyses();
  view.unmount();
  restoreWorkspaceSession();
  restoreAnalyses(renderer);
  restoreWorkspaceSession(workspace);
  renderPage();
  expect(await screen.findByTestId('spectrum-chart')).toBeInTheDocument();
  expect(screen.getByLabelText(/Time bin/)).toHaveValue('0.125');
  expect(screen.getByLabelText('log f')).not.toBeChecked();
  expect(screen.getByLabelText('Store rebinned as')).toHaveValue('unsent_derived');
  expect(screen.getByText('norm: leahy')).toBeInTheDocument();
  expect(screen.getByText('Inputs have changed since this result.')).toBeInTheDocument();
  restoreAnalyses({});
  publishBackendEpoch(null, true);
});
