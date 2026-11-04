import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/testUtils';
import { useUIStore } from '@/store/uiStore';
import { BackendContext } from '@/context/BackendContext';
import type { BackendState } from '@/hooks/useBackendStatus';

const listEventLists = vi.fn();
vi.mock('@/api/dataApi', () => ({
  dataApi: { listEventLists: (...a: unknown[]) => listEventLists(...a) },
}));

const createFromEventList = vi.fn();
const listLightcurves = vi.fn();
const getLightcurveData = vi.fn();
const rebin = vi.fn();
const deleteLightcurve = vi.fn();
vi.mock('@/api/lightcurveApi', () => ({
  lightcurveApi: {
    createFromEventList: (...a: unknown[]) => createFromEventList(...a),
    listLightcurves: (...a: unknown[]) => listLightcurves(...a),
    getLightcurveData: (...a: unknown[]) => getLightcurveData(...a),
    rebin: (...a: unknown[]) => rebin(...a),
    deleteLightcurve: (...a: unknown[]) => deleteLightcurve(...a),
  },
}));
vi.mock('@/components/plots/PlotlyChart', () => ({
  default: () => <div data-testid="chart" />,
}));

import LightCurvePage from './index';

describe('LightCurvePage', () => {
  beforeEach(() => {
    useUIStore.setState({ notifications: [], unreadNotificationCount: 0 });
    listEventLists.mockResolvedValue({
      success: true,
      data: [{ name: 'obs1', n_events: 5000, time_range: [0, 100] }],
      message: '',
      error: null,
    });
    listLightcurves.mockResolvedValue({ success: true, data: [], message: '', error: null });
    createFromEventList.mockResolvedValue({
      success: true,
      data: {
        name: 'obs1_lc',
        time: [0.5, 1.5, 2.5],
        counts: [10, 12, 9],
        dt: 1,
        n_bins: 3,
        plot_stride: 1,
        count_rate_mean: 10.3,
      },
      message: 'created',
      error: null,
    });
  });

  it('creates a light curve with parsed parameters and plots it', async () => {
    renderWithProviders(<LightCurvePage />);
    await userEvent.click(await screen.findByLabelText('Event list'));
    await userEvent.click(await screen.findByText(/obs1/));
    const dtField = screen.getByLabelText(/Time bin/);
    await userEvent.clear(dtField);
    await userEvent.type(dtField, '1.0');
    await userEvent.click(screen.getByRole('button', { name: /Generate/ }));
    await waitFor(() =>
      expect(createFromEventList).toHaveBeenCalledWith(
        expect.objectContaining({ event_list_name: 'obs1', dt: 1, output_name: 'obs1_lc' })
      )
    );
    expect(await screen.findByTestId('chart')).toBeInTheDocument();
  });

  it('disables Generate until inputs are valid', async () => {
    renderWithProviders(<LightCurvePage />);
    const button = await screen.findByRole('button', { name: /Generate/ });
    expect(button).toBeDisabled();
  });

  it('retains a deleted curve as a read-only snapshot and disables rebinning', async () => {
    listLightcurves.mockResolvedValue({
      success: true,
      data: [{ name: 'obs1_lc', n_bins: 3, dt: 1, time_range: [0.5, 2.5] }],
    });
    deleteLightcurve.mockImplementation(async () => {
      listLightcurves.mockResolvedValue({ success: true, data: [] });
      return { success: true, data: { name: 'obs1_lc' }, message: 'deleted', error: null };
    });
    renderWithProviders(<LightCurvePage />);
    await userEvent.click(await screen.findByLabelText('Event list'));
    await userEvent.click(await screen.findByRole('option', { name: /obs1/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Generate' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Rebin' })).toBeEnabled());
    await userEvent.click(screen.getByLabelText('Light curve'));
    await userEvent.click(screen.getByRole('option', { name: /obs1_lc/ }));
    await userEvent.click(screen.getByLabelText('Delete selected light curve'));
    expect(await screen.findByText(/stored light curve was deleted or replaced/)).toBeInTheDocument();
    expect(screen.getByTestId('chart')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Rebin' })).toBeDisabled();
  });

  it('keeps its original plot and inputs read-only after a backend restart', async () => {
    const ready = (generation: number): BackendState => ({
      generation, phase: 'ready', port: 54321, isReady: true, error: null,
    });
    listLightcurves.mockResolvedValue({
      success: true,
      data: [{ name: 'obs1_lc', n_bins: 3, dt: 1, time_range: [0.5, 2.5] }],
    });
    const page = (generation: number) => (
      <BackendContext.Provider value={ready(generation)}><LightCurvePage /></BackendContext.Provider>
    );
    const view = renderWithProviders(page(1));
    await userEvent.click(await screen.findByLabelText('Event list'));
    await userEvent.click(await screen.findByRole('option', { name: /obs1/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Generate' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Rebin' })).toBeEnabled());
    await userEvent.click(screen.getByLabelText('Light curve'));
    await userEvent.click(screen.getByRole('option', { name: /obs1_lc/ }));
    expect(screen.getByLabelText('Light curve')).toHaveTextContent('obs1_lc');
    view.rerender(page(2));
    expect(await screen.findByText(/previous backend session and is read-only/)).toBeInTheDocument();
    expect(screen.getByTestId('chart')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Rebin' })).toBeDisabled();
    expect(screen.getByLabelText('Light curve')).not.toHaveTextContent('obs1_lc');
    expect(rebin).not.toHaveBeenCalled();
  });
});
