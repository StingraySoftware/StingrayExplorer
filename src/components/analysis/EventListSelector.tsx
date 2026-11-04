import React from 'react';
import {
  Alert,
  Box,
  CircularProgress,
  FormControl,
  IconButton,
  InputLabel,
  inputLabelClasses,
  Link,
  MenuItem,
  Select,
  Tooltip,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { Link as RouterLink } from 'react-router';
import { useEventLists } from '@/hooks/useEventLists';
import type { EventListSummary } from '@/api/dataApi';
import { useBackendContext } from '@/context/BackendContext';
import { captureBackendEpoch } from '@/api/backendEpoch';

interface EventListSelectorProps {
  label: string;
  value: string;
  onChange: (name: string) => void;
  requiredCapability?: 'pi' | 'energy';
  disabled?: boolean;
}

function supportsRequiredCapability(
  eventList: EventListSummary,
  requiredCapability: EventListSelectorProps['requiredCapability']
): boolean {
  if (requiredCapability === 'pi') return eventList.has_pi === true;
  if (requiredCapability === 'energy') return eventList.has_energy === true;
  return true;
}

/** Dropdown of event lists currently loaded in the backend. */
const EventListSelector: React.FC<EventListSelectorProps> = ({
  label,
  value,
  onChange,
  requiredCapability,
  disabled = false,
}) => {
  const { data, isLoading, isError, error, refetch, isFetching } = useEventLists();
  const { generation, isReady } = useBackendContext();
  const backendAvailable = generation === null || isReady;
  const epoch = captureBackendEpoch().version;
  const selectedGeneration = React.useRef(generation);
  const selectedEpoch = React.useRef(epoch);
  const selectedDataset = React.useRef<{ name: string; id: string | null } | null>(null);
  const labelId = `event-list-selector-${React.useId()}`;
  const capabilityLabel = requiredCapability === 'pi' ? 'PI/channel' : 'energy';

  React.useEffect(() => {
    const changed = selectedGeneration.current !== generation || selectedEpoch.current !== epoch;
    selectedGeneration.current = generation;
    selectedEpoch.current = epoch;
    if (generation !== null && (changed || !isReady)) {
      selectedDataset.current = null;
      if (value !== '') onChange('');
    }
  }, [generation, isReady, value, onChange, epoch]);

  // A loaded name can be reused within one backend lifetime. Pin the catalog
  // identity of a selection and require a new deliberate selection when that
  // identity changes. Legacy catalogs without IDs retain name-based behavior.
  React.useEffect(() => {
    if (value === '') {
      selectedDataset.current = null;
      return;
    }
    if (!backendAvailable || isLoading || isFetching || data === undefined) return;
    const selected = data.find((eventList) => eventList.name === value);
    if (!selected) return; // The missing-name/capability effect clears this.
    const id = typeof selected.dataset_id === 'string' ? selected.dataset_id : null;
    const previous = selectedDataset.current;
    if (previous === null || previous.name !== value || previous.id === null) {
      selectedDataset.current = { name: value, id };
      return;
    }
    if (previous.id !== id) {
      onChange('');
    }
  }, [value, data, backendAvailable, isLoading, isFetching, onChange]);

  // Auto-clear a selection that no longer exists in the list (deleted
  // elsewhere or backend restart) so consumers never submit stale names.
  React.useEffect(() => {
    if (
      !isLoading &&
      !isFetching &&
      value !== '' &&
      data !== undefined &&
      !data.some(
        (ev) => ev.name === value && supportsRequiredCapability(ev, requiredCapability)
      )
    ) {
      onChange('');
    }
  }, [data, isLoading, isFetching, value, onChange, requiredCapability]);

  const refreshButton = (
    <Tooltip title="Refresh list">
      <span>
        <IconButton
          size="small"
          aria-label="Refresh event lists"
          onClick={() => refetch()}
          disabled={disabled || isFetching || !backendAvailable}
        >
          {isFetching ? <CircularProgress size={16} /> : <RefreshIcon fontSize="small" />}
        </IconButton>
      </span>
    </Tooltip>
  );

  if (!backendAvailable) {
    return <Alert severity="info">Waiting for the backend before selecting event data.</Alert>;
  }

  // Only take over the UI with an error when there is no usable (stale) data;
  // a failed background refetch keeps the populated dropdown rendered.
  if (isError && data === undefined) {
    return (
      <Alert severity="error" action={refreshButton}>
        Failed to load event lists: {error instanceof Error ? error.message : 'unknown error'}
      </Alert>
    );
  }

  if (!isLoading && (data?.length ?? 0) === 0) {
    return (
      <Alert severity="info" action={refreshButton}>
        No event lists loaded.{' '}
        <Link component={RouterLink} to="/data-ingestion">
          Load data
        </Link>{' '}
        first.
      </Alert>
    );
  }

  if (
    !isLoading &&
    requiredCapability !== undefined &&
    data !== undefined &&
    !data.some((eventList) => supportsRequiredCapability(eventList, requiredCapability))
  ) {
    return (
      <Alert severity="info" action={refreshButton}>
        No EventLists with {capabilityLabel} data are loaded.{' '}
        <Link component={RouterLink} to="/data-ingestion">
          Load compatible data
        </Link>{' '}
        first.
      </Alert>
    );
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <FormControl fullWidth size="small" disabled={disabled || isLoading}>
        <InputLabel
          id={labelId}
          // The resting outlined label stops 24px from the edge, but the select
          // arrow needs ~32px; keep long labels ellipsized clear of it.
          sx={{ [`&:not(.${inputLabelClasses.shrink})`]: { maxWidth: 'calc(100% - 46px)' } }}
        >
          {label}
        </InputLabel>
        <Select
          labelId={labelId}
          value={value}
          label={label}
          onChange={(event) => {
            const name = event.target.value;
            selectedDataset.current = {
              name,
              id: data?.find((eventList) => eventList.name === name)?.dataset_id ?? null,
            };
            onChange(name);
          }}
        >
          {(data ?? []).map((ev) => (
            <MenuItem
              key={ev.name}
              value={ev.name}
              disabled={!supportsRequiredCapability(ev, requiredCapability)}
            >
              {ev.name} ({ev.n_events.toLocaleString()} events)
              {!supportsRequiredCapability(ev, requiredCapability)
                ? ` — no ${capabilityLabel} data`
                : ''}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {refreshButton}
    </Box>
  );
};

export default EventListSelector;
