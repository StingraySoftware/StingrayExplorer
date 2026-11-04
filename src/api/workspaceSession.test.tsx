import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';
import { useWorkspaceState, workspaceSession, restoreWorkspaceSession, onWorkspaceRestored, recordWorkspacePath } from './workspaceSession';
import { publishBackendEpoch } from './backendEpoch';
import { useUIStore } from '@/store/uiStore';

it('round trips selected inputs, invalid unsent text and display choices independently', () => {
  const first = renderHook(() => {
    const selected = useWorkspaceState('selection', '');
    const draft = useWorkspaceState('draft', '.1');
    const log = useWorkspaceState('log', true);
    return { selected, draft, log };
  });
  act(() => { first.result.current.selected[1]('obs'); first.result.current.draft[1]('not-yet-valid'); first.result.current.log[1](false); });
  const saved = JSON.parse(JSON.stringify(workspaceSession()));
  first.unmount();
  restoreWorkspaceSession();
  restoreWorkspaceSession(saved);
  const second = renderHook(() => ({ selected: useWorkspaceState('selection', ''), draft: useWorkspaceState('draft', '.1'), log: useWorkspaceState('log', true) }));
  expect(second.result.current.selected[0]).toBe('obs');
  expect(second.result.current.draft[0]).toBe('not-yet-valid');
  expect(second.result.current.log[0]).toBe(false);
});
it('restores mounted forms, navigation and explicit layout preferences', () => {
  recordWorkspacePath('/quicklook/power-spectrum');
  useUIStore.setState({ logPanelOpen: true, rightToolbarCollapsed: true });
  const saved = workspaceSession();
  const mounted = renderHook(() => useWorkspaceState('draft', 'default'));
  let path: string | undefined;
  const stop = onWorkspaceRestored((value) => { path = value; });
  act(() => restoreWorkspaceSession({ ...saved, fields: { draft: 'restored' } }));
  expect(mounted.result.current[0]).toBe('restored');
  expect(path).toBe('/quicklook/power-spectrum');
  expect(useUIStore.getState().logPanelOpen).toBe(true);
  stop();
});
it('does not revive backend selections across an ordinary restart', () => {
  publishBackendEpoch(1, true);
  const appearance = renderHook(() => useWorkspaceState('$darkMode', true));
  act(() => appearance.result.current[1](false));
  const first = renderHook(() => useWorkspaceState('selection', ''));
  act(() => first.result.current[1]('old'));
  first.unmount();
  publishBackendEpoch(2, true);
  const second = renderHook(() => useWorkspaceState('selection', ''));
  expect(second.result.current[0]).toBe('');
  const retainedAppearance = renderHook(() => useWorkspaceState('$darkMode', true));
  expect(retainedAppearance.result.current[0]).toBe(false);
  appearance.unmount();
  retainedAppearance.unmount();
  second.unmount();
  publishBackendEpoch(null, true);
});
it('rejects unsupported versions and safely defaults incompatible field types', () => {
  expect(() => restoreWorkspaceSession({ version: 2, fields: {} } as never)).toThrow();
  restoreWorkspaceSession({ version: 1, fields: { draft: { invalid: true } } });
  const value = renderHook(() => useWorkspaceState('draft', 'default'));
  expect(value.result.current[0]).toBe('default');
});
