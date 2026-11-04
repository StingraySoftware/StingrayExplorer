import React from 'react';
import { Alert, Button, Stack, TextField } from '@mui/material';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import { captureBackendEpoch, isBackendEpochCurrent } from '@/api/backendEpoch';

export interface GrantedFileSelection {
  path: string;
  grant: string;
}

interface GrantedFileFieldProps {
  label: string;
  value: GrantedFileSelection | null;
  onChange: (selection: GrantedFileSelection | null) => void;
  filters?: { name: string; extensions: string[] }[];
  disabled?: boolean;
}

/** Native file picker whose result is cryptographically bound to the backend path. */
const GrantedFileField: React.FC<GrantedFileFieldProps> = ({
  label,
  value,
  onChange,
  filters,
  disabled = false,
}) => {
  const [dialogError, setDialogError] = React.useState<string | null>(null);
  const requestSequence = React.useRef(0);
  const mounted = React.useRef(true);
  const selectionKey = JSON.stringify([label, value?.path, value?.grant, filters]);
  const currentSelection = React.useRef({ selectionKey, disabled });
  currentSelection.current = { selectionKey, disabled };
  React.useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; requestSequence.current += 1; };
  }, []);

  const choose = async (): Promise<void> => {
    const request = ++requestSequence.current;
    const epoch = captureBackendEpoch();
    const stillCurrent = (): boolean => mounted.current &&
      requestSequence.current === request &&
      currentSelection.current.selectionKey === selectionKey &&
      !currentSelection.current.disabled && isBackendEpochCurrent(epoch);
    if (!stillCurrent()) return;
    setDialogError(null);
    if (!window.electronAPI?.openGrantedFile) {
      setDialogError('The native file dialog is unavailable.');
      return;
    }
    try {
      const selected = await window.electronAPI.openGrantedFile({ title: label, filters });
      if (!stillCurrent()) return;
      // Cancellation intentionally preserves the previous explicit selection.
      if (selected?.[0]) onChange(selected[0]);
    } catch (error) {
      if (!stillCurrent()) return;
      const detail = error instanceof Error ? error.message : String(error);
      setDialogError(`Could not open the native file dialog: ${detail}`);
    }
  };

  return (
    <Stack spacing={1}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <TextField
          fullWidth
          size="small"
          label={label}
          value={value?.path ?? ''}
          placeholder="Choose a file with the native dialog"
          InputProps={{ readOnly: true }}
        />
        <Button variant="outlined" startIcon={<FolderOpenIcon />} onClick={() => void choose()} disabled={disabled}>
          Choose
        </Button>
      </Stack>
      {dialogError ? <Alert severity="error">{dialogError}</Alert> : null}
    </Stack>
  );
};

export default GrantedFileField;
