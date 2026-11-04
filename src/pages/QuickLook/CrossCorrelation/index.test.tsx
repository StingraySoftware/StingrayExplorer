import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/testUtils';
import { useUIStore } from '@/store/uiStore';

const listEventLists = vi.fn();
vi.mock('@/api/dataApi', () => ({
  dataApi: { listEventLists: (...a: unknown[]) => listEventLists(...a) },
}));

const crossCorrelation = vi.fn();
vi.mock('@/api/correlationApi', () => ({
  correlationApi: {
    crossCorrelation: (...a: unknown[]) => crossCorrelation(...a),
  },
}));

const previewSelection = vi.fn();
vi.mock('@/api/selectionApi', () => ({
  selectionApi: { previewSelection: (...a: unknown[]) => previewSelection(...a) },
}));

vi.mock('@/api/schemaApi', async () => {
  const schemas = (await import('@/test/fixtures/form-schemas.json')).default;
  return {
    schemaApi: {
      getFormSchema: async () => ({ success: true, data: schemas.cross_correlation, message: '', error: null }),
    },
  };
});

vi.mock('@/components/plots/PlotlyChart', () => ({
  default: () => <div data-testid="chart" />,
}));

import CrossCorrelationPage from './index';

async function selectEventList(label: string, name: string): Promise<void> {
  await userEvent.click(await screen.findByLabelText(label));
  await userEvent.click(await screen.findAllByText(new RegExp(name)).then((els) => els[els.length - 1]));
}

describe('CrossCorrelationPage', () => {
  beforeEach(() => {
    useUIStore.setState({ notifications: [], unreadNotificationCount: 0 });
    listEventLists.mockResolvedValue({
      success: true,
      data: [
        { name: 'obs1', n_events: 5000, time_range: [0, 100] },
        { name: 'obs2', n_events: 4000, time_range: [0, 100] },
      ],
      message: '',
      error: null,
    });
    crossCorrelation.mockResolvedValue({
      success: true,
      data: {
        time_lags: [-0.5, 0, 0.5],
        corr: [2.0, 10.0, 2.0],
        time_shift: -0.5,
        dt: 0.1,
        n: 3,
        mode: 'same',
        norm: 'none',
        warnings: [],
      },
      message: 'done',
      error: null,
    });
  });

  it('computes a cross-correlation with parsed parameters, plots it, and shows the time-shift chip', async () => {
    renderWithProviders(<CrossCorrelationPage />);
    await selectEventList('Event list 1', 'obs1');
    await selectEventList('Event list 2', 'obs2');
    const dtField = screen.getByLabelText(/Time bin/);
    await userEvent.clear(dtField);
    await userEvent.type(dtField, '0.1');
    await userEvent.click(screen.getByRole('button', { name: /Compute/ }));
    await waitFor(() =>
      expect(crossCorrelation).toHaveBeenCalledWith(
        expect.objectContaining({
          event_list_1_name: 'obs1',
          event_list_2_name: 'obs2',
          dt: 0.1,
          mode: 'same',
          norm: 'none',
        })
      )
    );
    expect(await screen.findByTestId('chart')).toBeInTheDocument();
    expect(await screen.findByText(/time shift: -0.5000 s/)).toBeInTheDocument();
    expect(
      screen.getByText(/Positive shift means the first list lags the second\./)
    ).toBeInTheDocument();
  });

  it('disables Compute until inputs are valid', async () => {
    renderWithProviders(<CrossCorrelationPage />);
    const button = await screen.findByRole('button', { name: /Compute/ });
    expect(button).toBeDisabled();
  });

  it('omits the time-shift chip and renders warnings when time_shift is null', async () => {
    crossCorrelation.mockResolvedValue({
      success: true,
      data: {
        time_lags: [-0.1, 0, 0.1],
        corr: [null, 10.0, null],
        time_shift: null,
        dt: 0.1,
        n: 3,
        mode: 'same',
        norm: 'variance',
        warnings: ['The correlation contains NaN values.'],
      },
      message: 'done',
      error: null,
    });
    renderWithProviders(<CrossCorrelationPage />);
    await selectEventList('Event list 1', 'obs1');
    await selectEventList('Event list 2', 'obs2');
    const dtField = screen.getByLabelText(/Time bin/);
    await userEvent.clear(dtField);
    await userEvent.type(dtField, '0.1');
    await userEvent.click(screen.getByRole('button', { name: /Compute/ }));
    expect(await screen.findByText(/The correlation contains NaN values\./)).toBeInTheDocument();
    expect(screen.queryByText(/time shift:/)).not.toBeInTheDocument();
  });

  it('splits one event list into a subject and a reference band', async () => {
    listEventLists.mockResolvedValue({
      success: true,
      data: [{ name: 'obs1', n_events: 5000, time_range: [0, 100], has_energy: true }],
      message: '',
      error: null,
    });
    previewSelection.mockResolvedValue({
      success: true,
      data: {
        event_list_name: 'obs1',
        n_events: 2500,
        parent_n_events: 5000,
        energy_coverage: [0.5, 1.9],
        pi_coverage: null,
        detector_ids: null,
        exposure: 100,
      },
    });
    renderWithProviders(<CrossCorrelationPage />);
    await userEvent.click(await screen.findByLabelText('Two bands of one event list'));
    await selectEventList('Event list', 'obs1');
    const compute = screen.getByRole('button', { name: /Compute/ });
    expect(compute).toBeDisabled();

    const [subjectEnergy, referenceEnergy] = screen.getAllByRole('button', { name: 'Energy' });
    await userEvent.click(subjectEnergy);
    await userEvent.click(referenceEnergy);
    const [subjectLow, referenceLow] = screen.getAllByLabelText('From (keV)');
    const [subjectHigh, referenceHigh] = screen.getAllByLabelText('To (keV)');
    await userEvent.type(subjectLow, '0.5');
    await userEvent.type(subjectHigh, '3');
    await userEvent.type(referenceLow, '2');
    await userEvent.type(referenceHigh, '10');
    expect(screen.getByText(/These bands can share photons/)).toBeInTheDocument();

    await userEvent.clear(subjectHigh);
    await userEvent.type(subjectHigh, '2');
    expect(screen.queryByText(/These bands can share photons/)).not.toBeInTheDocument();

    await userEvent.click(compute);
    await waitFor(() =>
      expect(crossCorrelation).toHaveBeenCalledWith(
        expect.objectContaining({
          event_list_1_name: 'obs1',
          event_list_2_name: 'obs1',
          selection_1: { energy_range: [0.5, 2] },
          selection_2: { energy_range: [2, 10] },
        })
      )
    );
  });

  it('sends no selection fields when every photon is used', async () => {
    renderWithProviders(<CrossCorrelationPage />);
    await selectEventList('Event list 1', 'obs1');
    await selectEventList('Event list 2', 'obs2');
    await userEvent.click(screen.getByRole('button', { name: /Compute/ }));
    await waitFor(() => expect(crossCorrelation).toHaveBeenCalled());
    const request = crossCorrelation.mock.calls[0][0];
    expect(request).not.toHaveProperty('selection_1');
    expect(request).not.toHaveProperty('selection_2');
  });
});
