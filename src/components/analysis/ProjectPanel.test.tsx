import { beforeEach, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/testUtils';
import { apiClient } from '@/api/client';
import { restoreAnalyses, restoredAnalysis } from '@/api/projectResults';
import ProjectPanel from './ProjectPanel';
vi.mock('@/api/client', () => ({ apiClient: { post: vi.fn() } }));
beforeEach(() => { restoreAnalyses({}); vi.mocked(apiClient.post).mockReset(); });
it('saves a project only through the native granted destination', async () => {
  window.electronAPI = { saveGrantedFile: vi.fn().mockResolvedValue({ path: '/analysis.srproj', grant: 'test-grant' }) } as unknown as typeof window.electronAPI;
  vi.mocked(apiClient.post).mockResolvedValue({ success: true, data: {}, message: 'Project saved', error: null });
  renderWithProviders(<ProjectPanel />);
  await userEvent.click(screen.getByRole('button', { name: 'Save analysis project' }));
  expect(await screen.findByText('Project saved')).toBeInTheDocument();
  expect(apiClient.post).toHaveBeenCalledWith('/api/projects/save', { destination_path: '/analysis.srproj', destination_grant: 'test-grant', renderer: {}, workspace: expect.objectContaining({ version: 1, fields: {} }) });
});
it('reopens granted projects and makes saved result inputs available to QuickLook', async () => {
  const record = { result: { power: [2] }, resultInputs: { dt: .25 }, resultIdentity: null, warnings: [], stale: false };
  window.electronAPI = { openGrantedFile: vi.fn().mockResolvedValue([{ path: '/analysis.srproj', grant: 'test-read' }]) } as unknown as typeof window.electronAPI;
  vi.mocked(apiClient.post).mockResolvedValue({ success: true, data: { renderer: { Power: record } }, message: 'Project reopened', error: null });
  renderWithProviders(<ProjectPanel />);
  await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
  await userEvent.click(screen.getByRole('button', { name: 'Reopen analysis project' }));
  expect(await screen.findByText('Project reopened')).toBeInTheDocument();
  expect(restoredAnalysis('Power')?.resultInputs).toEqual({ dt: .25 });
});
