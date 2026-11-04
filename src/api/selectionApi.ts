/**
 * Photon selections shared by every analysis endpoint, their live preview,
 * and derived EventLists (filtered, joined, sorted, dead-time-applied).
 */

import { apiClient, ApiResponse } from './client';

/** Half-open [low, high) ranges, matching Stingray's get_energy_mask. */
export interface EventSelection {
  energy_range?: [number, number];
  pi_range?: [number, number];
  detector_ids?: number[];
  time_intervals?: Array<[number, number]>;
  gti?: Array<[number, number]>;
}

/** What the backend records about a selection it applied to an input. */
export interface AppliedSelection {
  energy_range_kev: [number, number] | null;
  pi_range: [number, number] | null;
  detector_ids: number[] | null;
  time_intervals: Array<[number, number]> | null;
  gti: Array<[number, number]> | null;
  parent_n_events: number;
  n_events: number;
  effective_gti: Array<[string, string]>;
}

export interface SelectionPreview {
  event_list_name: string;
  n_events: number;
  parent_n_events: number;
  energy_coverage: [number, number] | null;
  pi_coverage: [number, number] | null;
  detector_ids: number[] | null;
  exposure: number;
}

export interface EventLineageParent {
  name: string;
  dataset_id: string;
  n_events: number;
  lineage?: EventLineage;
}

export interface EventLineage {
  operation: 'filter' | 'join' | 'sort' | 'apply_deadtime' | 'rmf_pi_to_energy' | string;
  parents: EventLineageParent[];
  parameters: Record<string, unknown>;
  stingray_version: string;
}

export interface DerivedEventList {
  name: string;
  dataset_id: string;
  n_events: number;
  lineage: EventLineage;
}

export type GtiStrategy = 'infer' | 'intersection' | 'union' | 'append' | 'none';

export const selectionApi = {
  /** Count the events a selection keeps, without copying or storing anything. */
  previewSelection(
    eventListName: string,
    selection: EventSelection
  ): Promise<ApiResponse<SelectionPreview>> {
    return apiClient.post('/api/data/selection-preview', {
      event_list_name: eventListName,
      selection,
    });
  },

  deriveFiltered(params: {
    event_list_name: string;
    selection: EventSelection;
    output_name: string;
  }): Promise<ApiResponse<DerivedEventList>> {
    return apiClient.post('/api/data/derived/filter', params);
  },

  deriveJoined(params: {
    event_list_names: string[];
    gti_strategy: GtiStrategy;
    output_name: string;
  }): Promise<ApiResponse<DerivedEventList>> {
    return apiClient.post('/api/data/derived/join', params);
  },

  deriveSorted(params: {
    event_list_name: string;
    output_name: string;
  }): Promise<ApiResponse<DerivedEventList>> {
    return apiClient.post('/api/data/derived/sort', params);
  },

  deriveDeadtime(params: {
    event_list_name: string;
    dead_time: number;
    paralyzable: boolean;
    dt_sigma?: number | null;
    output_name: string;
  }): Promise<ApiResponse<DerivedEventList>> {
    return apiClient.post('/api/data/derived/deadtime', params);
  },
};
