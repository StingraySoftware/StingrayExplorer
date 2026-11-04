import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/testUtils';
import { useUIStore } from '@/store/uiStore';
import { BackendContext } from '@/context/BackendContext';
import { publishBackendEpoch } from '@/api/backendEpoch';
import type {
  ExportableObject,
  ExportableObjectsResult,
  FileInspectionResult,
  RmfInspectionResult,
} from '@/api/ioApi';

const inspectFile = vi.fn();
const inspectRmf = vi.fn();
const convertPi = vi.fn();
const convertEventList = vi.fn();
const listExportableObjects = vi.fn();
const exportObject = vi.fn();
const listEventLists = vi.fn();

vi.mock('@/api/ioApi', () => ({
  ioApi: {
    inspectFile: (...args: unknown[]) => inspectFile(...args),
    inspectRmf: (...args: unknown[]) => inspectRmf(...args),
    convertPi: (...args: unknown[]) => convertPi(...args),
    convertEventList: (...args: unknown[]) => convertEventList(...args),
    listExportableObjects: (...args: unknown[]) => listExportableObjects(...args),
    exportObject: (...args: unknown[]) => exportObject(...args),
  },
}));

vi.mock('@/api/dataApi', () => ({
  dataApi: { listEventLists: (...args: unknown[]) => listEventLists(...args) },
}));

vi.mock('@/components/plots/PlotlyChart', () => ({
  default: () => <div data-testid="io-chart" />,
}));

import IOPage from './index';

const CAPABILITIES: ExportableObjectsResult['capability_matrix'] = {
  spectrum: {
    csv: { supported: true, notes: 'Numeric spectrum columns only; metadata is not preserved.' },
    ecsv: { supported: true, notes: 'Spectrum columns and original input metadata.' },
    json: { supported: true, notes: 'Spectrum envelope with identity and provenance.' },
    fits: { supported: true, notes: 'Generic spectrum table with metadata.' },
    hdf5: { supported: false, notes: 'HDF5 unavailable.', reason: 'h5py unavailable.' },
  },
  event_list: {
    csv: { supported: true, notes: 'Tabular only' },
    ecsv: { supported: true, notes: 'Metadata' },
    json: { supported: true, notes: 'Envelope' },
    fits: { supported: true, notes: 'Generic FITS with GTI' },
    hdf5: {
      supported: false,
      notes: 'Optional HDF5 support is unavailable.',
      reason: 'HDF5 dependency h5py is not installed.',
      extensions: ['.hdf5'],
      dependency: { name: 'h5py', available: false, version: null },
    },
  },
  lightcurve: {
    csv: { supported: true, notes: 'Tabular only' },
    ecsv: { supported: true, notes: 'Metadata' },
    json: { supported: true, notes: 'Envelope' },
    fits: { supported: true, notes: 'Generic FITS' },
    hdf5: {
      supported: false,
      notes: 'Optional HDF5 support is unavailable.',
      reason: 'HDF5 dependency h5py is not installed.',
      extensions: ['.hdf5'],
      dependency: { name: 'h5py', available: false, version: null },
    },
  },
  analysis_result: {
    csv: { supported: true, notes: 'Tabular only' },
    ecsv: { supported: true, notes: 'Metadata' },
    json: { supported: true, notes: 'Envelope' },
    fits: { supported: true, notes: 'Generic FITS' },
    hdf5: {
      supported: false,
      notes: 'Optional HDF5 support is unavailable.',
      reason: 'HDF5 dependency h5py is not installed.',
      extensions: ['.hdf5'],
      dependency: { name: 'h5py', available: false, version: null },
    },
  },
};

const HDF5_CAPABILITIES: ExportableObjectsResult['capability_matrix'] = {
  spectrum: CAPABILITIES.spectrum,
  event_list: {
    ...CAPABILITIES.event_list,
    hdf5: {
      supported: true,
      notes: 'Lossless Stingray Explorer schema with semantic reopen verification.',
      reason: null,
      extensions: ['.hdf5'],
      dependency: { name: 'h5py', available: true, version: '3.15.1' },
    },
  },
  lightcurve: {
    ...CAPABILITIES.lightcurve,
    hdf5: {
      supported: true,
      notes: 'Lossless Stingray Explorer schema with semantic reopen verification.',
      reason: null,
      extensions: ['.hdf5'],
      dependency: { name: 'h5py', available: true, version: '3.15.1' },
    },
  },
  analysis_result: {
    ...CAPABILITIES.analysis_result,
    hdf5: {
      supported: true,
      notes: 'Lossless Stingray Explorer schema with semantic reopen verification.',
      reason: null,
      extensions: ['.hdf5'],
      dependency: { name: 'h5py', available: true, version: '3.15.1' },
    },
  },
};

function spectrumObject(resultId: string, name = 'power'): ExportableObject {
  return {
    object_type: 'spectrum',
    name,
    row_count: 3,
    exportable: true,
    formats: ['ecsv'],
    reason: null,
    result_id: resultId,
    backend_session_id: 'session-one',
  };
}

