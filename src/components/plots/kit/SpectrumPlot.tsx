import React from 'react';
import type { Data } from 'plotly.js';
import PlotlyChart from '../PlotlyChart';

export interface SpectrumSeries {
  name?: string;
  freq: number[];
  power: Array<number | null>;
  /** One-sigma errors; drawn as error bars. */
  error?: Array<number | null> | null;
  color?: string;
}

interface SpectrumPlotProps {
  series: SpectrumSeries[];
  logX?: boolean;
  logY?: boolean;
  yTitle?: string;
  workspaceKey?: string;
  height?: number;
}

/** Power (or any spectral quantity) against frequency, with errors, on log axes. */
const SpectrumPlot: React.FC<SpectrumPlotProps> = ({
  series,
  logX = true,
  logY = true,
  yTitle = 'Power',
  workspaceKey,
  height = 420,
}) => {
  const data: Data[] = series.map((item) => ({
    x: item.freq,
    y: item.power,
    name: item.name,
    type: 'scatter',
    mode: 'lines+markers',
    marker: { size: 3, color: item.color },
    line: { width: 1, color: item.color },
    ...(item.error
      ? {
        error_y: {
          type: 'data',
          array: item.error.map((value) => value ?? 0),
          visible: true,
          thickness: 1,
          width: 0,
        },
      }
      : {}),
  })) as Data[];
  return (
    <PlotlyChart
      workspaceKey={workspaceKey}
      data={data}
      height={height}
      layout={{
        xaxis: { title: { text: 'Frequency (Hz)' }, type: logX ? 'log' : 'linear' },
        yaxis: { title: { text: yTitle }, type: logY ? 'log' : 'linear' },
        showlegend: series.length > 1,
      }}
    />
  );
};

export default SpectrumPlot;
