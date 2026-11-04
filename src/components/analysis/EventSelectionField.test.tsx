import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EMPTY_SELECTION_DRAFT, SelectionDraft } from '@/utils/eventSelection';

const { previewSelection, listEventLists } = vi.hoisted(() => ({
  previewSelection: vi.fn(),
  listEventLists: vi.fn(),
}));
vi.mock('@/api/selectionApi', () => ({ selectionApi: { previewSelection } }));
vi.mock('@/api/dataApi', () => ({ dataApi: { listEventLists } }));
import EventSelectionField from './EventSelectionField';

function Harness({
  initial = EMPTY_SELECTION_DRAFT,
  spectral = true,
  onChange = () => undefined,
}: {
  initial?: SelectionDraft;
  spectral?: boolean;
  onChange?: (draft: SelectionDraft) => void;
}) {
  const [value, setValue] = React.useState(initial);
  return (
    <EventSelectionField
      eventListName="fpma"
      value={value}
      spectral={spectral}
      onChange={(draft) => {
        setValue(draft);
        onChange(draft);
      }}
    />
  );
}

function renderField(props: React.ComponentProps<typeof Harness> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <Harness {...props} />
    </QueryClientProvider>
  );
}

describe('EventSelectionField', () => {
  beforeEach(() => {
    localStorage.clear();
    listEventLists.mockResolvedValue({
      success: true,
      data: [
        { name: 'fpma', n_events: 1000, has_energy: true, has_pi: true, mission: 'NuSTAR' },
      ],
    });
    previewSelection.mockResolvedValue({
      success: true,
      data: {
        event_list_name: 'fpma',
        n_events: 250,
        parent_n_events: 1000,
        energy_coverage: [3.04, 9.96],
        pi_coverage: [36, 199],
        detector_ids: null,
        exposure: 1025,
      },
    });
  });
  afterEach(() => vi.clearAllMocks());

  it('applies a mission preset and previews the selected count', async () => {
    const onChange = vi.fn();
    renderField({ onChange });
    await screen.findByText('All 1,000 events');

    await userEvent.click(screen.getByRole('button', { name: 'Energy' }));
    await userEvent.click(screen.getByLabelText('Photon selection: band presets'));
    await userEvent.click(await screen.findByRole('menuitem', { name: 'NuSTAR 3–10 keV' }));

    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ mode: 'energy', low: '3', high: '10' })
    );
    expect(await screen.findByTestId('selection-preview')).toHaveTextContent(
      '250 of 1,000 events (25.0%) · 3.04–9.96 keV · 1025.0 s exposure'
    );
    expect(previewSelection).toHaveBeenCalledWith('fpma', { energy_range: [3, 10] });
  });

  it('shows the backend reason when a selection cannot be applied', async () => {
    previewSelection.mockResolvedValue({
      success: false,
      message: 'The selection leaves no events.',
      error: 'The selection leaves no events.',
    });
    renderField({ initial: { ...EMPTY_SELECTION_DRAFT, mode: 'energy', low: '80', high: '90' } });
    expect(await screen.findByText('The selection leaves no events.')).toBeInTheDocument();
  });

  it('reports invalid ranges without asking the backend', async () => {
    renderField({ initial: { ...EMPTY_SELECTION_DRAFT, mode: 'energy', low: '10', high: '3' } });
    expect(
      await screen.findByText('Energy range: lower bound must be below the upper bound')
    ).toBeInTheDocument();
    expect(previewSelection).not.toHaveBeenCalled();
  });

  it('saves and reuses a band preset', async () => {
    renderField({ initial: { ...EMPTY_SELECTION_DRAFT, mode: 'energy', low: '4', high: '12' } });
    await userEvent.click(screen.getByLabelText('Photon selection: band presets'));
    await userEvent.click(await screen.findByRole('menuitem', { name: /Save current band/ }));
    expect(JSON.parse(localStorage.getItem('stingray-explorer:energy-band-presets') ?? '[]')).toEqual([
      { label: '4–12 keV', range: [4, 12] },
    ]);
    await userEvent.click(screen.getByLabelText('Photon selection: band presets'));
    expect(await screen.findByRole('menuitem', { name: /4–12 keV/ })).toBeInTheDocument();
  });

  it('hides the energy axis on energy-resolved pages', async () => {
    renderField({ spectral: false });
    await screen.findByText('All 1,000 events');
    expect(screen.queryByRole('button', { name: 'Energy' })).not.toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Photon selection: more filters'));
    expect(screen.getByLabelText('Time intervals (s)')).toBeInTheDocument();
  });

  it('disables energy cuts for lists without an energy column', async () => {
    listEventLists.mockResolvedValue({
      success: true,
      data: [{ name: 'fpma', n_events: 1000, has_energy: false, has_pi: true }],
    });
    renderField();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Energy' })).toBeDisabled());
    expect(screen.getByRole('button', { name: 'PI' })).toBeEnabled();
  });
});
