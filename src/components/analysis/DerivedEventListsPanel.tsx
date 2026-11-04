import React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link as RouterLink } from 'react-router';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
  InputLabel,
  Link,
  MenuItem,
  OutlinedInput,
  Paper,
  Select,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import CallSplitIcon from '@mui/icons-material/CallSplit';
import { useWorkspaceState } from '@/api/workspaceSession';
import type { EventListSummary } from '@/api/dataApi';
import { ApiResponse } from '@/api/client';
import { DerivedEventList, EventLineage, GtiStrategy, selectionApi } from '@/api/selectionApi';
import { EVENT_LISTS_QUERY_KEY } from '@/hooks/useEventLists';
import { useEventSelection } from '@/hooks/useEventSelection';
import { useBackendContext } from '@/context/BackendContext';
import EventListSelector from './EventListSelector';
import EventSelectionField from './EventSelectionField';
import { nameError } from '@/utils/derivedName';

const KEY = 'DataIngestion/DerivedEventLists';
const GTI_STRATEGIES: Array<{ value: GtiStrategy; label: string }> = [
  { value: 'infer', label: 'Infer (intersect if they overlap, else union)' },
  { value: 'intersection', label: 'Intersection' },
  { value: 'union', label: 'Union' },
  { value: 'append', label: 'Append (must not overlap)' },
  { value: 'none', label: 'None (one span from first to last)' },
];
const OPERATION_LABELS: Record<string, string> = {
  filter: 'filtered',
  join: 'joined',
  sort: 'sorted',
  apply_deadtime: 'dead time',
  rmf_pi_to_energy: 'RMF calibrated',
};

/** Short lineage text for chips and tooltips, e.g. "filtered from obs1". */
export function describeLineage(lineage: EventLineage): string {
  const operation = OPERATION_LABELS[lineage.operation] ?? lineage.operation;
  const parents = lineage.parents.map((parent) => `'${parent.name}'`).join(' + ');
  return `${operation} from ${parents}`;
}

interface DerivedEventListsPanelProps {
  eventLists: EventListSummary[];
  /** Refresh the caller's own list after a product is stored. */
  onCreated?: () => void;
}

