import { workspaceSession, restoreWorkspaceSession, WorkspaceSession } from '@/api/workspaceSession';
import { useState } from 'react';
import { Alert, Button, Stack, Typography } from '@mui/material';
import { useQueryClient } from '@tanstack/react-query';
import GrantedFileField, { GrantedFileSelection } from '@/components/utilities/GrantedFileField';
import { apiClient } from '@/api/client';
import { captureBackendEpoch, isBackendEpochCurrent } from '@/api/backendEpoch';
import { savedAnalyses, restoreAnalyses, SavedAnalysis } from '@/api/projectResults';

export default function ProjectPanel() {
  const queryClient = useQueryClient();
  const [source, setSource] = useState<GrantedFileSelection | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ error: boolean; text: string } | null>(null);
  const act = async (opening: boolean) => {
    const epoch = captureBackendEpoch();
    setBusy(true);
    setMessage(null);
    try {
      let response;
      if (opening) {
        if (!source) return;
        response = await apiClient.post<{ renderer: Record<string, SavedAnalysis>; workspace?: WorkspaceSession }>('/api/projects/open', {
          file_path: source.path, file_grant: source.grant,
        });
        if (response.success && response.data && isBackendEpochCurrent(epoch)) {
          await queryClient.invalidateQueries();
          restoreAnalyses(response.data.renderer);
          restoreWorkspaceSession(response.data.workspace);
        }
      } else {
        const destination = await window.electronAPI?.saveGrantedFile({
          title: 'Save analysis project', defaultPath: 'analysis.srproj',
          filters: [{ name: 'Stingray project', extensions: ['srproj'] }],
        });
        if (!isBackendEpochCurrent(epoch) || !destination) return;
        response = await apiClient.post('/api/projects/save', {
          destination_path: destination.path, destination_grant: destination.grant,
          renderer: savedAnalyses(),
          workspace: workspaceSession(),
        });
      }
      if (isBackendEpochCurrent(epoch)) setMessage({ error: !response.success, text: response.message || response.error || 'Project operation failed' });
    } catch (error) {
      if (isBackendEpochCurrent(epoch)) setMessage({ error: true, text: String(error) });
    } finally { setBusy(false); }
  };
  return <Stack spacing={2} sx={{ mb: 3 }}>
    <Typography variant="h6">Analysis projects</Typography>
    <Typography variant="body2">Save loaded data, calculation settings, results and provenance in a self-contained project. Reopen into an empty backend, or a workspace with no conflicting object names. Existing files are never overwritten.</Typography>
    <Button disabled={busy} onClick={() => void act(false)}>Save analysis project</Button>
    <GrantedFileField label="Analysis project" value={source} onChange={setSource} disabled={busy} filters={[{ name: 'Stingray project', extensions: ['srproj'] }]} />
    <Button disabled={busy || !source} onClick={() => void act(true)}>Reopen analysis project</Button>
    {message && <Alert severity={message.error ? 'error' : 'success'}>{message.text}</Alert>}
  </Stack>;
}
