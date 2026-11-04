import React from 'react';
import type { Data } from 'plotly.js';
import PlotlyChart from '../PlotlyChart';

interface Image2DPlotProps {
  x: number[];
  y: number[];
  /** Rows follow y and columns follow x (Plotly's heatmap convention). */
  z: Array<Array<number | null>>;
  logZ?: boolean;
  xTitle: string;
  yTitle: string;
  zTitle?: string;
  workspaceKey?: string;
  height?: number;
}

/** A 2-D image, e.g. a dynamical power spectrum or a phaseogram. */
const Image2DPlot: React.FC<Image2DPlotProps> = ({
  x,
  y,
  z,
  logZ = false,
  xTitle,
  yTitle,
  zTitle = 'Value',
  workspaceKey,
  height = 500,
}) => {
  const values = logZ
    ? z.map((row) => row.map((value) => (value !== null && value > 0 ? Math.log10(value) : null)))
    : z;
  return (
    <PlotlyChart
      workspaceKey={workspaceKey}
      height={height}
      data={[
        {
          x,
          y,
          z: values,
          type: 'heatmap',
          colorscale: 'Viridis',
          colorbar: { title: { text: logZ ? `log10 ${zTitle}` : zTitle } },
        } as Data,
      ]}
      layout={{ xaxis: { title: { text: xTitle } }, yaxis: { title: { text: yTitle } } }}
    />
  );
};

export default Image2DPlot;
