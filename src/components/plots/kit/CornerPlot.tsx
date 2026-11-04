import React from 'react';
import type { Data, Layout } from 'plotly.js';
import PlotlyChart from '../PlotlyChart';

interface CornerPlotProps {
  /** Posterior samples: one row per sample, one column per parameter. */
  samples: number[][];
  labels: string[];
  bins?: number;
  workspaceKey?: string;
  height?: number;
}

const axisName = (prefix: 'x' | 'y', index: number) => (index === 0 ? prefix : `${prefix}${index + 1}`);

/**
 * Pairwise posterior plot: 1-D histograms on the diagonal and 2-D density
 * contours below it, with shared axes per parameter.
 */
const CornerPlot: React.FC<CornerPlotProps> = ({
  samples,
  labels,
  bins = 30,
  workspaceKey,
  height = 600,
}) => {
  const n = labels.length;
  const columns = labels.map((_, index) => samples.map((row) => row[index]));
  const gap = 0.02;
  const size = (1 - gap * (n - 1)) / n;
  const domain = (index: number): [number, number] => [index * (size + gap), index * (size + gap) + size];
  const data: Data[] = [];
  const layout: Partial<Layout> = { showlegend: false, height };
  let panel = 0;
  for (let row = 0; row < n; row += 1) {
    for (let column = 0; column <= row; column += 1) {
      const xa = axisName('x', panel);
      const ya = axisName('y', panel);
      if (row === column) {
        data.push({ x: columns[column], type: 'histogram', nbinsx: bins, xaxis: xa, yaxis: ya } as Data);
      } else {
        data.push({
          x: columns[column],
          y: columns[row],
          type: 'histogram2dcontour',
          ncontours: 8,
          showscale: false,
          xaxis: xa,
          yaxis: ya,
        } as Data);
      }
      const layoutRecord = layout as Record<string, unknown>;
      layoutRecord[xa === 'x' ? 'xaxis' : `xaxis${panel + 1}`] = {
        domain: domain(column),
        anchor: ya,
        title: row === n - 1 ? { text: labels[column] } : undefined,
        showticklabels: row === n - 1,
      };
      layoutRecord[ya === 'y' ? 'yaxis' : `yaxis${panel + 1}`] = {
        domain: domain(n - 1 - row),
        anchor: xa,
        title: column === 0 && row !== column ? { text: labels[row] } : undefined,
        showticklabels: column === 0 && row !== column,
      };
      panel += 1;
    }
  }
  return <PlotlyChart workspaceKey={workspaceKey} data={data} layout={layout} height={height} />;
};

export default CornerPlot;
