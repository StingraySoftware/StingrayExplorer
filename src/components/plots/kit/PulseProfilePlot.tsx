import React from 'react';
import type { Data } from 'plotly.js';
import PlotlyChart from '../PlotlyChart';

interface PulseProfilePlotProps {
  /** Bin centres in [0, 1). */
  phase: number[];
  counts: number[];
  errors?: number[] | null;
  /** Repetitions drawn, conventionally two for readability. */
  cycles?: number;
  yTitle?: string;
  workspaceKey?: string;
  height?: number;
}

/** A folded pulse profile drawn over several cycles, with Poisson or given errors. */
const PulseProfilePlot: React.FC<PulseProfilePlotProps> = ({
  phase,
  counts,
  errors,
  cycles = 2,
  yTitle = 'Counts',
  workspaceKey,
  height = 380,
}) => {
  const x: number[] = [];
  const y: number[] = [];
  const err: number[] = [];
  for (let cycle = 0; cycle < cycles; cycle += 1) {
    phase.forEach((value, index) => {
      x.push(value + cycle);
      y.push(counts[index]);
      err.push(errors ? errors[index] : Math.sqrt(Math.max(counts[index], 0)));
    });
  }
  return (
    <PlotlyChart
      workspaceKey={workspaceKey}
      height={height}
      data={[
        {
          x,
          y,
          type: 'scatter',
          mode: 'lines',
          line: { shape: 'hvh', width: 1.5 },
          error_y: { type: 'data', array: err, visible: true, thickness: 1, width: 0 },
        } as Data,
      ]}
      layout={{
        xaxis: { title: { text: 'Phase' }, range: [0, cycles] },
        yaxis: { title: { text: yTitle } },
      }}
    />
  );
};

export default PulseProfilePlot;
