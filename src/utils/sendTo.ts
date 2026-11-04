import type { EventSelection } from '@/api/selectionApi';
import { selectionToDraft, type SelectionDraft } from './eventSelection';

/** One "Send to" destination: a page and the inputs it is opened with. */
export interface SendAction {
  label: string;
  route: string;
  /** Workspace fields of the destination page, keyed as that page reads them. */
  fields: Record<string, unknown>;
}

/** A destination that is not available for this result, with the reason. */
export interface UnavailableSendAction {
  label: string;
  reason: string;
}

const PS = 'QuickLook/PowerSpectrum/index.tsx';
const APS = 'QuickLook/AvgPowerSpectrum/index.tsx';
const DPS = 'QuickLook/DynamicalPowerSpectrum/index.tsx';

/** Inputs that describe an event-list analysis, as the source page holds them. */
export interface EventListInputs {
  eventList: string;
  selection: SelectionDraft;
  dt: string;
  norm: string;
}

export function lightcurveToSpectra(lightcurveName: string): SendAction[] {
  return [
    {
      label: 'Power spectrum',
      route: '/quicklook/power-spectrum',
      fields: { [`${PS}:source`]: 'lightcurve', [`${PS}:selected:lightcurve`]: lightcurveName },
    },
    {
      label: 'Averaged power spectrum',
      route: '/quicklook/avg-power-spectrum',
      fields: { [`${APS}:source`]: 'lightcurve', [`${APS}:selected:lightcurve`]: lightcurveName },
    },
  ];
}

export function eventSpectrumTo(
  inputs: EventListInputs,
  include: Array<'averaged' | 'dynamical'>
): SendAction[] {
  const actions: SendAction[] = [];
  if (include.includes('averaged')) {
    actions.push({
      label: 'Averaged power spectrum',
      route: '/quicklook/avg-power-spectrum',
      fields: {
        [`${APS}:source`]: 'event_list',
        [`${APS}:eventList:1`]: inputs.eventList,
        [`${APS}:selection`]: inputs.selection,
        [`${APS}:dt:2`]: inputs.dt,
        [`${APS}:norm:4`]: inputs.norm,
      },
    });
  }
  if (include.includes('dynamical')) {
    actions.push({
      label: 'Dynamical power spectrum',
      route: '/quicklook/dynamical-power-spectrum',
      fields: {
        [`${DPS}:eventList:1`]: inputs.eventList,
        [`${DPS}:selection`]: inputs.selection,
        [`${DPS}:dt:2`]: inputs.dt,
        [`${DPS}:norm:4`]: inputs.norm,
      },
    });
  }
  return actions;
}

/** Destinations that arrive with later phases: fitting, folding and TOAs. */
export const FUTURE_SEND_TARGETS: UnavailableSendAction[] = [
  { label: 'Fit a model', reason: 'Arrives with spectral modelling (Phase 5)' },
  { label: 'Fold', reason: 'Arrives with the pulsar tools (Phase 4)' },
  { label: 'Pulse TOAs', reason: 'Arrives with the pulsar tools (Phase 4)' },
];

/**
 * "Send to" actions for a power-spectrum result, built from the inputs the
 * result was computed with (as recorded by the analysis runner).
 */
export function spectrumSendTo(
  inputs: Readonly<Record<string, unknown>> | null,
  operation: string,
  include: Array<'averaged' | 'dynamical'>
): { actions: SendAction[]; unavailable: UnavailableSendAction[] } | null {
  if (!inputs || inputs.operation !== operation) return null;
  if (typeof inputs.lightcurve_name === 'string') {
    return {
      actions: include.includes('averaged') ? lightcurveToSpectra(inputs.lightcurve_name).slice(1) : [],
      unavailable: include.includes('dynamical')
        ? [{ label: 'Dynamical power spectrum', reason: 'Dynamical spectra are computed from event lists' }]
        : [],
    };
  }
  if (typeof inputs.event_list_name !== 'string') return null;
  return {
    actions: eventSpectrumTo(
      {
        eventList: inputs.event_list_name,
        selection: selectionToDraft(inputs.selection as EventSelection | undefined),
        dt: String(inputs.dt),
        norm: String(inputs.norm),
      },
      include
    ),
    unavailable: [],
  };
}
