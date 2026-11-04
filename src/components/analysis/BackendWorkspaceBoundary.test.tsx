import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { BackendContext } from '@/context/BackendContext';
import type { BackendState } from '@/hooks/useBackendStatus';
import BackendWorkspaceBoundary from './BackendWorkspaceBoundary';
import { publishBackendEpoch } from '@/api/backendEpoch';

afterEach(() => publishBackendEpoch(null, true));

function Workbench() {
  const [selection, setSelection] = useState('');
  return <input aria-label="Selected dataset" value={selection} onChange={(event) => setSelection(event.target.value)} />;
}

function workspace(generation: number, isReady = true) {
  const value: BackendState = {
    generation, isReady, phase: isReady ? 'ready' : 'starting',
    port: isReady ? 50017 : null, error: null,
  };
  return (
    <BackendContext.Provider value={value}>
      <BackendWorkspaceBoundary><Workbench /></BackendWorkspaceBoundary>
    </BackendContext.Provider>
  );
}

describe('backend-bound scientific workbenches', () => {
  it('clears selections on a new generation even when the port is reused', () => {
    const view = render(workspace(1));
    fireEvent.change(screen.getByLabelText('Selected dataset'), { target: { value: 'old' } });
    view.rerender(workspace(2));
    expect(screen.getByLabelText('Selected dataset')).toHaveValue('');
    expect(screen.getByText(/workbench was reset/)).toBeInTheDocument();
  });

  it('unmounts native selections while unavailable and does not resurrect them', () => {
    const view = render(workspace(1));
    fireEvent.change(screen.getByLabelText('Selected dataset'), { target: { value: 'old' } });
    view.rerender(workspace(1, false));
    expect(screen.queryByLabelText('Selected dataset')).not.toBeInTheDocument();
    view.rerender(workspace(1));
    expect(screen.getByLabelText('Selected dataset')).toHaveValue('');
  });

  it('preserves user selections across an ordinary update in the same backend', () => {
    const view = render(workspace(1));
    fireEvent.change(screen.getByLabelText('Selected dataset'), { target: { value: 'current' } });
    view.rerender(workspace(1));
    expect(screen.getByLabelText('Selected dataset')).toHaveValue('current');
    expect(screen.queryByText(/workbench was reset/)).not.toBeInTheDocument();
  });

  it('resets after a loss/recovery batched before React sees an unavailable state', () => {
    publishBackendEpoch(1, true);
    const view = render(workspace(1));
    fireEvent.change(screen.getByLabelText('Selected dataset'), { target: { value: 'old' } });
    publishBackendEpoch(1, false);
    publishBackendEpoch(1, true);
    view.rerender(workspace(1));
    expect(screen.getByLabelText('Selected dataset')).toHaveValue('');
    expect(screen.getByText(/workbench was reset/)).toBeInTheDocument();
  });
});
