import React, { useEffect, useRef, useState } from 'react';
import { Alert, Stack } from '@mui/material';
import { useBackendContext } from '@/context/BackendContext';
import { captureBackendEpoch } from '@/api/backendEpoch';

/** Workbenches with native grants and cross-panel handoffs start fresh per backend.
 * QuickLook retains read-only result snapshots through its analysis runner.
 */
const BackendWorkspaceBoundary: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { generation, isReady } = useBackendContext();
  const managed = generation !== null;
  const epoch = captureBackendEpoch().version;
  const connectedBefore = useRef(false);
  const previousGeneration = useRef(generation);
  const previousEpoch = useRef(epoch);
  const [resetNotice, setResetNotice] = useState(false);

  useEffect(() => {
    if (managed && connectedBefore.current && (
      !isReady || generation !== previousGeneration.current || epoch !== previousEpoch.current
    )) {
      setResetNotice(true);
    }
    if (managed && isReady) connectedBefore.current = true;
    previousGeneration.current = generation;
    previousEpoch.current = epoch;
  }, [generation, isReady, managed, epoch]);

  if (managed && !isReady) {
    return (
      <Alert severity="info">
        Waiting for the backend. This workbench will open with fresh selections when it reconnects.
      </Alert>
    );
  }

  return (
    <Stack spacing={2}>
      {resetNotice ? (
        <Alert severity="info">
          The backend changed. This workbench was reset; select the inputs and files again.
        </Alert>
      ) : null}
      <React.Fragment key={managed ? `${generation}:${epoch}` : 'unmanaged'}>{children}</React.Fragment>
    </Stack>
  );
};

export default BackendWorkspaceBoundary;
