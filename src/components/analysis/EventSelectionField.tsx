import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Collapse,
  Divider,
  IconButton,
  ListSubheader,
  Menu,
  MenuItem,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from '@mui/material';
import BookmarkAddIcon from '@mui/icons-material/BookmarkAdd';
import DeleteOutlinedIcon from '@mui/icons-material/DeleteOutlined';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import TuneIcon from '@mui/icons-material/Tune';
import { selectionApi } from '@/api/selectionApi';
import { useEventLists } from '@/hooks/useEventLists';
import { useBackendContext } from '@/context/BackendContext';
import { captureBackendEpoch } from '@/api/backendEpoch';
import {
  BandPreset,
  genericPresets,
  loadUserPresets,
  missionPresets,
  saveUserPresets,
} from '@/utils/bandPresets';
import { parseSelectionDraft, SelectionDraft } from '@/utils/eventSelection';

interface EventSelectionFieldProps {
  /** The EventList this selection applies to; the preview counts its photons. */
  eventListName: string;
  value: SelectionDraft;
  onChange: (draft: SelectionDraft) => void;
  label?: string;
  /** False on energy-resolved pages, which choose energies with their own bands. */
  spectral?: boolean;
  disabled?: boolean;
}

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

const formatCount = (value: number): string => value.toLocaleString();

