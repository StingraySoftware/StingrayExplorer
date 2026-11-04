import { useState } from 'react';
import { IconButton, Tooltip } from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import { apiClient } from '@/api/client';
import { savedAnalyses } from '@/api/projectResults';
import { workspaceSession } from '@/api/workspaceSession';
import { captureBackendEpoch, isBackendEpochCurrent } from '@/api/backendEpoch';
import { useBackendContext } from '@/context/BackendContext';
import { useUIStore } from '@/store/uiStore';

export default function SaveProjectButton() {
  const [busy, setBusy] = useState(false);
  const { generation, isReady } = useBackendContext();
  const available = generation === null || isReady;
  const notify = useUIStore((state) => state.addNotification);
  const save = async () => {
    const epoch = captureBackendEpoch();
    setBusy(true);
    try {
      if (!window.electronAPI?.saveGrantedFile) throw new Error('The native save dialog is unavailable.');
      const destination = await window.electronAPI.saveGrantedFile({ title: 'Save analysis project', defaultPath: 'analysis.srproj', filters: [{ name: 'Stingray project', extensions: ['srproj'] }] });
      if (!destination || !isBackendEpochCurrent(epoch)) return;
      const response = await apiClient.post('/api/projects/save', { destination_path: destination.path, destination_grant: destination.grant, renderer: savedAnalyses(), workspace: workspaceSession() });
      if (isBackendEpochCurrent(epoch)) notify({ type: response.success ? 'success' : 'error', title: 'Analysis project', message: response.message || response.error || 'Project operation failed' });
    } catch (error) {
      if (isBackendEpochCurrent(epoch)) notify({ type: 'error', title: 'Analysis project', message: String(error) });
    } finally { setBusy(false); }
  };
  return <Tooltip title="Save analysis project"><span className="titlebar-no-drag"><IconButton aria-label="Save analysis project" disabled={busy || !available} onClick={() => void save()}><SaveIcon /></IconButton></span></Tooltip>;
}
