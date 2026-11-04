/**
 * Plot components for each registered result kind's default_plot, as listed
 * by GET /api/results/kinds (python-backend/services/result_registry.py).
 */
export const DEFAULT_PLOT_COMPONENTS = {
  event_list: 'EventList page histograms',
  lightcurve: 'LightCurve page chart',
  spectrum: 'SpectrumPlot',
  cross_spectrum: 'SpectrumPlot',
  image_2d: 'Image2DPlot',
  power_colors: 'PowerColors page chart',
  time_lags: 'SpectrumPlot',
  coherence: 'SpectrumPlot',
  table: 'NumericResultTable',
  // Arrive with the pulsar and modelling phases.
  pulse_profile: 'PulseProfilePlot',
  posterior: 'CornerPlot',
} as const;

export type DefaultPlotId = keyof typeof DEFAULT_PLOT_COMPONENTS;
