import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '@/test/testUtils';
import { publishBackendEpoch } from '@/api/backendEpoch';

const { inspectFile, loadFromFile } = vi.hoisted(() => ({
  inspectFile: vi.fn(),
  loadFromFile: vi.fn(),
}));
vi.mock('@/api/lightcurveApi', () => ({ lightcurveApi: { inspectFile, loadFromFile } }));
import LightcurveFilePanel from './LightcurveFilePanel';

const table = (overrides = {}) => ({
  index: 1,
  name: 'RATE',
  rate_columns: ['RATE'],
  n_rows: 30,
  n_bands: 1,
  timeunit: 's',
  has_mjdref: true,
  telescope: 'NICER',
  instrument: 'XTI',
  ...overrides,
});

function chooseFile(path = '/data/ni1234_0mpu7.lc') {
  Object.defineProperty(window, 'electronAPI', {
    configurable: true,
    value: { openGrantedFile: vi.fn().mockResolvedValue([{ path, grant: 'token' }]) },
  });
  return userEvent.click(screen.getByRole('button', { name: 'Choose' }));
}

describe('LightcurveFilePanel', () => {
  const originalElectronApi = window.electronAPI;
  beforeEach(() => {
    vi.clearAllMocks();
    publishBackendEpoch(null, true);
    loadFromFile.mockResolvedValue({
      success: true,
      data: { name: 'ni1234_0mpu7' },
      message: "Loaded light curve 'ni1234_0mpu7' from ni1234_0mpu7.lc (30 bins of 1.0 s)",
      error: null,
    });
  });
  afterEach(() => {
    Object.defineProperty(window, 'electronAPI', { configurable: true, value: originalElectronApi });
  });

  it('inspects the granted file and loads its table under a suggested name', async () => {
    inspectFile.mockResolvedValue({ success: true, data: { tables: [table()] } });
    renderWithProviders(<LightcurveFilePanel />);
    await chooseFile();
    expect(inspectFile).toHaveBeenCalledWith({ file_path: '/data/ni1234_0mpu7.lc', file_grant: 'token' });
    expect(await screen.findByText(/NICER \/ XTI · HDU 1 RATE · 30 bins/)).toBeInTheDocument();
    expect(screen.getByLabelText('Store as')).toHaveValue('ni1234_0mpu7');
    expect(screen.queryByLabelText('Reference epoch MJDREF')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Load light curve' }));
    await waitFor(() =>
      expect(loadFromFile).toHaveBeenCalledWith({
        file_path: '/data/ni1234_0mpu7.lc',
        file_grant: 'token',
        output_name: 'ni1234_0mpu7',
        hdu: 1,
        rate_column: 'RATE',
      })
    );
    expect(await screen.findByText(/Loaded light curve 'ni1234_0mpu7'/)).toBeInTheDocument();
  });

  it('asks for a band and the reference epoch when the file needs them', async () => {
    inspectFile.mockResolvedValue({
      success: true,
      data: { tables: [table({ n_bands: 3, has_mjdref: false, telescope: 'eROSITA', instrument: null })] },
    });
    renderWithProviders(<LightcurveFilePanel />);
    await chooseFile('/data/erosita.fits');
    const load = await screen.findByRole('button', { name: 'Load light curve' });
    expect(load).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Reference epoch MJDREF'), '51543.875');
    await userEvent.click(screen.getByLabelText('Energy band'));
    await userEvent.click(await screen.findByRole('option', { name: 'Band 2' }));
    await userEvent.click(load);
    await waitFor(() =>
      expect(loadFromFile).toHaveBeenCalledWith(
        expect.objectContaining({ band: 2, mjdref: 51543.875, output_name: 'erosita' })
      )
    );
  });

  it('reports files without a light-curve table', async () => {
    inspectFile.mockResolvedValue({
      success: false,
      message: 'This file has no light-curve table',
      error: null,
    });
    renderWithProviders(<LightcurveFilePanel />);
    await chooseFile('/data/events.evt');
    expect(await screen.findByText('This file has no light-curve table')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Load light curve' })).not.toBeInTheDocument();
  });
});
