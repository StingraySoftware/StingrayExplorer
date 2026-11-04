import { describe, expect, it } from 'vitest';
import {
  EMPTY_SELECTION_DRAFT,
  describeSelection,
  parseSelectionDraft,
  spectralBandsOverlap,
} from './eventSelection';

const draft = (changes: Partial<typeof EMPTY_SELECTION_DRAFT>) => ({
  ...EMPTY_SELECTION_DRAFT,
  ...changes,
});

describe('parseSelectionDraft', () => {
  it('treats an empty draft as all photons', () => {
    expect(parseSelectionDraft(EMPTY_SELECTION_DRAFT)).toEqual({ selection: null, error: null });
  });

  it('builds energy, PI, detector and interval selections', () => {
    expect(parseSelectionDraft(draft({ mode: 'energy', low: '0.5', high: '2' }))).toEqual({
      selection: { energy_range: [0.5, 2] },
      error: null,
    });
    expect(
      parseSelectionDraft(
        draft({
          mode: 'pi',
          low: '35',
          high: '480',
          detectors: '3, 1 3',
          timeIntervals: '0, 100; 200 300',
          gti: '10:20',
        })
      ).selection
    ).toEqual({
      pi_range: [35, 480],
      detector_ids: [1, 3],
      time_intervals: [
        [0, 100],
        [200, 300],
      ],
      gti: [[10, 20]],
    });
  });

  it.each([
    [{ mode: 'energy' as const, low: '2', high: '0.5' }, 'lower bound must be below'],
    [{ mode: 'energy' as const, low: '-1', high: '2' }, 'cannot be negative'],
    [{ mode: 'energy' as const, low: '', high: '2' }, 'enter a lower and upper bound'],
    [{ mode: 'pi' as const, low: '1.5', high: '20' }, 'whole numbers'],
    [{ detectors: '1, -2' }, 'Detector IDs'],
    [{ timeIntervals: '5, 1' }, 'start must be below'],
    [{ timeIntervals: '0, 5; 4, 8' }, 'must not overlap'],
    [{ gti: '0 5 6' }, 'start, stop'],
  ])('rejects %o', (changes, message) => {
    const parsed = parseSelectionDraft(draft(changes));
    expect(parsed.selection).toBeNull();
    expect(parsed.error).toContain(message);
  });

  it('ignores energy and PI cuts where the page defines its own energy bands', () => {
    expect(
      parseSelectionDraft(draft({ mode: 'energy', low: '0.5', high: '2', detectors: '0' }), {
        spectral: false,
      }).selection
    ).toEqual({ detector_ids: [0] });
  });
});

describe('spectralBandsOverlap', () => {
  it('compares half-open bands on the same axis', () => {
    expect(spectralBandsOverlap({ energy_range: [0.5, 2] }, { energy_range: [2, 10] })).toBe(false);
    expect(spectralBandsOverlap({ energy_range: [0.5, 3] }, { energy_range: [2, 10] })).toBe(true);
    expect(spectralBandsOverlap({ pi_range: [0, 10] }, { pi_range: [10, 20] })).toBe(false);
  });

  it('assumes overlap for unrestricted or mixed-axis bands', () => {
    expect(spectralBandsOverlap(null, { energy_range: [2, 10] })).toBe(true);
    expect(spectralBandsOverlap({ energy_range: [0.5, 2] }, { pi_range: [100, 200] })).toBe(true);
  });
});

describe('describeSelection', () => {
  it('summarises a selection for labels', () => {
    expect(describeSelection(null)).toBe('All photons');
    expect(describeSelection({ energy_range: [2, 10], detector_ids: [0, 1] })).toBe(
      '2–10 keV · detectors 0, 1'
    );
  });
});
