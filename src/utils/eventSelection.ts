import type { EventSelection } from '@/api/selectionApi';

/** Editable form of an EventSelection, stored as text like other page inputs. */
export interface SelectionDraft {
  mode: 'none' | 'energy' | 'pi';
  low: string;
  high: string;
  detectors: string;
  timeIntervals: string;
  gti: string;
}

export const EMPTY_SELECTION_DRAFT: SelectionDraft = {
  mode: 'none',
  low: '',
  high: '',
  detectors: '',
  timeIntervals: '',
  gti: '',
};

export interface ParsedSelection {
  /** The request selection; null means "all photons" (today's behaviour). */
  selection: EventSelection | null;
  /** First validation problem, mirroring the backend's request model. */
  error: string | null;
}

const NUMBER = /^[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$/;

function parseNumber(text: string): number | null {
  const trimmed = text.trim();
  if (!NUMBER.test(trimmed)) return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : null;
}

/** Parse "start, stop; start, stop" (or one interval per line). */
export function parseIntervals(
  text: string,
  label: string
): { intervals: Array<[number, number]> | null; error: string | null } {
  if (!text.trim()) return { intervals: null, error: null };
  const intervals: Array<[number, number]> = [];
  for (const entry of text.split(/[;\n]/).map((part) => part.trim()).filter(Boolean)) {
    const parts = entry.split(/[\s,:]+/).filter(Boolean);
    const start = parts.length === 2 ? parseNumber(parts[0]) : null;
    const stop = parts.length === 2 ? parseNumber(parts[1]) : null;
    if (start === null || stop === null) {
      return { intervals: null, error: `${label}: write each interval as "start, stop"` };
    }
    if (!(start < stop)) {
      return { intervals: null, error: `${label}: each start must be below its stop` };
    }
    intervals.push([start, stop]);
  }
  for (let index = 1; index < intervals.length; index += 1) {
    if (intervals[index][0] < intervals[index - 1][1]) {
      return { intervals: null, error: `${label} must be sorted and must not overlap` };
    }
  }
  return { intervals, error: null };
}

/** Convert a draft into the request model, or report why it is invalid. */
export function parseSelectionDraft(
  draft: SelectionDraft,
  options: { spectral?: boolean } = {}
): ParsedSelection {
  const spectral = options.spectral ?? true;
  const selection: EventSelection = {};

  if (spectral && draft.mode !== 'none') {
    const low = parseNumber(draft.low);
    const high = parseNumber(draft.high);
    const unit = draft.mode === 'energy' ? 'Energy' : 'PI';
    if (low === null || high === null) {
      return { selection: null, error: `${unit} range: enter a lower and upper bound` };
    }
    if (low < 0) return { selection: null, error: `${unit} range cannot be negative` };
    if (!(low < high)) {
      return { selection: null, error: `${unit} range: lower bound must be below the upper bound` };
    }
    if (draft.mode === 'pi') {
      if (!Number.isInteger(low) || !Number.isInteger(high)) {
        return { selection: null, error: 'PI range: channels are whole numbers' };
      }
      selection.pi_range = [low, high];
    } else {
      selection.energy_range = [low, high];
    }
  }

  if (draft.detectors.trim()) {
    const ids = draft.detectors.split(/[\s,;]+/).filter(Boolean).map(parseNumber);
    if (ids.some((id) => id === null || !Number.isInteger(id) || id < 0)) {
      return { selection: null, error: 'Detector IDs are non-negative whole numbers' };
    }
    selection.detector_ids = [...new Set(ids as number[])].sort((a, b) => a - b);
  }

  for (const [field, label] of [
    ['timeIntervals', 'Time intervals'],
    ['gti', 'Extra GTIs'],
  ] as const) {
    const parsed = parseIntervals(draft[field], label);
    if (parsed.error) return { selection: null, error: parsed.error };
    if (parsed.intervals) {
      if (field === 'timeIntervals') selection.time_intervals = parsed.intervals;
      else selection.gti = parsed.intervals;
    }
  }

  return { selection: Object.keys(selection).length > 0 ? selection : null, error: null };
}

/**
 * Whether two bands of one EventList can share photons. Bands on different
 * axes (keV vs PI) or an unrestricted band are assumed to overlap; the backend
 * reports the exact shared-photon count after a run.
 */
export function spectralBandsOverlap(
  first: EventSelection | null,
  second: EventSelection | null
): boolean {
  const range = (selection: EventSelection | null): [number, number] | null =>
    selection?.energy_range ?? selection?.pi_range ?? null;
  const a = range(first);
  const b = range(second);
  // An unrestricted band contains every photon of the other band.
  if (a === null || b === null) return true;
  if ((first?.energy_range == null) !== (second?.energy_range == null)) return true;
  return a[0] < b[1] && b[0] < a[1];
}

/** A short human description, e.g. "2–10 keV · detectors 0, 1". */
export function describeSelection(selection: EventSelection | null): string {
  if (!selection) return 'All photons';
  const parts: string[] = [];
  if (selection.energy_range) parts.push(`${selection.energy_range[0]}–${selection.energy_range[1]} keV`);
  if (selection.pi_range) parts.push(`PI ${selection.pi_range[0]}–${selection.pi_range[1]}`);
  if (selection.detector_ids) parts.push(`detectors ${selection.detector_ids.join(', ')}`);
  if (selection.time_intervals) parts.push(`${selection.time_intervals.length} time interval(s)`);
  if (selection.gti) parts.push(`${selection.gti.length} extra GTI(s)`);
  return parts.join(' · ');
}
