import { useUIStore } from '@/store/uiStore';
import { Dispatch, SetStateAction, useCallback, useState, useSyncExternalStore } from 'react';
import { captureBackendEpoch } from './backendEpoch';

export interface WorkspaceSession {
  version: 1;
  fields: Record<string, unknown>;
  preferences?: { logPanelOpen: boolean; rightToolbarCollapsed: boolean };
  path?: string;
}
let fields: Record<string, unknown> = {};
let epoch = captureBackendEpoch().version;
let path = '/';
const restoreListeners = new Set<(path?: string) => void>();
export function recordWorkspacePath(value: string): void { path = value; }
export function onWorkspaceRestored(listener: (path?: string) => void): () => void { restoreListeners.add(listener); return () => { restoreListeners.delete(listener); }; }
const listeners = new Set<() => void>();
function current() {
  const next = captureBackendEpoch().version;
  if (epoch !== next) {
    // Drafts and presentation choices survive a restart; dataset names cannot
    // carry authority into a replacement backend which may reuse those names.
    fields = Object.fromEntries(Object.entries(fields).filter(([key]) =>
      !/(^selection$|:(eventList[12]?|eventListName|sourceEventList|selected|existingSelection|objectKey)(:|$))/.test(key)
    ));
    epoch = next;
  }
}
function notify() { for (const listener of listeners) listener(); }
export function workspaceSession(): WorkspaceSession {
  current();
  const { logPanelOpen, rightToolbarCollapsed } = useUIStore.getState();
  return { version: 1, fields: structuredClone(Object.fromEntries(Object.entries(fields).filter(([key]) => !key.startsWith('ephemeral:')))), preferences: { logPanelOpen, rightToolbarCollapsed }, path };
}
/** Prefill other pages' inputs, e.g. before "Send to" navigates to them. */
export function setWorkspaceFields(values: Record<string, unknown>): void {
  current();
  for (const [key, value] of Object.entries(values)) fields[key] = structuredClone(value);
  notify();
}
export function restoreWorkspaceSession(value?: WorkspaceSession): void {
  if (value && (value.version !== 1 || !value.fields || typeof value.fields !== 'object' || Array.isArray(value.fields))) throw new Error('Unsupported workspace session');
  fields = structuredClone(value?.fields ?? {});
  epoch = captureBackendEpoch().version;
  if (value?.preferences) useUIStore.setState(value.preferences);
  if (value?.path) path = value.path;
  notify();
  for (const listener of restoreListeners) listener(value?.path);
}
export function useWorkspaceState<T>(key: string, initial: T | (() => T)): [T, Dispatch<SetStateAction<T>>] {
  const resolveDefault = (): { key: string; value: T } => ({ key, value: typeof initial === 'function' ? (initial as () => T)() : initial });
  const [storedDefaults, setStoredDefaults] = useState(resolveDefault);
  // Resolve a changed key's default once, during render, as React's derived-state pattern.
  let defaults = storedDefaults;
  if (storedDefaults.key !== key) { defaults = resolveDefault(); setStoredDefaults(defaults); }
  const defaultValue = defaults.value;
  const fallback = useCallback(() => defaultValue, [defaultValue]);
  const subscribe = useCallback((listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; }, []);
  const read = useCallback((): T => {
    current();
    const defaultValue = fallback();
    if (!(key in fields) || (defaultValue === null && fields[key] !== null && typeof fields[key] !== 'string') || (defaultValue !== null && typeof fields[key] !== typeof defaultValue) || Array.isArray(fields[key]) !== Array.isArray(defaultValue) || (defaultValue !== null && fields[key] === null)) fields[key] = defaultValue;
    return fields[key] as T;
  }, [key, fallback]);
  const value = useSyncExternalStore(subscribe, read, read);
  const setValue = useCallback<Dispatch<SetStateAction<T>>>((next) => {
    current();
    const previous = key in fields ? fields[key] as T : fallback();
    fields[key] = typeof next === 'function' ? (next as (value: T) => T)(previous) : next;
    notify();
  }, [key, fallback]);
  return [value, setValue];
}
