/**
 * API functions for dead-time correction operations (model-based PDS
 * correction and two-detector FAD correction).
 */

import { apiClient, ApiResponse } from './client';
import type { EventSelection } from './selectionApi';

// Types

export interface PdsCorrectionData {
  freq: number[];
  power_uncorrected: Array<number | null>;
  power_corrected: Array<number | null>;
  rate: number;
  n_events: number;
  exposure: number;
  n_segments: number;
  dt: number;
  segment_size: number;
  dead_time: number;
  background_rate: number;
  limit_k: number;
  norm: string;
  warnings: string[];
}

export interface FadCorrectionData {
  freq: number[];
  pds1: Array<number | null>;
  pds2: Array<number | null>;
  ptot: Array<number | null>;
  /** Magnitude of the complex corrected cross spectrum. */
  cs: Array<number | null>;
  /** Signed cospectrum (real part of the complex cross spectrum). */
  cs_real: Array<number | null>;
  n_segments: number;
  dt: number;
  segment_size: number;
  norm: string;
  smoothing_length: number;
  is_compliant: boolean;
  fad_delta: number;
  warnings: string[];
}

// API functions
export const deadtimeApi = {
  /**
   * Model-based dead-time correction of an averaged power spectrum
   * (Zhang+95 correction). Normalization is hard-locked to Leahy server-side.
   */
  async pdsCorrection(params: {
    event_list_name: string;
    selection?: EventSelection | null;
    dt: number;
    segment_size: number;
    dead_time: number;
    background_rate?: number;
    limit_k?: number;
  }): Promise<ApiResponse<PdsCorrectionData>> {
    return apiClient.post('/api/deadtime/pds-correction', {
      event_list_name: params.event_list_name,
      selection: params.selection ?? undefined,
      dt: params.dt,
      segment_size: params.segment_size,
      dead_time: params.dead_time,
      background_rate: params.background_rate ?? 0,
      limit_k: params.limit_k ?? 200,
    });
  },

  /**
   * Frequency-Amplitude-Determined (FAD) dead-time correction between two
   * independent, simultaneous event lists (different detectors).
   */
  async fadCorrection(params: {
    event_list_1_name: string;
    event_list_2_name: string;
    selection_1?: EventSelection | null;
    selection_2?: EventSelection | null;
    dt: number;
    segment_size: number;
    norm?: string;
    smoothing_length?: number | null;
  }): Promise<ApiResponse<FadCorrectionData>> {
    return apiClient.post('/api/deadtime/fad-correction', {
      event_list_1_name: params.event_list_1_name,
      event_list_2_name: params.event_list_2_name,
      selection_1: params.selection_1 ?? undefined,
      selection_2: params.selection_2 ?? undefined,
      dt: params.dt,
      segment_size: params.segment_size,
      norm: params.norm ?? 'frac',
      smoothing_length: params.smoothing_length ?? null,
    });
  },
};

export default deadtimeApi;