/** Choose which photons of an EventList an analysis uses, with a live count. */
const EventSelectionField: React.FC<EventSelectionFieldProps> = ({
  eventListName,
  value,
  onChange,
  label = 'Photon selection',
  spectral = true,
  disabled = false,
}) => {
  const { data: eventLists } = useEventLists();
  const summary = eventLists?.find((eventList) => eventList.name === eventListName);
  const { generation, isReady } = useBackendContext();
  const backendAvailable = generation === null || isReady;
  const epoch = captureBackendEpoch().version;
  const [presetAnchor, setPresetAnchor] = React.useState<HTMLElement | null>(null);
  const [userPresets, setUserPresets] = React.useState<BandPreset[]>(loadUserPresets);
  const [moreOpen, setMoreOpen] = React.useState(
    () => Boolean(value.detectors || value.timeIntervals || value.gti)
  );

  const parsed = parseSelectionDraft(value, { spectral });
  const requestKey = parsed.selection ? JSON.stringify(parsed.selection) : null;
  const debouncedKey = useDebouncedValue(requestKey, 400);
  const preview = useQuery({
    queryKey: ['selection-preview', generation, epoch, eventListName, debouncedKey],
    enabled: backendAvailable && eventListName !== '' && debouncedKey !== null,
    retry: false,
    staleTime: 30_000,
    queryFn: async () => {
      const response = await selectionApi.previewSelection(
        eventListName,
        JSON.parse(debouncedKey as string)
      );
      if (!response.success || !response.data) {
        throw new Error(response.message || response.error || 'Selection preview failed');
      }
      return response.data;
    },
  });

  const update = (changes: Partial<SelectionDraft>): void => onChange({ ...value, ...changes });
  const unit = value.mode === 'pi' ? 'PI channel' : 'keV';
  const presets = missionPresets(summary?.mission);
  const applyPreset = (preset: BandPreset): void => {
    update({ mode: 'energy', low: String(preset.range[0]), high: String(preset.range[1]) });
    setPresetAnchor(null);
  };
  const currentRange = parsed.selection?.energy_range ?? null;
  const saveCurrentPreset = (): void => {
    if (!currentRange) return;
    const next = [
      ...userPresets.filter(
        (preset) => preset.range[0] !== currentRange[0] || preset.range[1] !== currentRange[1]
      ),
      { label: `${currentRange[0]}–${currentRange[1]} keV`, range: currentRange },
    ];
    setUserPresets(next);
    saveUserPresets(next);
    setPresetAnchor(null);
  };
  const removePreset = (preset: BandPreset): void => {
    const next = userPresets.filter((item) => item !== preset);
    setUserPresets(next);
    saveUserPresets(next);
  };

  const noEnergy = summary !== undefined && summary.has_energy === false;
  const noPi = summary !== undefined && summary.has_pi === false;

  let status: React.ReactNode;
  if (parsed.error) {
    status = <Alert severity="error" variant="outlined">{parsed.error}</Alert>;
  } else if (!parsed.selection) {
    status = (
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        {summary ? `All ${formatCount(summary.n_events)} events` : 'All events'}
      </Typography>
    );
  } else if (!eventListName) {
    status = (
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        Choose an event list to count the selected events.
      </Typography>
    );
  } else if (preview.isError) {
    status = <Alert severity="warning" variant="outlined">{preview.error.message}</Alert>;
  } else if (preview.data && debouncedKey === requestKey) {
    const data = preview.data;
    const share = data.parent_n_events > 0 ? (100 * data.n_events) / data.parent_n_events : 0;
    const coverage = data.energy_coverage
      ? ` · ${data.energy_coverage[0].toFixed(2)}–${data.energy_coverage[1].toFixed(2)} keV`
      : data.pi_coverage
        ? ` · PI ${data.pi_coverage[0]}–${data.pi_coverage[1]}`
        : '';
    status = (
      <Typography variant="caption" sx={{ color: 'text.secondary' }} data-testid="selection-preview">
        {formatCount(data.n_events)} of {formatCount(data.parent_n_events)} events (
        {share.toFixed(1)}%){coverage} · {data.exposure.toFixed(1)} s exposure
      </Typography>
    );
  } else {
    status = (
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        Counting selected events…
      </Typography>
    );
  }

  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 500, flexGrow: 1 }}>
          {label}
        </Typography>
        <Tooltip title="Detector, time and GTI filters">
          <IconButton
            size="small"
            aria-label={`${label}: more filters`}
            onClick={() => setMoreOpen((open) => !open)}
            disabled={disabled}
          >
            <TuneIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>
      <Stack spacing={1.5}>
        {spectral && (
          <ToggleButtonGroup
            size="small"
            exclusive
            fullWidth
            value={value.mode}
            disabled={disabled}
            onChange={(_event, mode: SelectionDraft['mode'] | null) => {
              if (mode) update({ mode });
            }}
            aria-label={`${label}: photons`}
          >
            <ToggleButton value="none">All</ToggleButton>
            <ToggleButton value="energy" disabled={noEnergy}>
              Energy
            </ToggleButton>
            <ToggleButton value="pi" disabled={noPi}>
              PI
            </ToggleButton>
          </ToggleButtonGroup>
        )}
        {spectral && value.mode !== 'none' && (
          <Stack direction="row" spacing={1} sx={{ alignItems: 'flex-start' }}>
            <TextField
              label={`From (${unit})`}
              size="small"
              value={value.low}
              disabled={disabled}
              onChange={(event) => update({ low: event.target.value })}
            />
            <TextField
              label={`To (${unit})`}
              size="small"
              value={value.high}
              disabled={disabled}
              onChange={(event) => update({ high: event.target.value })}
            />
            {value.mode === 'energy' && (
              <Tooltip title="Band presets">
                <IconButton
                  size="small"
                  aria-label={`${label}: band presets`}
                  onClick={(event) => setPresetAnchor(event.currentTarget)}
                  disabled={disabled}
                  sx={{ mt: 0.5 }}
                >
                  <ExpandMoreIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
          </Stack>
        )}
        {spectral && value.mode !== 'none' && (
          <Typography variant="caption" sx={{ color: 'text.secondary', mt: -0.5 }}>
            Includes the lower bound and excludes the upper, so adjacent bands never share photons.
          </Typography>
        )}
        <Menu
          anchorEl={presetAnchor}
          open={presetAnchor !== null}
          onClose={() => setPresetAnchor(null)}
        >
          {presets.length > 0 && <ListSubheader>{summary?.mission?.toUpperCase()}</ListSubheader>}
          {presets.map((preset) => (
            <MenuItem key={`mission-${preset.label}`} onClick={() => applyPreset(preset)}>
              {preset.label}
            </MenuItem>
          ))}
          <ListSubheader>Common bands</ListSubheader>
          {genericPresets().map((preset) => (
            <MenuItem key={`generic-${preset.label}`} onClick={() => applyPreset(preset)}>
              {preset.label}
            </MenuItem>
          ))}
          {userPresets.length > 0 && <ListSubheader>Saved bands</ListSubheader>}
          {userPresets.map((preset) => (
            <MenuItem key={`user-${preset.label}`} onClick={() => applyPreset(preset)}>
              <Box sx={{ flexGrow: 1 }}>{preset.label}</Box>
              <IconButton
                size="small"
                edge="end"
                aria-label={`Delete saved band ${preset.label}`}
                onClick={(event) => {
                  event.stopPropagation();
                  removePreset(preset);
                }}
              >
                <DeleteOutlinedIcon fontSize="small" />
              </IconButton>
            </MenuItem>
          ))}
          <Divider />
          <MenuItem onClick={saveCurrentPreset} disabled={!currentRange}>
            <BookmarkAddIcon fontSize="small" sx={{ mr: 1 }} />
            Save current band
          </MenuItem>
        </Menu>
        <Collapse in={moreOpen} unmountOnExit>
          <Stack spacing={1.5}>
            <TextField
              label="Detector IDs"
              size="small"
              value={value.detectors}
              disabled={disabled || summary?.has_detector_id === false}
              onChange={(event) => update({ detectors: event.target.value })}
              placeholder="e.g. 0, 1"
              helperText={
                summary?.has_detector_id === false
                  ? 'This event list has no detector ID column'
                  : 'Comma-separated'
              }
            />
            <TextField
              label="Time intervals (s)"
              size="small"
              multiline
              minRows={1}
              value={value.timeIntervals}
              disabled={disabled}
              onChange={(event) => update({ timeIntervals: event.target.value })}
              placeholder="start, stop; start, stop"
              helperText="Mission time; intersected with the GTIs"
            />
            <TextField
              label="Extra GTIs (s)"
              size="small"
              multiline
              minRows={1}
              value={value.gti}
              disabled={disabled}
              onChange={(event) => update({ gti: event.target.value })}
              placeholder="start, stop; start, stop"
            />
            <Button
              size="small"
              onClick={() => update({ detectors: '', timeIntervals: '', gti: '' })}
              disabled={disabled || !(value.detectors || value.timeIntervals || value.gti)}
            >
              Clear filters
            </Button>
          </Stack>
        </Collapse>
        {status}
      </Stack>
    </Box>
  );
};

export default EventSelectionField;
