import { afterEach, expect, it } from 'vitest';
import { captureBackendEpoch, publishBackendEpoch } from './backendEpoch';
import { rememberAnalysis, restoredAnalysis, restoreAnalyses, savedAnalyses, onProjectRestored } from './projectResults';
const record = { result: { power: [1, 2], parameters: { dt: .1 } }, resultInputs: { name: 'source', dt: .1 }, resultIdentity: { resultId: 'saved-id', backendGeneration: 1, backendSessionId: 'historical-session', completedAt: 'original-time' }, warnings: [], stale: false };
afterEach(() => { restoreAnalyses({}); publishBackendEpoch(null, true); });
it('owns input/result snapshots and marks records stale across a backend restart', () => {
  publishBackendEpoch(1, true);
  rememberAnalysis('Power spectrum', record);
  const exported = savedAnalyses();
  (exported['Power spectrum'].result as {power: number[]}).power[0] = 99;
  expect((savedAnalyses()['Power spectrum'].result as {power: number[]}).power[0]).toBe(1);
  publishBackendEpoch(2, true);
  expect(savedAnalyses()['Power spectrum'].stale).toBe(true);
});
it('rebinds reopened records to this launch while preserving scientific result identity', () => {
  publishBackendEpoch(3, true);
  let notified = 0;
  const stop = onProjectRestored(() => { notified++; });
  restoreAnalyses({ 'Power spectrum': record });
  const restored = restoredAnalysis('Power spectrum');
  expect(restored?.resultInputs).toEqual(record.resultInputs);
  expect(restored?.resultIdentity).toEqual({ ...record.resultIdentity, backendGeneration: captureBackendEpoch().generation });
  expect(restored?.stale).toBe(false);
  expect(notified).toBe(1);
  stop();
});
