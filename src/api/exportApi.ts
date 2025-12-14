/**
 * API functions for data export operations
 */

import { apiClient, ApiResponse } from './client';

// Types
export interface ExportResult {
  file_path: string;
  n_rows?: number;
}

// API functions
export const exportApi = {
  /**
   * Export an EventList to CSV file
   */
  async exportEventListToCsv(params: {
    name: string;
    file_path: string;
  }): Promise<ApiResponse<ExportResult>> {
    return apiClient.post('/api/export/event-list/csv', params);
  },

  /**
   * Export a Lightcurve to CSV file
   */
  async exportLightcurveToCsv(params: {
    name: string;
    file_path: string;
  }): Promise<ApiResponse<ExportResult>> {
    return apiClient.post('/api/export/lightcurve/csv', params);
  },

  /**
   * Export a spectrum to CSV file
   */
  async exportSpectrumToCsv(params: {
    name: string;
    file_path: string;
  }): Promise<ApiResponse<ExportResult>> {
    return apiClient.post('/api/export/spectrum/csv', params);
  },

  /**
   * Export a bispectrum to CSV file
   */
  async exportBispectrumToCsv(params: {
    name: string;
    file_path: string;
  }): Promise<ApiResponse<ExportResult>> {
    return apiClient.post('/api/export/bispectrum/csv', params);
  },

  /**
   * Export data to HDF5 file
   */
  async exportToHdf5(params: {
    name: string;
    file_path: string;
    data_type?: 'event_list' | 'lightcurve' | 'spectrum';
  }): Promise<ApiResponse<ExportResult>> {
    return apiClient.post('/api/export/hdf5', {
      name: params.name,
      file_path: params.file_path,
      data_type: params.data_type || 'event_list',
    });
  },

  /**
   * Export data to FITS file
   */
  async exportToFits(params: {
    name: string;
    file_path: string;
    data_type?: 'event_list';
  }): Promise<ApiResponse<ExportResult>> {
    return apiClient.post('/api/export/fits', {
      name: params.name,
      file_path: params.file_path,
      data_type: params.data_type || 'event_list',
    });
  },
};

export default exportApi;
