import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '@/test/testUtils';
import { restoreWorkspaceSession } from '@/api/workspaceSession';

const { listEventLists, deriveFiltered, deriveJoined, deriveSorted, deriveDeadtime, previewSelection } =
  vi.hoisted(() => ({
    listEventLists: vi.fn(),
    deriveFiltered: vi.fn(),
    deriveJoined: vi.fn(),
    deriveSorted: vi.fn(),
    deriveDeadtime: vi.fn(),
    previewSelection: vi.fn(),
  }));
vi.mock('@/api/dataApi', () => ({ dataApi: { listEventLists } }));
vi.mock('@/api/selectionApi', () => ({
  selectionApi: { deriveFiltered, deriveJoined, deriveSorted, deriveDeadtime, previewSelection },
}));
import DerivedEventListsPanel, { describeLineage, nameError } from './DerivedEventListsPanel';

const lists = [
  { name: 'fpma', n_events: 1000, time_range: [0, 10] as [number, number], has_energy: true },
  { name: 'fpmb', n_events: 900, time_range: [0, 10] as [number, number], has_energy: true },
];
const created = (operation: string, parents: string[]) => ({
  success: true,
  data: {
    name: 'product',
    dataset_id: 'id',
    n_events: 500,
    lineage: {
      operation,
      parents: parents.map((name) => ({ name, dataset_id: name, n_events: 1000 })),
      parameters: {},
      stingray_version: '2.3.2',
    },
  },
  message: 'ok',
  error: null,
});

async function choose(label: string, name: string): Promise<void> {
  await userEvent.click(await screen.findByLabelText(label));
  await userEvent.click(await screen.findByRole('option', { name: new RegExp(name) }));
}

describe('DerivedEventListsPanel', () => {
  beforeEach(() => {
    restoreWorkspaceSession();
    vi.clearAllMocks();
    listEventLists.mockResolvedValue({ success: true, data: lists });
    previewSelection.mockResolvedValue({ success: false, message: 'not needed', error: null });
  });

  it('filters a list to the chosen photons under a new name', async () => {
    const onCreated = vi.fn();
    deriveFiltered.mockResolvedValue(created('filter', ['fpma']));
    renderWithProviders(<DerivedEventListsPanel eventLists={lists} onCreated={onCreated} />);
    await choose('Source event list', 'fpma');
    await userEvent.click(screen.getByRole('button', { name: 'Energy' }));
    await userEvent.type(screen.getByLabelText('From (keV)'), '3');
    await userEvent.type(screen.getByLabelText('To (keV)'), '10');
    const button = screen.getByRole('button', { name: 'Create event list' });
    expect(button).toBeDisabled();
    await userEvent.type(screen.getByLabelText('New event list name'), 'fpma 3-10 keV');
    await userEvent.click(button);
    await waitFor(() =>
      expect(deriveFiltered).toHaveBeenCalledWith({
        event_list_name: 'fpma',
        selection: { energy_range: [3, 10] },
        output_name: 'fpma 3-10 keV',
      })
    );
    expect(await screen.findByText(/Created 'product' \(500 events\), filtered from 'fpma'/)).toBeInTheDocument();
    expect(onCreated).toHaveBeenCalled();
  });

  it('joins two detectors with the chosen GTI handling', async () => {
    deriveJoined.mockResolvedValue(created('join', ['fpma', 'fpmb']));
    renderWithProviders(<DerivedEventListsPanel eventLists={lists} />);
    await userEvent.click(screen.getByRole('tab', { name: 'Join' }));
    await userEvent.click(screen.getByLabelText('Event lists to join'));
    const listbox = await screen.findByRole('listbox');
    await userEvent.click(within(listbox).getByRole('option', { name: /fpma/ }));
    await userEvent.click(within(listbox).getByRole('option', { name: /fpmb/ }));
    await userEvent.keyboard('{Escape}');
    await userEvent.type(screen.getByLabelText('New event list name'), 'nustar');
    await userEvent.click(screen.getByRole('button', { name: 'Create event list' }));
    await waitFor(() =>
      expect(deriveJoined).toHaveBeenCalledWith({
        event_list_names: ['fpma', 'fpmb'],
        gti_strategy: 'infer',
        output_name: 'nustar',
      })
    );
  });

  it('applies paralyzable dead time', async () => {
    deriveDeadtime.mockResolvedValue(created('apply_deadtime', ['fpma']));
    renderWithProviders(<DerivedEventListsPanel eventLists={lists} />);
    await userEvent.click(screen.getByRole('tab', { name: 'Dead time' }));
    await choose('Source event list', 'fpma');
    await userEvent.click(screen.getByLabelText('Paralyzable detector'));
    await userEvent.type(screen.getByLabelText('New event list name'), 'dead');
    await userEvent.click(screen.getByRole('button', { name: 'Create event list' }));
    await waitFor(() =>
      expect(deriveDeadtime).toHaveBeenCalledWith({
        event_list_name: 'fpma',
        dead_time: 0.0025,
        paralyzable: true,
        output_name: 'dead',
      })
    );
  });

  it('refuses names that already exist and shows backend errors', async () => {
    deriveSorted.mockResolvedValue({ success: false, message: "EventList 'x' not found", error: null });
    renderWithProviders(<DerivedEventListsPanel eventLists={lists} />);
    await userEvent.click(screen.getByRole('tab', { name: 'Sort' }));
    await choose('Source event list', 'fpma');
    await userEvent.type(screen.getByLabelText('New event list name'), 'fpmb');
    expect(screen.getByText('An event list with this name already exists')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create event list' })).toBeDisabled();
    await userEvent.clear(screen.getByLabelText('New event list name'));
    await userEvent.type(screen.getByLabelText('New event list name'), 'sorted');
    await userEvent.click(screen.getByRole('button', { name: 'Create event list' }));
    expect(await screen.findByText("EventList 'x' not found")).toBeInTheDocument();
  });

  it('points PI calibration at the RMF utilities', async () => {
    renderWithProviders(<DerivedEventListsPanel eventLists={lists} />);
    await userEvent.click(screen.getByRole('tab', { name: 'PI → energy' }));
    expect(screen.getByRole('link', { name: 'General I/O → RMF utilities' })).toHaveAttribute(
      'href',
      '/utilities/io'
    );
  });
});

describe('derived-list helpers', () => {
  it('validates names like the backend', () => {
    expect(nameError('fpma 3-10 keV')).toBeNull();
    expect(nameError(' x')).toMatch(/whitespace/);
    expect(nameError('a+b')).toMatch(/letters, digits/);
  });

  it('describes lineage', () => {
    expect(describeLineage(created('join', ['fpma', 'fpmb']).data.lineage)).toBe(
      "joined from 'fpma' + 'fpmb'"
    );
  });
});