/** Create filtered, joined, sorted or dead-time-applied EventLists. */
const DerivedEventListsPanel: React.FC<DerivedEventListsPanelProps> = ({
  eventLists,
  onCreated,
}) => {
  const queryClient = useQueryClient();
  const { generation, isReady } = useBackendContext();
  const backendAvailable = generation === null || isReady;
  // Dataset names use the ':eventList' keys the workspace clears when the
  // backend restarts, so a stale name cannot select a different dataset.
  const [tab, setTab] = useWorkspaceState(`${KEY}:tab`, 0);
  const [source, setSource] = useWorkspaceState(`${KEY}:eventList`, '');
  const [joinNames, setJoinNames] = useWorkspaceState<string[]>(`${KEY}:join:eventListName`, []);
  const [gtiStrategy, setGtiStrategy] = useWorkspaceState<GtiStrategy>(`${KEY}:gtiStrategy`, 'infer');
  const [deadTime, setDeadTime] = useWorkspaceState(`${KEY}:deadTime`, '0.0025');
  const [paralyzable, setParalyzable] = useWorkspaceState(`${KEY}:paralyzable`, false);
  const [outputName, setOutputName] = useWorkspaceState(`${KEY}:outputName`, '');
  const filter = useEventSelection(`${KEY}:selection`);
  const [busy, setBusy] = React.useState(false);
  const [outcome, setOutcome] = React.useState<
    { severity: 'success' | 'error'; message: string } | null
  >(null);

  const deadTimeValue = Number(deadTime);
  const deadTimeValid = deadTime.trim() !== '' && Number.isFinite(deadTimeValue) && deadTimeValue > 0;
  const outputProblem = nameError(outputName);
  const takenName = eventLists.some((eventList) => eventList.name === outputName);
  const operations = ['filter', 'join', 'sort', 'deadtime', 'calibrate'] as const;
  const operation = operations[tab] ?? 'filter';

  let inputProblem: string | null = null;
  if (operation === 'join') {
    if (joinNames.length < 2) inputProblem = 'Choose at least two event lists to join';
  } else if (operation !== 'calibrate' && source === '') {
    inputProblem = 'Choose an event list';
  }
  if (operation === 'filter') {
    inputProblem ??= filter.error ?? (filter.selection ? null : 'Choose which photons to keep');
  }
  if (operation === 'deadtime' && !deadTimeValid) {
    inputProblem ??= 'Dead time must be a positive number of seconds';
  }
  const canCreate =
    backendAvailable && !busy && inputProblem === null && outputProblem === null && !takenName;

  const create = async (): Promise<void> => {
    if (!canCreate) return;
    setBusy(true);
    setOutcome(null);
    const name = outputName;
    let response: ApiResponse<DerivedEventList>;
    if (operation === 'filter' && filter.selection) {
      response = await selectionApi.deriveFiltered({
        event_list_name: source,
        selection: filter.selection,
        output_name: name,
      });
    } else if (operation === 'join') {
      response = await selectionApi.deriveJoined({
        event_list_names: joinNames,
        gti_strategy: gtiStrategy,
        output_name: name,
      });
    } else if (operation === 'sort') {
      response = await selectionApi.deriveSorted({ event_list_name: source, output_name: name });
    } else {
      response = await selectionApi.deriveDeadtime({
        event_list_name: source,
        dead_time: deadTimeValue,
        paralyzable,
        output_name: name,
      });
    }
    setBusy(false);
    if (response.success && response.data) {
      setOutcome({
        severity: 'success',
        message: `Created '${response.data.name}' (${response.data.n_events.toLocaleString()} events), ${describeLineage(response.data.lineage)}.`,
      });
      setOutputName('');
      void queryClient.invalidateQueries({ queryKey: EVENT_LISTS_QUERY_KEY });
      onCreated?.();
    } else {
      setOutcome({ severity: 'error', message: response.message || response.error || 'Failed' });
    }
  };

  const nameField = (
    <TextField
      label="New event list name"
      size="small"
      value={outputName}
      onChange={(event) => setOutputName(event.target.value)}
      error={outputName !== '' && (outputProblem !== null || takenName)}
      helperText={
        takenName
          ? 'An event list with this name already exists'
          : outputName !== '' && outputProblem
            ? outputProblem
            : 'The source event lists are never modified'
      }
    />
  );

  return (
    <Paper variant="outlined" sx={{ mt: 3, p: 3 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 1 }}>
        <CallSplitIcon fontSize="small" />
        <Typography variant="h6">Derive event lists</Typography>
      </Stack>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
        Each product is stored as a new event list that remembers its parents, appears in every
        event-list picker and is saved with projects.
      </Typography>
      <Tabs
        value={tab}
        onChange={(_event, value: number) => {
          setTab(value);
          setOutcome(null);
        }}
        variant="scrollable"
        sx={{ mb: 2 }}
      >
        <Tab label="Filter" />
        <Tab label="Join" />
        <Tab label="Sort" />
        <Tab label="Dead time" />
        <Tab label="PI → energy" />
      </Tabs>
      <Stack spacing={2} sx={{ maxWidth: 560 }}>
        {(operation === 'filter' || operation === 'sort' || operation === 'deadtime') && (
          <EventListSelector label="Source event list" value={source} onChange={setSource} />
        )}
        {operation === 'filter' && (
          <EventSelectionField
            label="Photons to keep"
            eventListName={source}
            value={filter.draft}
            onChange={filter.setDraft}
          />
        )}
        {operation === 'join' && (
          <>
            <FormControl size="small">
              <InputLabel id="derived-join-label">Event lists to join</InputLabel>
              <Select
                labelId="derived-join-label"
                multiple
                value={joinNames}
                onChange={(event) => {
                  const value = event.target.value;
                  setJoinNames(typeof value === 'string' ? value.split(',') : value);
                }}
                input={<OutlinedInput label="Event lists to join" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((name) => (
                      <Chip key={name} label={name} size="small" />
                    ))}
                  </Box>
                )}
              >
                {eventLists.map((eventList) => (
                  <MenuItem key={eventList.name} value={eventList.name}>
                    {eventList.name} ({eventList.n_events.toLocaleString()} events)
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small">
              <InputLabel id="derived-gti-label">GTI handling</InputLabel>
              <Select
                labelId="derived-gti-label"
                label="GTI handling"
                value={gtiStrategy}
                onChange={(event) => setGtiStrategy(event.target.value as GtiStrategy)}
              >
                {GTI_STRATEGIES.map((strategy) => (
                  <MenuItem key={strategy.value} value={strategy.value}>
                    {strategy.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              For example NuSTAR FPMA and FPMB. Photons are merged in time order.
            </Typography>
          </>
        )}
        {operation === 'sort' && (
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            Orders photons by time, keeping energy, PI and other columns aligned.
          </Typography>
        )}
        {operation === 'deadtime' && (
          <>
            <TextField
              label="Dead time (s)"
              size="small"
              value={deadTime}
              onChange={(event) => setDeadTime(event.target.value)}
              error={deadTime !== '' && !deadTimeValid}
              helperText="Photons arriving within this time of an earlier one are removed"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={paralyzable}
                  onChange={(event) => setParalyzable(event.target.checked)}
                />
              }
              label="Paralyzable detector"
            />
          </>
        )}
        {operation === 'calibrate' ? (
          <Alert severity="info">
            PI → energy calibration needs the instrument&apos;s RMF file, chosen through the native
            file dialog. Use{' '}
            <Link component={RouterLink} to="/utilities/io">
              General I/O → RMF utilities
            </Link>
            , then save the calibrated copy: it is stored as a derived event list with the same
            lineage.
          </Alert>
        ) : (
          <>
            {nameField}
            {inputProblem && source !== '' && operation !== 'join' && (
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                {inputProblem}
              </Typography>
            )}
            <Box>
              <Button
                variant="contained"
                onClick={() => void create()}
                disabled={!canCreate}
                startIcon={busy ? <CircularProgress size={16} color="inherit" /> : undefined}
              >
                Create event list
              </Button>
            </Box>
          </>
        )}
        {outcome && <Alert severity={outcome.severity}>{outcome.message}</Alert>}
      </Stack>
    </Paper>
  );
};

export { nameError };
export default DerivedEventListsPanel;
