import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AnalysisResultIdentity from './AnalysisResultIdentity';

const inputs = { operation: 'power_spectrum', event_list_name: 'original_events', dt: 0.125, norm: 'leahy' };
const identity = { resultId: 'spectrum-1', backendGeneration: 1, completedAt: '2026-10-29T12:00:00Z' };

describe('AnalysisResultIdentity', () => {
  it('shows frozen input values and backend identity when controls have changed', () => {
    render(
      <AnalysisResultIdentity
        inputs={inputs}
        identity={identity}
        status="current"
        currentInputs={{ ...inputs, norm: 'frac', event_list_name: 'new_events' }}
        result={{ name: 'stored_psd', backend_session_id: 'backend-session-1', inputs: [{ name: 'original_events', dataset_id: 'dataset-1' }] }}
      />
    );
    const panel = screen.getByRole('region', { name: 'Result identity' });
    expect(within(panel).getByText('Inputs have changed since this result.')).toBeInTheDocument();
    expect(within(panel).getByText('Result ID: spectrum-1')).toBeInTheDocument();
    expect(within(panel).getByText('Stored result: stored_psd')).toBeInTheDocument();
    fireEvent.click(within(panel).getByRole('button', { name: 'Original calculation inputs' }));
    expect(within(panel).getByText('original_events')).toBeVisible();
    expect(within(panel).getByText('leahy')).toBeVisible();
    expect(within(panel).queryByText('new_events')).not.toBeInTheDocument();
    expect(within(panel).getByText(/"dataset_id": "dataset-1"/)).toBeVisible();
  });

  it('compares canonical request values without a key-order or undefined-field false positive', () => {
    render(
      <AnalysisResultIdentity
        inputs={inputs}
        identity={identity}
        status="current"
        currentInputs={{ norm: 'leahy', dt: 0.125, event_list_name: 'original_events', operation: 'power_spectrum', output_name: undefined }}
      />
    );
    expect(screen.queryByText('Inputs have changed since this result.')).not.toBeInTheDocument();
  });

  it('explains the retained previous result and a stale backend separately', () => {
    const view = render(<AnalysisResultIdentity inputs={inputs} identity={identity} status="previous" />);
    expect(screen.getByText(/The latest request failed/)).toBeInTheDocument();
    view.rerender(<AnalysisResultIdentity inputs={inputs} identity={identity} status="stale" />);
    expect(screen.getByText(/previous backend session and is read-only/)).toBeInTheDocument();
    expect(screen.queryByText(/The latest request failed/)).not.toBeInTheDocument();
  });
});
