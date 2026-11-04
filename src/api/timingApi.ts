/**
 * API functions for timing analysis operations
 */

import { apiClient, ApiResponse } from './client';
import type { EventSelection } from './selectionApi';

// Types
export interface BispectrumData {
  name: string | null;
  freq: number[];
  lags: number[];
  bispec_mag: number[][];
  bispec_phase: number[][];
  maxlag: number;
  scale: string;
  window: string;
}

export interface PowerColorsData {
  name: string | null;
  power_colors: Record<string, Array<number | null>>;
  time: number[];
  freq_ranges: Record<string, [number, number]>;
  band_order: string[];
  band_variance_errors: Record<string, Array<number | null>>;
  pc1: Array<number | null>;
  pc1_err: Array<number | null>;
  pc2: Array<number | null>;
  pc2_err: Array<number | null>;
  valid_segments: boolean[];
  band_bin_counts: Record<string, number>;
  normalization: 'frac';
  variance_unit: string;
  /** Mean Poisson level; integration uses the per-segment levels below. */
  poisson_power: number;
  poisson_power_by_segment: number[];
  segment_count_rates: number[];
  common_mean_count_rate: number;
  normalization_reference: string;
  dt: number;
  segment_size: number;
  df: number;
  detection_sigma: number;
  warnings: string[];
  metadata: Record<string, unknown>;
  provenance: {
    input_source: { kind: string; name: string };
    parameters: Record<string, unknown>;
    [key: string]: unknown;
  };
}

export interface TimeLagsData {
  name: string | null;
  freq: number[];
  time_lags: Array<number | null>;
  time_lags_err?: Array<number | null> | null;
  freq_range: [number, number] | null;
}

export interface CoherenceData {
  name: string | null;
  freq: number[];
  coherence: Array<number | null>;
  coherence_err?: Array<number | null> | null;
  segment_size?: number;
  n_segments?: number | null;
}

// API functions
export const timingApi = {
  /**
   * Create a bispectrum from an EventList
   */
  async createBispectrum(params: {
    event_list_name: string;
    selection?: EventSelection | null;
    dt: number;
    maxlag?: number;
    scale?: string;
    window?: string;
    output_name?: string;
  }): Promise<ApiResponse<BispectrumData>> {
    return apiClient.post('/api/timing/bispectrum', {
      event_list_name: params.event_list_name,
      selection: params.selection ?? undefined,
      dt: params.dt,
      maxlag: params.maxlag || 25,
      scale: params.scale || 'unbiased',
      window: params.window || 'uniform',
      output_name: params.output_name,
    });
  },

  /**
   * Calculate power colors from frequency bands
   */
  async calculatePowerColors(params: {
    event_list_name: string;
    selection?: EventSelection | null;
    dt: number;
    segment_size: number;
    freq_ranges: Record<string, [number, number]>;
    output_name?: string;
  }): Promise<ApiResponse<PowerColorsData>> {
    return apiClient.post('/api/timing/power-colors', {
      event_list_name: params.event_list_name,
      selection: params.selection ?? undefined,
      dt: params.dt,
      segment_size: params.segment_size,
      freq_ranges: params.freq_ranges,
      output_name: params.output_name,
    });
  },

  /**
   * Calculate time lags between two event lists
   */
  async calculateTimeLags(params: {
    event_list_1_name: string;
    event_list_2_name: string;
    selection_1?: EventSelection | null;
    selection_2?: EventSelection | null;
    dt: number;
    segment_size: number;
    freq_range?: [number, number];
    output_name?: string;
  }): Promise<ApiResponse<TimeLagsData>> {
    return apiClient.post('/api/timing/time-lags', {
      event_list_1_name: params.event_list_1_name,
      event_list_2_name: params.event_list_2_name,
      selection_1: params.selection_1 ?? undefined,
      selection_2: params.selection_2 ?? undefined,
      dt: params.dt,
      segment_size: params.segment_size,
      freq_range: params.freq_range,
      output_name: params.output_name,
    });
  },

  /**
   * Calculate coherence between two event lists
   */
  async calculateCoherence(params: {
    event_list_1_name: string;
    event_list_2_name: string;
    selection_1?: EventSelection | null;
    selection_2?: EventSelection | null;
    dt: number;
    segment_size: number;
    output_name?: string;
  }): Promise<ApiResponse<CoherenceData>> {
    return apiClient.post('/api/timing/coherence', {
      event_list_1_name: params.event_list_1_name,
      event_list_2_name: params.event_list_2_name,
      selection_1: params.selection_1 ?? undefined,
      selection_2: params.selection_2 ?? undefined,
      dt: params.dt,
      segment_size: params.segment_size,
      output_name: params.output_name,
    });
  },
};

export default timingApi;
