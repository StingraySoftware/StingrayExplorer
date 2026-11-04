import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/testUtils';

const { calculatePowerColors, chartProps } = vi.hoisted(() => ({
  calculatePowerColors: vi.fn(),
  chartProps: vi.fn(),
}));
vi.mock('@/api/dataApi', () => ({
  dataApi: {
    listEventLists: async () => ({
      success: true,
      data: [{ name: 'obs1', n_events: 5000 }],
    }),
  },
}));
vi.mock('@/api/timingApi', () => ({ timingApi: { calculatePowerColors } }));
vi.mock('@/components/plots/PlotlyChart', () => ({
  default: (props: unknown) => {
    chartProps(props);
    return <div data-testid="chart" />;
  },
}));
import PowerColorsPage from './index';

const bands = {
  A: [1 / 256, 1 / 32],
  B: [1 / 32, .25],
  C: [.25, 2],
  D: [2, 16],
};
const result = {
  name: null,
  time: [256],
  freq_ranges: bands,
  band_order: ['A', 'B', 'C', 'D'],
  power_colors: { A: [.1], B: [.2], C: [.4], D: [.1] },
  band_variance_errors: { A: [.01], B: [.02], C: [.04], D: [.01] },
  pc1: [4],
  pc1_err: [.4],
  pc2: [2],
  pc2_err: [.2],
  valid_segments: [true],
  normalization: 'frac',
  variance_unit: 'fractional rms squared',
  poisson_power: .01,
  poisson_power_by_segment: [.01],
  segment_count_rates: [200],
  normalization_reference: 'common mean detected count rate',
  dt: 1 / 64,
  segment_size: 512,
  df: 1 / 512,
  detection_sigma: 3,
  warnings: ['Scientific advisory from backend'],
  provenance: {
    input_source: { kind: 'event_list', name: 'obs1' },
    parameters: { dt: 1 / 64, segment_size: 512, freq_ranges: bands },
  },
};

async function chooseEventList() {
  await userEvent.click(await screen.findByLabelText('Event list'));
  await userEvent.click(await screen.findByText(/obs1/));
}

describe('PowerColorsPage', () => {
  beforeEach(() => {
    chartProps.mockClear();
    calculatePowerColors.mockResolvedValue({
      success: true,
      data: result,
      warnings: ['Additional request warning'],
    });
  });

  it('uses exact canonical bounds and resolved 512-second defaults', async () => {
    renderWithProviders(<PowerColorsPage />);
    await chooseEventList();
    expect(screen.getByLabelText(/Segment size/)).toHaveValue('512');
    expect(screen.getByLabelText(/Time bin/)).toHaveValue('0.015625');
    await userEvent.click(screen.getByRole('button', { name: 'Compute' }));
    expect(calculatePowerColors).toHaveBeenCalledWith({
      event_list_name: 'obs1',
      dt: 1 / 64,
      segment_size: 512,
      freq_ranges: bands,
    });
    expect(await screen.findByText('Scientific advisory from backend')).toBeInTheDocument();
    expect(screen.getByText('Additional request warning')).toBeInTheDocument();
    expect(chartProps.mock.calls.some(([props]) =>
      props.data?.[0]?.error_x?.array?.[0] === .4
    )).toBe(true);
  });

  it('blocks unsupported Nyquist-edge and unresolved lower-band requests', async () => {
    renderWithProviders(<PowerColorsPage />);
    await chooseEventList();
    const dt = screen.getByLabelText(/Time bin/);
    await userEvent.clear(dt);
    await userEvent.type(dt, '.03125');
    expect(screen.getByRole('button', { name: 'Compute' })).toBeDisabled();
    expect(screen.getByText(/available Fourier support/)).toBeInTheDocument();
    await userEvent.clear(dt);
    await userEvent.type(dt, '.015625');
    const segment = screen.getByLabelText(/Segment size/);
    await userEvent.clear(segment);
    await userEvent.type(segment, '64');
    expect(screen.getByRole('button', { name: 'Compute' })).toBeDisabled();
    expect(screen.getByText(/Fourier resolution/)).toBeInTheDocument();
  });

  it('keeps backend ratios and frozen result bands when inputs are edited', async () => {
    renderWithProviders(<PowerColorsPage />);
    await chooseEventList();
    await userEvent.click(screen.getByRole('button', { name: 'Compute' }));
    await screen.findByText('Scientific advisory from backend');
    const minimum = screen.getAllByLabelText('f min')[0];
    await userEvent.clear(minimum);
    await userEvent.type(minimum, '.01');
    expect(screen.getByText(/Inputs have changed since this result/)).toBeInTheDocument();
    const diagrams = chartProps.mock.calls
      .map(([props]) => props)
      .filter((props) => props.data?.[0]?.error_x);
    expect(diagrams.at(-1).data[0].x).toEqual([4]);
    expect(diagrams.at(-1).data[0].y).toEqual([2]);
    expect(screen.getByText(/A: 0.00390625–0.03125 Hz/)).toBeInTheDocument();
  });

  it('explains null colours while retaining negative variances on a linear plot', async () => {
    calculatePowerColors.mockResolvedValue({
      success: true,
      data: {
        ...result,
        pc1: [null],
        pc1_err: [null],
        pc2: [null],
        pc2_err: [null],
        valid_segments: [false],
        power_colors: { ...result.power_colors, A: [-.01] },
      },
    });
    renderWithProviders(<PowerColorsPage />);
    await chooseEventList();
    await userEvent.click(screen.getByRole('button', { name: 'Compute' }));
    expect(await screen.findByText(/No segment has a positive/)).toBeInTheDocument();
    const varianceChart = chartProps.mock.calls
      .map(([props]) => props)
      .find((props) => props.data?.[0]?.y?.[0] === -.01);
    expect(varianceChart.layout.yaxis.type).toBe('linear');
  });
});
