/**
 * API functions for EventList data operations
 */

import { apiClient, ApiResponse } from './client';

// Types
export interface EventListSummary {
  name: string;
  n_events: number;
  time_range: [number, number];
  has_energy?: boolean;
  has_pi?: boolean;
  gti_count?: number;
}

export interface EventListInfo extends EventListSummary {
  duration: number;
  mjdref: number | null;
}

export interface FileSizeInfo {
  file_size_bytes: number;
  file_size_mb: number;
  file_size_gb: number;
  risk_level: 'safe' | 'caution' | 'risky' | 'critical';
  recommend_lazy: boolean;
}

// API functions
export const dataApi = {
  /**
   * Load an EventList from a file
   */
  async loadEventList(params: {
    file_path: string;
    name: string;
    fmt?: string;
    rmf_file?: string;
    additional_columns?: string[];
  }): Promise<ApiResponse<EventListSummary>> {
    return apiClient.post('/api/data/load', {
      file_path: params.file_path,
      name: params.name,
      fmt: params.fmt || 'ogip',
      rmf_file: params.rmf_file,
      additional_columns: params.additional_columns,
    });
  },

  /**
   * Load an EventList from a URL
   */
  async loadEventListFromUrl(params: {
    url: string;
    name: string;
    fmt?: string;
  }): Promise<ApiResponse<EventListSummary>> {
    return apiClient.post('/api/data/load-url', {
      url: params.url,
      name: params.name,
      fmt: params.fmt || 'ogip',
    });
  },

  /**
   * Save an EventList to disk
   */
  async saveEventList(params: {
    name: string;
    file_path: string;
    fmt?: string;
  }): Promise<ApiResponse<{ file_path: string }>> {
    return apiClient.post('/api/data/save', {
      name: params.name,
      file_path: params.file_path,
      fmt: params.fmt || 'ogip',
    });
  },

  /**
   * Delete an EventList from state
   */
  async deleteEventList(name: string): Promise<ApiResponse<{ name: string }>> {
    return apiClient.delete(`/api/data/${name}`);
  },

  /**
   * Get information about an EventList
   */
  async getEventListInfo(name: string): Promise<ApiResponse<EventListInfo>> {
    return apiClient.get(`/api/data/${name}`);
  },

  /**
   * List all loaded EventLists
   */
  async listEventLists(): Promise<ApiResponse<EventListSummary[]>> {
    return apiClient.get('/api/data/');
  },

  /**
   * Check file size and get loading recommendations
   */
  async checkFileSize(file_path: string): Promise<ApiResponse<FileSizeInfo>> {
    return apiClient.post('/api/data/check-size', { file_path });
  },
};

export default dataApi;
