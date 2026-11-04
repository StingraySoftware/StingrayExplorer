import { describe, expect, it } from 'vitest';
import { FUTURE_SEND_TARGETS, lightcurveToSpectra, spectrumSendTo } from './sendTo';
import { parseSelectionDraft, selectionToDraft } from './eventSelection';

describe('send to', () => {
  it('opens spectra of a stored light curve', () => {
    const [single, averaged] = lightcurveToSpectra('nicer lc');
    expect(single.route).toBe('/quicklook/power-spectrum');
    expect(single.fields).toEqual({
      'QuickLook/PowerSpectrum/index.tsx:source': 'lightcurve',
      'QuickLook/PowerSpectrum/index.tsx:selected:lightcurve': 'nicer lc',
    });
    expect(averaged.route).toBe('/quicklook/avg-power-spectrum');
  });

  it('carries an event-list spectrum\'s inputs, including its photon selection', () => {
    const send = spectrumSendTo(
      {
        operation: 'power_spectrum',
        event_list_name: 'obs',
        selection: { energy_range: [3, 10], detector_ids: [0, 1] },
        dt: 0.0625,
        norm: 'frac',
      },
      'power_spectrum',
      ['averaged', 'dynamical']
    );
    expect(send?.actions.map((action) => action.label)).toEqual([
      'Averaged power spectrum',
      'Dynamical power spectrum',
    ]);
    expect(send?.actions[1].fields).toEqual({
      'QuickLook/DynamicalPowerSpectrum/index.tsx:eventList:1': 'obs',
      'QuickLook/DynamicalPowerSpectrum/index.tsx:selection': {
        mode: 'energy', low: '3', high: '10', detectors: '0, 1', timeIntervals: '', gti: '',
      },
      'QuickLook/DynamicalPowerSpectrum/index.tsx:dt:2': '0.0625',
      'QuickLook/DynamicalPowerSpectrum/index.tsx:norm:4': 'frac',
    });
  });

  it('explains why a light-curve spectrum cannot become a dynamical spectrum', () => {
    const send = spectrumSendTo(
      { operation: 'power_spectrum', lightcurve_name: 'lc', norm: 'leahy' },
      'power_spectrum',
      ['averaged', 'dynamical']
    );
    expect(send?.actions.map((action) => action.label)).toEqual(['Averaged power spectrum']);
    expect(send?.unavailable[0].label).toBe('Dynamical power spectrum');
  });

  it('offers nothing for other operations and keeps future hooks', () => {
    expect(spectrumSendTo({ operation: 'rebin_spectrum' }, 'power_spectrum', ['averaged'])).toBeNull();
    expect(FUTURE_SEND_TARGETS.map((target) => target.label)).toEqual(['Fit a model', 'Fold', 'Pulse TOAs']);
  });

  it('turns a selection back into an equivalent draft', () => {
    const selection = {
      pi_range: [35, 480] as [number, number],
      time_intervals: [[0, 10], [20, 30]] as Array<[number, number]>,
      gti: [[1, 2]] as Array<[number, number]>,
    };
    expect(parseSelectionDraft(selectionToDraft(selection)).selection).toEqual(selection);
    expect(selectionToDraft(null).mode).toBe('none');
  });
});
