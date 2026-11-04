/**
 * API functions for Lightcurve operations
 */

import { apiClient, ApiResponse } from './client';
import type { EventSelection } from './selectionApi';

// Types
export interface LightcurveData {
  name: string;
  time: number[];
  counts: number[];
  dt: number;
  n_bins: number;
  result_id?: string;
  backend_session_id?: string;
  inputs?: unknown[];
  parameters?: Record<string, unknown>;
  plot_stride?: number;
  time_range?: [number, number];
  count_rate_mean?: number;
  count_stats?: {
    mean: number;
    std: number;
    min: number;
    max: number;
  };
}

export interface LightcurveSummary {
  name: string;
  n_bins: number;
  dt: number;
  time_range: [number, number];
  result_id?: string;
}

/** A light-curve table found in a FITS file. */
export interface LightcurveFileTable {
  index: number;
  name: string;
  rate_columns: string[];
  n_rows: number;
  n_bands: number;
  timeunit: string | null;
  has_mjdref: boolean;
  telescope: string | null;
  instrument: string | null;
}

// API functions
export const lightcurveApi = {
  /** List the light-curve tables in a natively selected FITS file. */
  async inspectFile(params: {
    file_path: string;
    file_grant: string;
  }): Promise<ApiResponse<{ tables: LightcurveFileTable[] }>> {
    return apiClient.post('/api/lightcurve/inspect-file', params);
  },

  /** Store a light curve read from a natively selected mission FITS file. */
  async loadFromFile(params: {
    file_path: string;
    file_grant: string;
    output_name: string;
    hdu?: number;
    rate_column?: string;
    band?: number;
    mjdref?: number;
  }): Promise<ApiResponse<LightcurveData>> {
    return apiClient.post('/api/lightcurve/from-file', params);
  },

  /**
   * Create a Lightcurve from an EventList
   */
  async createFromEventList(params: {
    event_list_name: string;
    selection?: EventSelection | null;
    dt: number;
    output_name: string;
    gti?: number[][];
    max_points?: number;
  }): Promise<ApiResponse<LightcurveData>> {
    return apiClient.post('/api/lightcurve/from-event-list', {
      event_list_name: params.event_list_name,
      selection: params.selection ?? undefined,
      dt: params.dt,
      output_name: params.output_name,
      gti: params.gti,
      max_points: params.max_points,
    });
  },

  /**
   * Create a Lightcurve from arrays
   */
  async createFromArrays(params: {
    times: number[];
    counts: number[];
    dt: number;
    output_name: string;
  }): Promise<ApiResponse<LightcurveData>> {
    return apiClient.post('/api/lightcurve/from-arrays', params);
  },

  /**
   * Rebin a lightcurve
   */
  async rebin(params: {
    name: string;
    rebin_factor: number;
    output_name: string;
    max_points?: number;
    expected_result_id?: string;
  }): Promise<ApiResponse<LightcurveData>> {
    return apiClient.post('/api/lightcurve/rebin', {
      name: params.name,
      rebin_factor: params.rebin_factor,
      output_name: params.output_name,
      max_points: params.max_points,
      expected_result_id: params.expected_result_id,
    });
  },

  /**
   * Get lightcurve data for plotting
   */
  async getLightcurveData(
    name: string,
    maxPoints?: number
  ): Promise<ApiResponse<LightcurveData>> {
    const query = maxPoints ? `?max_points=${maxPoints}` : '';
    return apiClient.get(`/api/lightcurve/${encodeURIComponent(name)}${query}`);
  },

  /**
   * List all loaded lightcurves
   */
  async listLightcurves(): Promise<ApiResponse<LightcurveSummary[]>> {
    return apiClient.get('/api/lightcurve/');
  },

  /**
   * Delete a lightcurve from state
   */
  async deleteLightcurve(name: string): Promise<ApiResponse<{ name: string }>> {
    return apiClient.delete(`/api/lightcurve/${encodeURIComponent(name)}`);
  },
};

export default lightcurveApi;
