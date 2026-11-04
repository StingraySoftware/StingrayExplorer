/** Energy-band presets: common bands per mission, plus the user's own. */

export interface BandPreset {
  label: string;
  range: [number, number];
}

const GENERIC: BandPreset[] = [
  { label: 'Soft 0.5–2 keV', range: [0.5, 2] },
  { label: 'Hard 2–10 keV', range: [2, 10] },
  { label: 'Broad 0.5–10 keV', range: [0.5, 10] },
];

/** Keyed by the lower-case MISSION keyword Stingray reads from the FITS header. */
export const MISSION_BAND_PRESETS: Record<string, BandPreset[]> = {
  nustar: [
    { label: 'NuSTAR 3–10 keV', range: [3, 10] },
    { label: 'NuSTAR 10–79 keV', range: [10, 79] },
    { label: 'NuSTAR 3–79 keV', range: [3, 79] },
  ],
  nicer: [
    { label: 'NICER 0.5–2 keV', range: [0.5, 2] },
    { label: 'NICER 2–10 keV', range: [2, 10] },
    { label: 'NICER 0.3–12 keV', range: [0.3, 12] },
  ],
  xte: [
    { label: 'RXTE 2–10 keV', range: [2, 10] },
    { label: 'RXTE 10–30 keV', range: [10, 30] },
  ],
  xmm: [
    { label: 'XMM 0.3–2 keV', range: [0.3, 2] },
    { label: 'XMM 2–10 keV', range: [2, 10] },
  ],
  chandra: [
    { label: 'Chandra 0.5–2 keV', range: [0.5, 2] },
    { label: 'Chandra 2–7 keV', range: [2, 7] },
  ],
  swift: [
    { label: 'Swift XRT 0.3–2 keV', range: [0.3, 2] },
    { label: 'Swift XRT 2–10 keV', range: [2, 10] },
  ],
};

export function missionPresets(mission: string | null | undefined): BandPreset[] {
  const key = (mission ?? '').trim().toLowerCase();
  const match = Object.keys(MISSION_BAND_PRESETS).find(
    (name) => key === name || key.startsWith(name)
  );
  return match ? MISSION_BAND_PRESETS[match] : [];
}

export function genericPresets(): BandPreset[] {
  return GENERIC;
}

const USER_PRESETS_KEY = 'stingray-explorer:energy-band-presets';

function isPreset(value: unknown): value is BandPreset {
  if (!value || typeof value !== 'object') return false;
  const { label, range } = value as Partial<BandPreset>;
  return (
    typeof label === 'string' &&
    Array.isArray(range) &&
    range.length === 2 &&
    range.every((bound) => typeof bound === 'number' && Number.isFinite(bound)) &&
    range[0] >= 0 &&
    range[0] < range[1]
  );
}

/** The user's saved bands; empty when storage is unavailable or corrupt. */
export function loadUserPresets(): BandPreset[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(USER_PRESETS_KEY) ?? '[]');
    return Array.isArray(parsed) ? parsed.filter(isPreset) : [];
  } catch {
    return [];
  }
}

export function saveUserPresets(presets: BandPreset[]): void {
  try {
    localStorage.setItem(USER_PRESETS_KEY, JSON.stringify(presets.filter(isPreset)));
  } catch {
    // Storage can be unavailable; presets are a convenience only.
  }
}