function catalog(
  objects: ExportableObjectsResult['objects'] = []
): ExportableObjectsResult {
  return {
    objects,
    capability_matrix: CAPABILITIES,
    format_allowlist: ['csv', 'ecsv', 'json', 'fits'],
    excluded_formats: {
      pickle: 'Unsafe deserialization format',
      hdf5: 'HDF5 dependency h5py is not installed.',
    },
    row_cap: 2_000_000,
    provenance: { operation: 'list_exportable_objects' },
  };
}

function catalogWithHdf5(
  objects: ExportableObjectsResult['objects'] = []
): ExportableObjectsResult {
  return {
    ...catalog(objects),
    capability_matrix: HDF5_CAPABILITIES,
    format_allowlist: ['csv', 'ecsv', 'json', 'fits', 'hdf5'],
    excluded_formats: { pickle: 'Unsafe deserialization format' },
  };
}

function success<T>(data: T, message = 'Done') {
  return { success: true, data, message, error: null };
}

const INSPECTION: FileInspectionResult = {
  path: '/science/events.fits',
  filename: 'events.fits',
  extension: '.fits',
  size_bytes: 4096,
  supported: true,
  detected_type: 'fits',
  hdus: [
    {
      index: 1,
      name: 'EVENTS',
      type: 'binary_table',
      row_count: 2,
      dimensions: [16, 2],
      columns: [
        { name: 'TIME', format: 'D', unit: 's' },
        { name: 'PI', format: 'J', unit: null },
      ],
      timing: {
        status: 'available',
        note: 'Exact split keyword reference',
        mjdref: {
          decimal: '58000.12345678901234568',
          stingray_value: '58000.12345678901235',
          source_keywords: { MJDREFI: '58000', MJDREFF: '0.12345678901234568' },
        },
        keywords: {
          MJDREFI: 58000,
          MJDREFF: 0.12345678901234568,
          TIMESYS: 'TT',
          TIMEUNIT: 's',
          TIMEZERO: 0,
          TSTART: 12.5,
          TSTOP: 42.5,
          CLOCKAPP: true,
        },
        high_precision_keywords: {
          TSTART: {
            decimal: '12.500000000000000001',
            stingray_value: '12.5',
            source_keywords: {
              TSTARTI: '12',
              TSTARTF: '0.500000000000000001',
            },
          },
        },
      },
    },
  ],
  warnings: [],
  provenance: { operation: 'inspect_file' },
};

const UNITLESS_RMF_INSPECTION: RmfInspectionResult = {
  path: '/calibration/unitless.rmf',
  filename: 'unitless.rmf',
  size_bytes: 2048,
  channel_count: 2,
  channel_min: 0,
  channel_max: 1,
  energy_min: 0.1,
  energy_max: 0.4,
  energy_unit: null,
  conversion_supported: false,
  contiguous_channels: true,
  preview_rows: [
    { channel: 0, energy_min: 0.1, energy_max: 0.2, energy_midpoint: 0.15 },
  ],
  preview_truncated: true,
  warnings: ['EBOUNDS energy units are missing.'],
  provenance: { operation: 'inspect_rmf' },
};

