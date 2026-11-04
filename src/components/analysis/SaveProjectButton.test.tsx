import { expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/testUtils';
import { apiClient } from '@/api/client';
import { recordWorkspacePath, restoreWorkspaceSession } from '@/api/workspaceSession';
import SaveProjectButton from './SaveProjectButton';
vi.mock('@/api/client', () => ({ apiClient: { post: vi.fn() } }));
it('saves from the active analysis page with its unsent draft instead of navigating to I/O', async () => {
  restoreWorkspaceSession({ version: 1, fields: { 'draft': 'unfinished-value' } });
  recordWorkspacePath('/quicklook/power-spectrum');
  window.electronAPI = { saveGrantedFile: vi.fn().mockResolvedValue({ path: '/session.srproj', grant: 'dummy' }) } as unknown as typeof window.electronAPI;
  vi.mocked(apiClient.post).mockResolvedValue({ success: true, data: {}, error: null, message: 'Project saved' });
  renderWithProviders(<SaveProjectButton />);
  await userEvent.click(screen.getByRole('button', { name: 'Save analysis project' }));
  await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith('/api/projects/save', expect.objectContaining({
    destination_path: '/session.srproj', destination_grant: 'dummy',
    workspace: expect.objectContaining({ path: '/quicklook/power-spectrum', fields: { draft: 'unfinished-value' } }),
  })));
});
