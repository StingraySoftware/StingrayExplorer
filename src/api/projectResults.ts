import { captureBackendEpoch, isBackendEpochCurrent } from './backendEpoch';

export interface SavedAnalysis {
  result: unknown;
  resultInputs: Readonly<Record<string, unknown>> | null;
  resultIdentity: { resultId: string | null; backendGeneration: number | null; backendSessionId: string | null; completedAt: string } | null;
  warnings: string[];
  stale: boolean;
}
const results = new Map<string, { record: SavedAnalysis; epoch: ReturnType<typeof captureBackendEpoch>; hydrate: boolean }>();
const listeners = new Set<() => void>();
export function rememberAnalysis(label: string, record: SavedAnalysis, hydrate = false): void {
  results.set(label, { record: structuredClone(record), epoch: captureBackendEpoch(), hydrate });
}
export function forgetAnalysis(label: string): void { results.delete(label); }
export function savedAnalyses(): Record<string, SavedAnalysis> {
  return Object.fromEntries([...results].map(([label, { record, epoch }]) => [label, {
    ...structuredClone(record), stale: record.stale || !isBackendEpochCurrent(epoch),
  }]));
}
export function restoredAnalysis(label: string): SavedAnalysis | undefined {
  const item = results.get(label);
  if (!item || !item.hydrate || !isBackendEpochCurrent(item.epoch)) return undefined;
  return structuredClone(item.record);
}
export function restoreAnalyses(records: Record<string, SavedAnalysis>): void {
  results.clear();
  for (const [label, record] of Object.entries(records)) {
    if (!record || typeof record !== 'object' || !('result' in record)) throw new Error('Invalid saved analysis record');
    const copy = structuredClone(record);
    if (copy.resultIdentity) copy.resultIdentity.backendGeneration = captureBackendEpoch().generation;
    rememberAnalysis(label, copy, true);
  }
  for (const notify of listeners) notify();
}
export function onProjectRestored(notify: () => void): () => void {
  listeners.add(notify);
  return () => { listeners.delete(notify); };
}