describe('General I/O Utilities page', () => {
  const originalElectronApi = window.electronAPI;

  beforeEach(() => {
    vi.clearAllMocks();
    useUIStore.setState({ notifications: [], unreadNotificationCount: 0 });
    listExportableObjects.mockResolvedValue(success(catalog()));
    listEventLists.mockResolvedValue(
      success([
        { name: 'events', n_events: 3, time_range: [0, 2], has_pi: true },
        { name: 'already_loaded', n_events: 2, time_range: [0, 1], has_pi: true },
      ])
    );
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: originalElectronApi,
    });
  });

  afterEach(() => {
    publishBackendEpoch(null, true);
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: originalElectronApi,
    });
  });

  it('is ready and presents the verified capability matrix even with no loaded objects', async () => {
    renderWithProviders(<IOPage />);

    expect(screen.getByRole('heading', { name: 'General I/O Functionality' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Data Ingestion' })).toHaveAttribute(
      'href',
      '/data-ingestion'
    );
    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));

    expect(await screen.findByText('No compatible loaded objects are available to export.')).toBeInTheDocument();
    expect(screen.getByText('Verified format compatibility')).toBeInTheDocument();
    expect(screen.getAllByText(/Supported — Tabular only/).length).toBeGreaterThan(0);
    expect(screen.getByText(/PICKLE: Unsafe deserialization format/)).toBeInTheDocument();
    expect(screen.getByText('HDF5 dependency h5py is not installed.')).toBeInTheDocument();
  });

  it('does not offer HDF5 when the backend reports the capability as unavailable', async () => {
    listExportableObjects.mockResolvedValue(
      success(
        catalog([
          {
            object_type: 'event_list',
            name: 'events',
            row_count: 3,
            exportable: true,
            formats: ['fits', 'hdf5'],
            reason: null,
          },
        ])
      )
    );
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await screen.findByLabelText('Loaded object');

    await userEvent.click(screen.getByLabelText('Format'));
    expect(screen.getByRole('option', { name: 'FITS' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'HDF5' })).not.toBeInTheDocument();
    expect(screen.getByText('HDF5 dependency h5py is not installed.')).toBeInTheDocument();
  });

  it('preserves a native file selection on cancellation and sends the exact inspection payload', async () => {
    const openGrantedFile = vi
      .fn()
      .mockResolvedValueOnce([{ path: '/science/events.fits', grant: 'read-grant' }])
      .mockResolvedValueOnce(null);
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { ...originalElectronApi, openGrantedFile },
    });
    inspectFile.mockResolvedValue(success(INSPECTION));
    renderWithProviders(<IOPage />);

    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    expect(openGrantedFile).toHaveBeenNthCalledWith(1, {
      title: 'Scientific file',
      filters: undefined,
    });
    expect(screen.getByLabelText('Scientific file')).toHaveValue('/science/events.fits');
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    expect(screen.getByLabelText('Scientific file')).toHaveValue('/science/events.fits');

    await userEvent.click(screen.getByRole('button', { name: 'Inspect file' }));
    expect(inspectFile).toHaveBeenCalledWith({
      file_path: '/science/events.fits',
      file_grant: 'read-grant',
    });
    expect(await screen.findByText('58000.12345678901234568')).toBeInTheDocument();
    expect(screen.getByText('58000.12345678901235')).toBeInTheDocument();
    expect(screen.getAllByText(/TSTART=12\.5/).length).toBeGreaterThan(0);
    expect(screen.getByText(/CLOCKAPP=true/)).toBeInTheDocument();
    expect(screen.getByText(/TSTART=12.500000000000000001/)).toBeInTheDocument();
    expect(screen.getAllByText('EVENTS').length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole('tab', { name: 'RMF utilities' }));
    await userEvent.click(screen.getByRole('tab', { name: 'File inspector' }));
    expect(screen.getByText('58000.12345678901234568')).toBeVisible();
  });

  it('recognizes exact non-MJD timing metadata as available for display', async () => {
    const openGrantedFile = vi.fn().mockResolvedValue([
      { path: '/science/timing-only.fits', grant: 'read-grant' },
    ]);
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { ...originalElectronApi, openGrantedFile },
    });
    inspectFile.mockResolvedValue(
      success({
        ...INSPECTION,
        path: '/science/timing-only.fits',
        hdus: INSPECTION.hdus.map((hdu) => ({
          ...hdu,
          timing: {
            ...hdu.timing,
            status: 'missing' as const,
            mjdref: null,
            keywords: { TSTART: 12.5, TSTOP: 42.5, TIMEUNIT: 's' },
          },
        })),
      })
    );
    renderWithProviders(<IOPage />);

    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    await userEvent.click(screen.getByRole('button', { name: 'Inspect file' }));

    expect(await screen.findByText(/TSTART=12.500000000000000001/)).toBeInTheDocument();
    expect(
      screen.queryByText(/No unambiguous time-reference metadata was found/)
    ).not.toBeInTheDocument();
  });

  it('clears a completed file inspection when a different file is selected', async () => {
    const openGrantedFile = vi
      .fn()
      .mockResolvedValueOnce([{ path: '/science/events.fits', grant: 'first-grant' }])
      .mockResolvedValueOnce([{ path: '/science/other.fits', grant: 'second-grant' }]);
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { ...originalElectronApi, openGrantedFile },
    });
    inspectFile.mockResolvedValue(success(INSPECTION));
    renderWithProviders(<IOPage />);

    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    await userEvent.click(screen.getByRole('button', { name: 'Inspect file' }));
    expect(await screen.findByText('58000.12345678901234568')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    expect(screen.getByLabelText('Scientific file')).toHaveValue('/science/other.fits');
    expect(screen.queryByText('58000.12345678901234568')).not.toBeInTheDocument();
    expect(screen.getByText(/Choose a file to inspect/)).toBeInTheDocument();
  });

  it('does not invent keV for a unitless RMF and clears results after RMF changes', async () => {
    const openGrantedFile = vi
      .fn()
      .mockResolvedValueOnce([{ path: '/calibration/unitless.rmf', grant: 'first-grant' }])
      .mockResolvedValueOnce([{ path: '/calibration/other.rmf', grant: 'second-grant' }]);
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { ...originalElectronApi, openGrantedFile },
    });
    inspectRmf.mockResolvedValue(success(UNITLESS_RMF_INSPECTION));
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'RMF utilities' }));

    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    expect(openGrantedFile).toHaveBeenCalledWith({
      title: 'RMF file',
      filters: undefined,
    });
    await userEvent.click(screen.getByRole('button', { name: 'Inspect RMF' }));

    expect(await screen.findByText('Energy range (unit not declared)')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Energy low' })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Energy low (keV)' })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    expect(screen.getByLabelText('RMF file')).toHaveValue('/calibration/other.rmf');
    expect(screen.queryByLabelText('RMF inspection result')).not.toBeInTheDocument();
  });

  it('rejects fractional PI locally, then converts valid channels with the exact RMF payload', async () => {
    const openGrantedFile = vi
      .fn()
      .mockResolvedValueOnce([
        { path: '/calibration/response.rmf', grant: 'rmf-grant' },
      ])
      .mockResolvedValueOnce([
        { path: '/calibration/replacement.rmf', grant: 'replacement-grant' },
      ]);
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { ...originalElectronApi, openGrantedFile },
    });
    convertPi.mockResolvedValue(
      success({
        rows: [
          { index: 0, pi: 0, energy: 0.15 },
          { index: 1, pi: 2, energy: 0.6 },
        ],
        count: 2,
        energy_unit: 'keV',
        plot: { arrays: [[0, 2], [0.15, 0.6]], stride: 1, source_points: 2 },
        warnings: ['Exact EBOUNDS channel matches were required.'],
        provenance: { operation: 'rmf_pi_to_energy' },
      })
    );
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'RMF utilities' }));
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));

    const piField = screen.getByLabelText('PI values');
    await userEvent.type(piField, '0, 1.5');
    expect(screen.getByText('PI value 2 must be a non-negative integer')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Convert PI values' })).toBeDisabled();
    expect(convertPi).not.toHaveBeenCalled();

    await userEvent.clear(piField);
    await userEvent.type(piField, '0, 2');
    await userEvent.click(screen.getByRole('button', { name: 'Convert PI values' }));
    expect(convertPi).toHaveBeenCalledWith({
      pi_values: [0, 2],
      rmf_path: '/calibration/response.rmf',
      rmf_grant: 'rmf-grant',
    });
    expect(await screen.findByTestId('io-chart')).toBeInTheDocument();
    expect(screen.getByText('Exact EBOUNDS channel matches were required.')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    expect(screen.queryByTestId('io-chart')).not.toBeInTheDocument();
  });

  it('shows loading and errors while preserving the previous successful inspection', async () => {
    const openGrantedFile = vi.fn().mockResolvedValue([
      { path: '/science/events.fits', grant: 'read-grant' },
    ]);
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { ...originalElectronApi, openGrantedFile },
    });
    inspectFile.mockResolvedValueOnce(
      success({ ...INSPECTION, warnings: ['Retained inspection advisory.'] })
    );
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    await userEvent.click(screen.getByRole('button', { name: 'Inspect file' }));
    expect(await screen.findByText('58000.12345678901234568')).toBeInTheDocument();

    let resolveFailure: ((value: unknown) => void) | undefined;
    inspectFile.mockImplementationOnce(
      () => new Promise((resolve) => { resolveFailure = resolve; })
    );
    await userEvent.click(screen.getByRole('button', { name: 'Inspect file' }));
    expect(screen.getByRole('button', { name: 'Inspecting…' })).toBeDisabled();
    resolveFailure?.({
      success: false,
      data: null,
      message: 'Malformed FITS',
      error: 'Invalid header',
      warnings: ['Failure-specific FITS advisory.'],
    });

    expect(await screen.findByText('Invalid header')).toBeInTheDocument();
    expect(screen.getByText('Failure-specific FITS advisory.')).toBeInTheDocument();
    expect(screen.getByText('Retained inspection advisory.')).toBeInTheDocument();
    expect(screen.getByText('58000.12345678901234568')).toBeInTheDocument();
  });

  it('binds save-dialog extension to the selected format, preserves cancellation, and exports exactly', async () => {
    listExportableObjects.mockResolvedValue(
      success(
        catalog([
          {
            object_type: 'event_list',
            name: 'events',
            row_count: 3,
            exportable: true,
            formats: ['fits', 'csv'],
            reason: null,
          },
          {
            object_type: 'analysis_result',
            name: 'not_tabular',
            row_count: null,
            exportable: false,
            formats: [],
            reason: 'No one-dimensional columns',
          },
        ])
      )
    );
    const saveGrantedFile = vi
      .fn()
      .mockResolvedValueOnce({ path: '/exports/events.csv', grant: 'write-grant' })
      .mockResolvedValueOnce(null)
      .mockRejectedValueOnce(new Error('save dialog process failed'));
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { ...originalElectronApi, saveGrantedFile },
    });
    exportObject.mockResolvedValue(
      success({
        path: '/exports/events.csv',
        bytes: 128,
        format: 'csv',
        row_count: 3,
        object_type: 'event_list',
        object_name: 'events',
        verified: true,
        warnings: ['CSV stores tabular values only.'],
        provenance: { operation: 'export_loaded_object' },
      })
    );
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await screen.findByLabelText('Loaded object');

    await userEvent.click(screen.getByLabelText('Loaded object'));
    expect(screen.getByRole('option', { name: /not_tabular/ })).toHaveAttribute('aria-disabled', 'true');
    await userEvent.keyboard('{Escape}');
    await userEvent.click(screen.getByLabelText('Format'));
    await userEvent.click(screen.getByRole('option', { name: 'CSV' }));
    expect(screen.getByText(/CSV scientific-data behavior:/)).toBeInTheDocument();
    expect(screen.getAllByText('Tabular only').length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    expect(saveGrantedFile).toHaveBeenLastCalledWith({
      title: 'Export events',
      defaultPath: 'events.csv',
      filters: [{ name: 'CSV', extensions: ['csv'] }],
    });
    expect(screen.getByLabelText('Destination')).toHaveValue('/exports/events.csv');

    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    expect(screen.getByLabelText('Destination')).toHaveValue('/exports/events.csv');
    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    expect(await screen.findByText(/save dialog process failed/)).toBeInTheDocument();
    expect(screen.getByLabelText('Destination')).toHaveValue('/exports/events.csv');
    await userEvent.click(screen.getByRole('button', { name: 'Export' }));
    expect(exportObject).toHaveBeenCalledWith({
      object_type: 'event_list',
      object_name: 'events',
      format: 'csv',
      destination_path: '/exports/events.csv',
      destination_grant: 'write-grant',
    });
    expect(await screen.findByText('Reopened / verified')).toBeInTheDocument();

    await userEvent.click(screen.getByLabelText('Format'));
    await userEvent.click(screen.getByRole('option', { name: 'FITS' }));
    expect(screen.getByLabelText('Destination')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Export' })).toBeDisabled();
  });

  it('exports a spectrum with its selected result identity and generic semantic verification', async () => {
    listExportableObjects.mockResolvedValue(success(catalog([
      spectrumObject('result-original', 'cross'),
      {
        object_type: 'spectrum',
        name: 'dynamic',
        row_count: null,
        exportable: false,
        formats: [],
        reason: 'Two-dimensional dynamical spectra require a different export schema.',
      },
    ])));
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: {
        ...originalElectronApi,
        saveGrantedFile: vi.fn().mockResolvedValue({
          path: '/exports/cross.ecsv',
          grant: 'write-grant',
        }),
      },
    });
    exportObject.mockResolvedValue(success({
      path: '/exports/cross.ecsv',
      bytes: 512,
      format: 'ecsv',
      row_count: 3,
      object_type: 'spectrum',
      object_name: 'cross',
      verified: true,
      warnings: [],
      verification: {
        schema: 'stingray-explorer.spectrum-export.v1',
        semantic_round_trip: true,
        checks: ['Complex components and original inputs match.'],
        format: 'ecsv',
        metadata_preserved: true,
      },
      provenance: { operation: 'export_loaded_object' },
    }));
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await screen.findByLabelText('Loaded object');
    await userEvent.click(screen.getByLabelText('Loaded object'));
    expect(screen.getByRole('option', { name: /dynamic/ })).toHaveAttribute('aria-disabled', 'true');
    await userEvent.keyboard('{Escape}');
    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    await userEvent.click(screen.getByRole('button', { name: 'Export' }));
    expect(exportObject).toHaveBeenCalledWith({
      object_type: 'spectrum',
      object_name: 'cross',
      expected_result_id: 'result-original',
      format: 'ecsv',
      destination_path: '/exports/cross.ecsv',
      destination_grant: 'write-grant',
    });
    expect(await screen.findByText('Complex components and original inputs match.')).toBeInTheDocument();
    expect(screen.queryByText('h5py version')).not.toBeInTheDocument();
  });

  it.each(['spectrum', 'lightcurve'] as const)(
    'requires a fresh native destination when a same-named %s is replaced', async (objectType) => {
    const original = { ...spectrumObject('result-one'), object_type: objectType };
    listExportableObjects.mockResolvedValueOnce(success(catalog([original])))
      .mockResolvedValue(success(catalog([{ ...original, result_id: 'result-two' }])));
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: {
        ...originalElectronApi,
        saveGrantedFile: vi.fn().mockResolvedValue({
          path: '/exports/power.ecsv',
          grant: 'original-grant',
        }),
      },
    });
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await screen.findByLabelText('Loaded object');
    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    expect(screen.getByLabelText('Destination')).toHaveValue('/exports/power.ecsv');
    await userEvent.click(screen.getByRole('button', { name: 'Refresh' }));
    await waitFor(() => expect(listExportableObjects).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByLabelText('Destination')).toHaveValue(''));
    expect(screen.getByRole('button', { name: 'Export' })).toBeDisabled();
  });

  it('binds an identified light curve export to its original result ID', async () => {
    listExportableObjects.mockResolvedValue(success(catalog([
      { ...spectrumObject('lightcurve-result', 'curve'), object_type: 'lightcurve' },
    ])));
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: {
        ...originalElectronApi,
        saveGrantedFile: vi.fn().mockResolvedValue({
          path: '/exports/curve.ecsv', grant: 'curve-grant',
        }),
      },
    });
    exportObject.mockResolvedValue(success({
      path: '/exports/curve.ecsv', bytes: 256, format: 'ecsv', row_count: 3,
      object_type: 'lightcurve', object_name: 'curve', result_id: 'lightcurve-result',
      verified: true, warnings: [], provenance: { operation: 'export_loaded_object' },
    }));
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await screen.findByText('Source result: lightcurve-result');
    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    await userEvent.click(screen.getByRole('button', { name: 'Export' }));
    expect(exportObject).toHaveBeenCalledWith({
      object_type: 'lightcurve', object_name: 'curve', expected_result_id: 'lightcurve-result',
      format: 'ecsv', destination_path: '/exports/curve.ecsv', destination_grant: 'curve-grant',
    });
  });

  it('ignores a native save-dialog completion for a replaced spectrum', async () => {
    const original = spectrumObject('result-one');
    listExportableObjects.mockResolvedValueOnce(success(catalog([original])))
      .mockResolvedValue(success(catalog([{ ...original, result_id: 'result-two' }])));
    let finishDialog: ((value: { path: string; grant: string }) => void) | undefined;
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: {
        ...originalElectronApi,
        saveGrantedFile: vi.fn().mockImplementation(() => new Promise((resolve) => {
          finishDialog = resolve;
        })),
      },
    });
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await screen.findByLabelText('Loaded object');
    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    await userEvent.click(screen.getByRole('button', { name: 'Refresh' }));
    await waitFor(() => expect(listExportableObjects).toHaveBeenCalledTimes(2));
    await screen.findByText('Spectrum result: result-two');
    await act(async () => {
      finishDialog?.({ path: '/exports/old-power.ecsv', grant: 'old-grant' });
      await Promise.resolve();
    });
    expect(screen.getByLabelText('Destination')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Export' })).toBeDisabled();
  });

  it('invalidates catalogs and native grants immediately when the backend generation changes', async () => {
    listExportableObjects.mockResolvedValue(success(catalog([spectrumObject('result-one')])));
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: {
        ...originalElectronApi,
        saveGrantedFile: vi.fn().mockResolvedValue({
          path: '/exports/power.ecsv',
          grant: 'old-grant',
        }),
      },
    });
    const ready = {
      generation: 1,
      phase: 'ready' as const,
      port: 51001,
      isReady: true,
      error: null,
    };
    const view = renderWithProviders(
      <BackendContext.Provider value={ready}><IOPage /></BackendContext.Provider>
    );
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await screen.findByLabelText('Loaded object');
    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    expect(screen.getByRole('button', { name: 'Export' })).toBeEnabled();
    view.rerender(
      <BackendContext.Provider
        value={{ ...ready, generation: 2, phase: 'starting', port: null, isReady: false }}
      >
        <IOPage />
      </BackendContext.Provider>
    );
    expect(screen.queryByLabelText('Loaded object')).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue('/exports/power.ecsv')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Export' })).not.toBeInTheDocument();
  });

  it('keeps the newest destination when same-selection dialogs complete out of order', async () => {
    listExportableObjects.mockResolvedValue(success(catalog([spectrumObject('result-one')])));
    type Destination = { path: string; grant: string };
    let finishOlder: ((selection: Destination) => void) | undefined;
    let finishNewer: ((selection: Destination) => void) | undefined;
    const saveGrantedFile = vi.fn()
      .mockImplementationOnce(() => new Promise((resolve) => { finishOlder = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { finishNewer = resolve; }));
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { ...originalElectronApi, saveGrantedFile },
    });
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await screen.findByLabelText('Loaded object');
    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    await act(async () => {
      finishNewer?.({ path: '/exports/newer.ecsv', grant: 'newer-grant' });
      await Promise.resolve();
    });
    expect(screen.getByLabelText('Destination')).toHaveValue('/exports/newer.ecsv');
    await act(async () => {
      finishOlder?.({ path: '/exports/older.ecsv', grant: 'older-grant' });
      await Promise.resolve();
    });
    expect(screen.getByLabelText('Destination')).toHaveValue('/exports/newer.ecsv');
  });

  it('ignores a catalog response from the previous backend generation', async () => {
    const spectrum = { ...spectrumObject('new-result', 'new_power'), backend_session_id: 'session-two' };
    let finishOldCatalog: ((value: unknown) => void) | undefined;
    listExportableObjects.mockImplementationOnce(() => new Promise((resolve) => {
      finishOldCatalog = resolve;
    })).mockResolvedValue(success(catalog([spectrum])));
    const ready = {
      generation: 1,
      phase: 'ready' as const,
      port: 51001,
      isReady: true,
      error: null,
    };
    const view = renderWithProviders(
      <BackendContext.Provider value={ready}><IOPage /></BackendContext.Provider>
    );
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await waitFor(() => expect(listExportableObjects).toHaveBeenCalledTimes(1));
    view.rerender(
      <BackendContext.Provider value={{ ...ready, generation: 2, port: 51002 }}>
        <IOPage />
      </BackendContext.Provider>
    );
    await screen.findByText('Spectrum result: new-result');
    await act(async () => {
      finishOldCatalog?.(success(catalog([{
        ...spectrum,
        name: 'old_power',
        result_id: 'old-result',
        backend_session_id: 'session-one',
      }])));
      await Promise.resolve();
    });
    expect(screen.getByText('Spectrum result: new-result')).toBeInTheDocument();
    expect(screen.queryByText('Spectrum result: old-result')).not.toBeInTheDocument();
  });

  it('rejects a file-dialog completion after an epoch change before React rerenders', async () => {
    let finishDialog: ((selection: Array<{ path: string; grant: string }>) => void) | undefined;
    const openGrantedFile = vi.fn()
      .mockResolvedValueOnce([{ path: '/science/events.fits', grant: 'first-grant' }])
      .mockImplementationOnce(() => new Promise((resolve) => { finishDialog = resolve; }));
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { ...originalElectronApi, openGrantedFile },
    });
    inspectFile.mockResolvedValue(success(INSPECTION));
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    await userEvent.click(screen.getByRole('button', { name: 'Inspect file' }));
    await screen.findByText('58000.12345678901234568');
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    await act(async () => {
      publishBackendEpoch(9, false);
      finishDialog?.([{ path: '/science/stale.fits', grant: 'stale-grant' }]);
      await Promise.resolve();
    });
    expect(screen.getByLabelText('Scientific file')).toHaveValue('/science/events.fits');
    expect(screen.getByText('58000.12345678901234568')).toBeInTheDocument();
  });

  it('offers only capability-advertised HDF5 with an exact .hdf5 destination and verification record', async () => {
    listExportableObjects.mockResolvedValue(
      success(
        catalogWithHdf5([
          {
            object_type: 'event_list',
            name: 'events',
            row_count: 3,
            exportable: true,
            formats: ['fits', 'hdf5'],
            reason: null,
          },
        ])
      )
    );
    const saveGrantedFile = vi.fn().mockResolvedValue({
      path: '/exports/events.hdf5',
      grant: 'hdf5-write-grant',
    });
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { ...originalElectronApi, saveGrantedFile },
    });
    exportObject.mockResolvedValueOnce(
      success({
        path: '/exports/events.hdf5',
        bytes: 4096,
        format: 'hdf5',
        row_count: 3,
        object_type: 'event_list',
        object_name: 'events',
        verified: true,
        verification: {
          schema: 'stingray-explorer.hdf5.v1',
          table_path: 'stingray_explorer/table',
          semantic_round_trip: true,
          checks: ['Column order, dtypes, units, and masks match.', 'Explicit GTI state matches.'],
          h5py_version: '3.15.1',
        },
        warnings: ['HDF5 was reopened before publication.'],
        provenance: { operation: 'export_loaded_object', schema: 'stingray-explorer.hdf5.v1' },
      })
    );

    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await screen.findByLabelText('Loaded object');
    expect(screen.queryByText(/HDF5 unavailable:/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByLabelText('Format'));
    await userEvent.click(screen.getByRole('option', { name: 'HDF5' }));
    expect(screen.getByText(/HDF5 scientific-data behavior:/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    expect(saveGrantedFile).toHaveBeenCalledWith({
      title: 'Export events',
      defaultPath: 'events.hdf5',
      filters: [{ name: 'HDF5', extensions: ['hdf5'] }],
    });

    await userEvent.click(screen.getByRole('button', { name: 'Export' }));
    expect(exportObject).toHaveBeenCalledWith({
      object_type: 'event_list',
      object_name: 'events',
      format: 'hdf5',
      destination_path: '/exports/events.hdf5',
      destination_grant: 'hdf5-write-grant',
    });
    expect(await screen.findByLabelText('Export verification metadata')).toBeInTheDocument();
    expect(screen.getByText('stingray-explorer.hdf5.v1')).toBeInTheDocument();
    expect(screen.getByText('stingray_explorer/table')).toBeInTheDocument();
    expect(screen.getByText('Explicit GTI state matches.')).toBeInTheDocument();
    expect(screen.getByText('HDF5 was reopened before publication.')).toBeInTheDocument();
  });

  it('shows the exact per-object reason when HDF5 cannot represent a loaded object losslessly', async () => {
    const unsupportedReason =
      "Column 'cross' has complex values that the verified HDF5 schema does not support.";
    listExportableObjects.mockResolvedValue(
      success(
        catalogWithHdf5([
          {
            object_type: 'analysis_result',
            name: 'cross_spectrum',
            row_count: 2,
            exportable: true,
            formats: ['fits'],
            format_reasons: { hdf5: unsupportedReason },
            reason: null,
          },
        ])
      )
    );

    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await screen.findByLabelText('Loaded object');
    expect(screen.getByText(unsupportedReason)).toBeInTheDocument();

    await userEvent.click(screen.getByLabelText('Format'));
    expect(screen.getByRole('option', { name: 'FITS' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'HDF5' })).not.toBeInTheDocument();
  });

  it('keeps the last successful HDF5 result visible when a later export fails', async () => {
    listExportableObjects.mockResolvedValue(
      success(
        catalogWithHdf5([
          {
            object_type: 'analysis_result',
            name: 'periodogram',
            row_count: 2,
            exportable: true,
            formats: ['hdf5'],
            reason: null,
          },
        ])
      )
    );
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: {
        ...originalElectronApi,
        saveGrantedFile: vi.fn().mockResolvedValue({
          path: '/exports/periodogram.hdf5',
          grant: 'analysis-write-grant',
        }),
      },
    });
    exportObject
      .mockResolvedValueOnce(
        success({
          path: '/exports/periodogram.hdf5',
          bytes: 2048,
          format: 'hdf5',
          row_count: 2,
          object_type: 'analysis_result',
          object_name: 'periodogram',
          verified: true,
          verification: {
            schema: 'stingray-explorer.hdf5.v1',
            table_path: 'stingray_explorer/table',
            semantic_round_trip: true,
            checks: ['Analysis metadata matches.'],
            h5py_version: '3.15.1',
          },
          warnings: ['Successful export advisory.'],
          provenance: { operation: 'export_loaded_object' },
        })
      )
      .mockResolvedValueOnce({
        success: false,
        data: null,
        message: 'HDF5 verification failed',
        error: 'Reopened units did not match',
        warnings: ['Failed artifact was removed before publication.'],
      });

    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'Export / conversion' }));
    await screen.findByLabelText('Loaded object');
    await userEvent.click(screen.getByRole('button', { name: 'Choose destination' }));
    await userEvent.click(screen.getByRole('button', { name: 'Export' }));
    expect(await screen.findByText('Analysis metadata matches.')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Export' }));
    expect(await screen.findByText('Reopened units did not match')).toBeInTheDocument();
    expect(screen.getByText('Failed artifact was removed before publication.')).toBeInTheDocument();
    expect(screen.getByText('Successful export advisory.')).toBeInTheDocument();
    expect(screen.getByText('Analysis metadata matches.')).toBeInTheDocument();
  });

  it('requires a unique derived name and sends an explicit save-as conversion', async () => {
    const initialObjects: ExportableObjectsResult['objects'] = [
      {
        object_type: 'event_list',
        name: 'events',
        row_count: 3,
        exportable: true,
        formats: ['fits', 'csv'],
        reason: null,
      },
      {
        object_type: 'event_list',
        name: 'already_loaded',
        row_count: 2,
        exportable: true,
        formats: ['fits'],
        reason: null,
      },
    ];
    listExportableObjects
      .mockResolvedValueOnce(success(catalog(initialObjects)))
      .mockResolvedValue(
        success(
          catalog([
            ...initialObjects,
            {
              object_type: 'event_list',
              name: 'events_calibrated',
              row_count: 3,
              exportable: true,
              formats: ['fits', 'csv'],
              reason: null,
            },
          ])
        )
      );
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: {
        ...originalElectronApi,
        openGrantedFile: vi.fn().mockResolvedValue([
          { path: '/calibration/response.rmf', grant: 'rmf-grant' },
        ]),
      },
    });
    convertEventList
      .mockResolvedValueOnce(
        success({
          source_name: 'events',
          saved: false,
          saved_name: null,
          event_count: 3,
          energy_unit: 'keV',
          preview_rows: [{ index: 0, pi: 0, energy: 0.15 }],
          preview_truncated: true,
          plot: { arrays: [[0], [0.15]], stride: 3, source_points: 3 },
          pi_preserved: true,
          warnings: [],
          provenance: { operation: 'rmf_event_list_pi_to_energy' },
        })
      )
      .mockResolvedValueOnce(success({
        source_name: 'events',
        saved: true,
        saved_name: 'events_calibrated',
        event_count: 3,
        energy_unit: 'keV',
        preview_rows: [{ index: 0, pi: 0, energy: 0.15 }],
        preview_truncated: true,
        plot: { arrays: [[0], [0.15]], stride: 3, source_points: 3 },
        pi_preserved: true,
        warnings: [],
        provenance: { operation: 'rmf_event_list_pi_to_energy' },
      }));
    renderWithProviders(<IOPage />);
    await userEvent.click(screen.getByRole('tab', { name: 'RMF utilities' }));
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    await userEvent.click(await screen.findByLabelText('Source EventList'));
    await userEvent.click(screen.getByRole('option', { name: /events \(3 events\)/ }));

    await userEvent.click(screen.getByRole('button', { name: 'Preview conversion' }));
    expect(convertEventList).toHaveBeenLastCalledWith({
      event_list_name: 'events',
      rmf_path: '/calibration/response.rmf',
      rmf_grant: 'rmf-grant',
      save_as: null,
    });
    expect(await screen.findByText(/no object was saved and the source was not modified/)).toBeInTheDocument();

    const saveAs = screen.getByLabelText('Save as (new EventList name)');
    await userEvent.type(saveAs, 'events');
    expect(screen.getByText('Destination name must differ from the source EventList')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Convert and save derived EventList' })).toBeDisabled();
    await userEvent.clear(saveAs);
    await userEvent.type(saveAs, 'already_loaded');
    expect(screen.getByText(/already_loaded.*already exists/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Convert and save derived EventList' })).toBeDisabled();
    await userEvent.clear(saveAs);
    await userEvent.type(saveAs, 'events_calibrated');
    await userEvent.click(screen.getByRole('button', { name: 'Convert and save derived EventList' }));

    expect(convertEventList).toHaveBeenLastCalledWith({
      event_list_name: 'events',
      rmf_path: '/calibration/response.rmf',
      rmf_grant: 'rmf-grant',
      save_as: 'events_calibrated',
    });
    expect(await screen.findByText(/Saved events_calibrated with 3 events/)).toBeInTheDocument();
    await waitFor(() => expect(listExportableObjects).toHaveBeenCalledTimes(2));
    expect(screen.getByText(/events_calibrated.*already exists/)).toBeInTheDocument();

    const saveButton = screen.getByRole('button', {
      name: 'Convert and save derived EventList',
    });
    expect(saveButton).toBeDisabled();
    fireEvent.click(saveButton);
    expect(convertEventList).toHaveBeenCalledTimes(2);
  });
});
