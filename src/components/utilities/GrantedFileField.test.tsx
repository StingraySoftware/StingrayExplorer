import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GrantedFileField, { GrantedFileSelection } from './GrantedFileField';
import { publishBackendEpoch } from '@/api/backendEpoch';

describe('GrantedFileField', () => {
  const originalElectronApi = window.electronAPI;

  afterEach(() => {
    publishBackendEpoch(null, true);
    vi.restoreAllMocks();
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: originalElectronApi,
    });
  });

  it('returns a native-dialog selection and never exposes a typed path', async () => {
    const selected = { path: '/data/response.rmf', grant: 'token' };
    const openGrantedFile = vi.fn().mockResolvedValue([selected]);
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { openGrantedFile },
    });
    const onChange = vi.fn();
    render(<GrantedFileField label="RMF file" value={null} onChange={onChange} />);
    expect(screen.getByLabelText('RMF file')).toHaveAttribute('readonly');
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    expect(onChange).toHaveBeenCalledWith(selected);
  });

  it('preserves the current explicit selection when the dialog is cancelled', async () => {
    const current: GrantedFileSelection = { path: '/data/current.fits', grant: 'old' };
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { openGrantedFile: vi.fn().mockResolvedValue(null) },
    });
    const onChange = vi.fn();
    render(<GrantedFileField label="FITS file" value={current} onChange={onChange} />);
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByLabelText('FITS file')).toHaveValue('/data/current.fits');
  });

  it('shows native dialog failures without replacing the current selection', async () => {
    const current: GrantedFileSelection = { path: '/data/current.fits', grant: 'old' };
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { openGrantedFile: vi.fn().mockRejectedValue(new Error('dialog process failed')) },
    });
    const onChange = vi.fn();
    render(<GrantedFileField label="FITS file" value={current} onChange={onChange} />);

    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));

    expect(await screen.findByText(/dialog process failed/)).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByLabelText('FITS file')).toHaveValue('/data/current.fits');
  });

  it('ignores a native selection returned after a backend replacement', async () => {
    publishBackendEpoch(1, true);
    let complete!: (selections: GrantedFileSelection[]) => void;
    const pending = new Promise<GrantedFileSelection[]>((resolve) => { complete = resolve; });
    Object.defineProperty(window, 'electronAPI', {
      configurable: true, value: { openGrantedFile: vi.fn().mockReturnValue(pending) },
    });
    const onChange = vi.fn();
    render(<GrantedFileField label="FITS file" value={null} onChange={onChange} />);
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    publishBackendEpoch(2, true);
    await act(async () => { complete([{ path: '/data/old.fits', grant: 'old' }]); await pending; });
    expect(onChange).not.toHaveBeenCalled();
  });

  it('does not let an older dialog overwrite a newer choice or surface its error', async () => {
    let failOld!: (error: Error) => void;
    const old = new Promise<GrantedFileSelection[]>((_resolve, reject) => { failOld = reject; });
    const current = { path: '/data/current.fits', grant: 'current' };
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { openGrantedFile: vi.fn().mockReturnValueOnce(old).mockResolvedValueOnce([current]) },
    });
    const onChange = vi.fn();
    render(<GrantedFileField label="FITS file" value={null} onChange={onChange} />);
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    expect(onChange).toHaveBeenCalledWith(current);
    await act(async () => { failOld(new Error('obsolete dialog failure')); await old.catch(() => undefined); });
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/obsolete dialog failure/)).not.toBeInTheDocument();
  });
});
