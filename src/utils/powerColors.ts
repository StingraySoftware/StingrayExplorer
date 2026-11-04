/**
 * Power-color ratios following the Heil et al. (2015) convention: with four
 * frequency bands A < B < C < D (ascending f_min),
 *   PC1 = P(C) / P(A)  and  PC2 = P(B) / P(D)
 * computed per dynamical-spectrum segment.
 */
export interface PowerColorRatios {
  pc1: number[];
  pc2: number[];
}

export function computePowerColorRatios(
  powerColors: Record<string, Array<number | null>>,
  bandOrder: string[]
): PowerColorRatios | null {
  if (bandOrder.length !== 4) return null;
  const [a, b, c, d] = bandOrder.map((key) => powerColors[key]);
  if (!a || !b || !c || !d) return null;

  const n = Math.min(a.length, b.length, c.length, d.length);
  const pc1: number[] = [];
  const pc2: number[] = [];
  for (let i = 0; i < n; i++) {
    const av = a[i];
    const bv = b[i];
    const cv = c[i];
    const dv = d[i];
    if (
      av != null && bv != null && cv != null && dv != null &&
      av > 0 && bv > 0 && cv > 0 && dv > 0 &&
      [av, bv, cv, dv, cv / av, bv / dv].every(Number.isFinite)
    ) {
      pc1.push(cv / av);
      pc2.push(bv / dv);
    }
  }
  return { pc1, pc2 };
}

export interface PowerColorBandInput {
  label: string;
  fmin: string;
  fmax: string;
}

export const CANONICAL_POWER_COLOR_BANDS: PowerColorBandInput[] = [
  { label: 'A', fmin: '0.00390625', fmax: '0.03125' },
  { label: 'B', fmin: '0.03125', fmax: '0.25' },
  { label: 'C', fmin: '0.25', fmax: '2' },
  { label: 'D', fmin: '2', fmax: '16' },
];

/** Match backend Fourier-support checks before sending an expensive request. */
export function validatePowerColorInputs(
  dt: number | null,
  segment: number | null,
  bands: PowerColorBandInput[]
): string | null {
  if (dt === null || !Number.isFinite(dt) || dt <= 0) {
    return 'Time bin dt must be finite and positive.';
  }
  if (segment === null || !Number.isFinite(segment) || segment <= 0) {
    return 'Segment size must be finite and positive.';
  }
  const bins = segment / dt;
  if (!Number.isFinite(bins) || bins < 3) {
    return 'Segment size must be at least 3 × dt.';
  }
  if (Math.abs(bins - Math.round(bins)) > 1e-7) {
    return 'Segment size must contain an integer number of time bins.';
  }
  if (bins > 1_000_000) {
    return 'A segment is limited to 1,000,000 time bins.';
  }
  if (
    bands.length !== 4 ||
    bands.some((band, index) => band.label !== ['A', 'B', 'C', 'D'][index])
  ) {
    return 'Four ordered bands A, B, C, D are required.';
  }
  const resolution = 1 / segment;
  const lastIndex = Math.floor((Math.round(bins) - 1) / 2);
  const support = (lastIndex + .5) * resolution;
  let previousMaximum = 0;
  for (const band of bands) {
    const minimum = Number(band.fmin);
    const maximum = Number(band.fmax);
    if (
      !Number.isFinite(minimum) || !Number.isFinite(maximum) ||
      minimum <= 0 || maximum <= minimum
    ) {
      return `Band ${band.label} needs finite bounds with 0 < f min < f max.`;
    }
    if (minimum < previousMaximum) {
      return 'Bands A, B, C, D must be ordered without overlap.';
    }
    if (minimum < resolution * (1 - 1e-12)) {
      return `Band ${band.label} starts below Fourier resolution (${resolution} Hz); increase segment size.`;
    }
    if (maximum > support * (1 + 1e-12)) {
      return `Band ${band.label} exceeds available Fourier support (${support} Hz); decrease dt.`;
    }
    const first = Math.max(1, Math.ceil(minimum / resolution - 1e-10));
    if (first > lastIndex || first * resolution >= maximum - resolution * 1e-10) {
      return `Band ${band.label} contains no Fourier bins; increase segment size.`;
    }
    previousMaximum = maximum;
  }
  return null;
}
