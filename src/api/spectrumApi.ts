/**
 * API functions for spectrum operations
 */

import { apiClient, ApiResponse } from './client';

// Types
export interface PowerSpectrumData {
  name: string | null;
  freq: number[];
  power: Array<number | null>;
  power_phase?: Array<number | null> | null;
  norm?: string;
  n_freq: number;
  df?: number | number[];
  frequency_bin_width?: number[];
  freq_range?: [number, number];
  segment_size?: number;
  n_segments?: number;
  result_id?: string;
  backend_session_id?: string;
  operation?: string;
  inputs?: unknown[];
  parameters?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
  warnings?: string[];
  created_at?: string;
}

export interface DynamicalPowerSpectrumData {
  name: string | null;
  freq: number[];
  time: number[];
  dyn_ps: Array<Array<number | null>>;
  norm: string;
  segment_size: number;
  shape: [number, number];
  result_id?: string;
  backend_session_id?: string;
  inputs?: unknown[];
  parameters?: Record<string, unknown>;
}

export interface SpectrumSummary {
  name: string;
  type: string;
  n_freq: number | null;
  result_id?: string;
  backend_session_id?: string;
}

// API functions
export const spectrumApi = {
  /**
   * Create a power spectrum from an EventList
   */
  async createPowerSpectrum(params: {
    event_list_name: string;
    dt: number;
    norm?: string;
    output_name?: string;
  }): Promise<ApiResponse<PowerSpectrumData>> {
    return apiClient.post('/api/spectrum/power-spectrum', {
      event_list_name: params.event_list_name,
      dt: params.dt,
      norm: params.norm || 'leahy',
      output_name: params.output_name,
    });
  },

  /**
   * Create an averaged power spectrum from an EventList
   */
  async createAveragedPowerSpectrum(params: {
    event_list_name: string;
    dt: number;
    segment_size: number;
    norm?: string;
    output_name?: string;
  }): Promise<ApiResponse<PowerSpectrumData>> {
    return apiClient.post('/api/spectrum/averaged-power-spectrum', {
      event_list_name: params.event_list_name,
      dt: params.dt,
      segment_size: params.segment_size,
      norm: params.norm || 'leahy',
      output_name: params.output_name,
    });
  },

  /**
   * Create a cross spectrum from two EventLists
   */
  async createCrossSpectrum(params: {
    event_list_1_name: string;
    event_list_2_name: string;
    dt: number;
    norm?: string;
    output_name?: string;
  }): Promise<ApiResponse<PowerSpectrumData>> {
    return apiClient.post('/api/spectrum/cross-spectrum', {
      event_list_1_name: params.event_list_1_name,
      event_list_2_name: params.event_list_2_name,
      dt: params.dt,
      norm: params.norm || 'leahy',
      output_name: params.output_name,
    });
  },

  /**
   * Create an averaged cross spectrum from two EventLists
   */
  async createAveragedCrossSpectrum(params: {
    event_list_1_name: string;
    event_list_2_name: string;
    dt: number;
    segment_size: number;
    norm?: string;
    output_name?: string;
  }): Promise<ApiResponse<PowerSpectrumData>> {
    return apiClient.post('/api/spectrum/averaged-cross-spectrum', {
      event_list_1_name: params.event_list_1_name,
      event_list_2_name: params.event_list_2_name,
      dt: params.dt,
      segment_size: params.segment_size,
      norm: params.norm || 'leahy',
      output_name: params.output_name,
    });
  },

  /**
   * Create a dynamical power spectrum from an EventList
   */
  async createDynamicalPowerSpectrum(params: {
    event_list_name: string;
    dt: number;
    segment_size: number;
    norm?: string;
    output_name?: string;
  }): Promise<ApiResponse<DynamicalPowerSpectrumData>> {
    return apiClient.post('/api/spectrum/dynamical-power-spectrum', {
      event_list_name: params.event_list_name,
      dt: params.dt,
      segment_size: params.segment_size,
      norm: params.norm || 'leahy',
      output_name: params.output_name,
    });
  },

  /**
   * Rebin a spectrum
   */
  async rebinSpectrum(params: {
    name: string;
    rebin_factor: number;
    log?: boolean;
    output_name?: string;
    expected_result_id?: string;
  }): Promise<ApiResponse<PowerSpectrumData>> {
    return apiClient.post('/api/spectrum/rebin', {
      name: params.name,
      rebin_factor: params.rebin_factor,
      log: params.log || false,
      output_name: params.output_name,
      expected_result_id: params.expected_result_id,
    });
  },

  /**
   * List all loaded spectra
   */
  async listSpectra(): Promise<ApiResponse<SpectrumSummary[]>> {
    return apiClient.get('/api/spectrum/');
  },

  /**
   * Delete a spectrum from state
   */
  async deleteSpectrum(name: string): Promise<ApiResponse<{ name: string }>> {
    return apiClient.delete(`/api/spectrum/${encodeURIComponent(name)}`);
  },
};

export default spectrumApi;
