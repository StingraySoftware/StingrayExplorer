import { render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { chart } = vi.hoisted(() => ({ chart: vi.fn() }));
vi.mock('../PlotlyChart', () => ({
  default: (props: unknown) => {
    chart(props);
    return null;
  },
}));
import SpectrumPlot from './SpectrumPlot';
import Image2DPlot from './Image2DPlot';
import PulseProfilePlot from './PulseProfilePlot';
import CornerPlot from './CornerPlot';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const lastProps = (): any => chart.mock.calls[chart.mock.calls.length - 1][0];

describe('plot kit', () => {
  beforeEach(() => chart.mockClear());

  it('draws spectra with error bars on log axes', () => {
    render(
      <SpectrumPlot
        series={[{ name: 'a', freq: [1, 2], power: [3, null], error: [0.5, null] }, { freq: [1], power: [1] }]}
      />
    );
    const { data, layout } = lastProps();
    expect(layout.xaxis.type).toBe('log');
    expect(layout.yaxis.type).toBe('log');
    expect(data[0].error_y.array).toEqual([0.5, 0]);
    expect(data[1].error_y).toBeUndefined();
    expect(layout.showlegend).toBe(true);
  });

  it('can draw linear spectra', () => {
    render(<SpectrumPlot series={[{ freq: [1], power: [1] }]} logX={false} logY={false} yTitle="Lag (s)" />);
    const { layout } = lastProps();
    expect(layout.xaxis.type).toBe('linear');
    expect(layout.yaxis.title.text).toBe('Lag (s)');
  });

  it('draws 2-D images with an optional log colour scale', () => {
    render(
      <Image2DPlot x={[0, 1]} y={[1]} z={[[10, 0]]} logZ xTitle="Time (s)" yTitle="Frequency (Hz)" zTitle="Power" />
    );
    const { data } = lastProps();
    expect(data[0].type).toBe('heatmap');
    expect(data[0].z).toEqual([[1, null]]);
    expect(data[0].colorbar.title.text).toBe('log10 Power');
  });

  it('repeats pulse profiles over two cycles with Poisson errors by default', () => {
    render(<PulseProfilePlot phase={[0.25, 0.75]} counts={[4, 9]} />);
    const { data, layout } = lastProps();
    expect(data[0].x).toEqual([0.25, 0.75, 1.25, 1.75]);
    expect(data[0].error_y.array).toEqual([2, 3, 2, 3]);
    expect(layout.xaxis.range).toEqual([0, 2]);
  });

  it('lays out corner plots with histograms on the diagonal', () => {
    const samples = Array.from({ length: 50 }, (_, index) => [index, index * 2, index % 7]);
    render(<CornerPlot samples={samples} labels={['a', 'b', 'c']} />);
    const { data, layout } = lastProps();
    expect(data).toHaveLength(6);
    expect(data.filter((trace: { type: string }) => trace.type === 'histogram')).toHaveLength(3);
    expect(data[1].type).toBe('histogram2dcontour');
    expect(data[1].x).toEqual(samples.map((row) => row[0]));
    expect(data[1].y).toEqual(samples.map((row) => row[1]));
    expect(layout.xaxis6.title.text).toBe('c');
  });
});
