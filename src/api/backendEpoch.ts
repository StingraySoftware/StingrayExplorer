/** Renderer-side lifetime of the managed backend, independent of React timing.
 *
 * Readiness can change twice before React renders again. A monotonic version
 * invalidates requests crossing either transition, including same-port restarts.
 * The null generation is reserved for clients used without a managed provider.
 */
export interface BackendEpoch {
  readonly generation: number | null;
  readonly isReady: boolean;
  readonly version: number;
}

let epoch: BackendEpoch = { generation: null, isReady: true, version: 0 };

export function publishBackendEpoch(generation: number | null, isReady: boolean): void {
  if (epoch.generation === generation && epoch.isReady === isReady) return;
  epoch = { generation, isReady, version: epoch.version + 1 };
}

export function captureBackendEpoch(): BackendEpoch {
  return { ...epoch };
}

export function isBackendEpochCurrent(snapshot: BackendEpoch): boolean {
  return snapshot.version === epoch.version && snapshot.isReady && epoch.isReady;
}
