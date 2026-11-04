import { useWorkspaceState } from '@/api/workspaceSession';
import React, { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  FormControlLabel,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import type { Data } from 'plotly.js';
import PageTemplate from '@/components/common/PageTemplate';
import PlotlyChart from '@/components/plots/PlotlyChart';
import EventListSelector from '@/components/analysis/EventListSelector';
import LightcurveSelector from '@/components/analysis/LightcurveSelector';
import EventSelectionField from '@/components/analysis/EventSelectionField';
import { useEventSelection } from '@/hooks/useEventSelection';
import AnalysisResultIdentity from '@/components/analysis/AnalysisResultIdentity';
import { useAnalysisRunner } from '@/hooks/useAnalysisRunner';
import { spectrumApi, PowerSpectrumData } from '@/api/spectrumApi';
import { parsePositiveNumber } from '@/utils/numbers';

const NORM_OPTIONS = ['leahy', 'frac', 'abs', 'none'];

const AvgPowerSpectrumPage: React.FC = () => {
  const [eventList, setEventList] = useWorkspaceState('QuickLook/AvgPowerSpectrum/index.tsx:eventList:1', '');
  const { draft: selectionDraft, setDraft: setSelectionDraft, selection, error: selectionError } =
    useEventSelection('QuickLook/AvgPowerSpectrum/index.tsx:selection');
  const [source, setSource] = useWorkspaceState<'event_list' | 'lightcurve'>('QuickLook/AvgPowerSpectrum/index.tsx:source', 'event_list');
  const [lightcurveName, setLightcurveName] = useWorkspaceState('QuickLook/AvgPowerSpectrum/index.tsx:selected:lightcurve', '');
  const fromLightcurve = source === 'lightcurve';
  const [dt, setDt] = useWorkspaceState('QuickLook/AvgPowerSpectrum/index.tsx:dt:2', '0.0625');
  const [segmentSize, setSegmentSize] = useWorkspaceState('QuickLook/AvgPowerSpectrum/index.tsx:segmentSize:3', '16');
  const [norm, setNorm] = useWorkspaceState('QuickLook/AvgPowerSpectrum/index.tsx:norm:4', 'leahy');
  const [outputName, setOutputName] = useWorkspaceState('QuickLook/AvgPowerSpectrum/index.tsx:outputName:5', '');
  const [logX, setLogX] = useWorkspaceState('QuickLook/AvgPowerSpectrum/index.tsx:logX:6', true);
  const [logY, setLogY] = useWorkspaceState('QuickLook/AvgPowerSpectrum/index.tsx:logY:7', true);
  const [rebinFactor, setRebinFactor] = useWorkspaceState('QuickLook/AvgPowerSpectrum/index.tsx:rebinFactor:8', '0.02');
  const [logRebin, setLogRebin] = useWorkspaceState('QuickLook/AvgPowerSpectrum/index.tsx:logRebin:9', true);
  const [rebinOutputName, setRebinOutputName] = useWorkspaceState('QuickLook/AvgPowerSpectrum/index.tsx:rebinOutputName:10', '');
  const queryClient = useQueryClient();
  const { result, running, error, run, resultInputs, resultIdentity, resultStatus, resultStale, backendAvailable } = useAnalysisRunner<PowerSpectrumData>('Averaged Power Spectrum');

  const lastStoredName = result?.name ?? null;
  const existingSpectra = useQuery({
    queryKey: ['spectra'],
    enabled: lastStoredName !== null && backendAvailable && !resultStale,
    staleTime: 0,
    refetchInterval: 5_000,
    queryFn: async () => {
      const response = await spectrumApi.listSpectra();
      if (!response.success) throw new Error(response.error || response.message);
      return response.data ?? [];
    },
  });
  const matchingStoredResult = existingSpectra.data?.some((spectrum) =>
    spectrum.name === lastStoredName &&
    (result?.result_id === undefined || spectrum.result_id === result.result_id)
  ) ?? false;
  const storedResultAvailable = backendAvailable && !resultStale && existingSpectra.isSuccess && matchingStoredResult;
  const backingResultMissing = lastStoredName !== null && !resultStale &&
    existingSpectra.isSuccess && !existingSpectra.isFetching && !matchingStoredResult;

  const suggestedFor = React.useRef(result);
  useEffect(() => {
    if (!result || suggestedFor.current === result) return;
    suggestedFor.current = result;
    void queryClient.invalidateQueries({ queryKey: ['spectra'] });
    setRebinOutputName(result.name
      ? `${result.name.slice(0, 43)}_r_${result.result_id?.slice(0, 8) ?? 'derived'}`
      : '');
  }, [result, queryClient, setRebinOutputName]);

  const dtNum = parsePositiveNumber(dt);
  const segNum = parsePositiveNumber(segmentSize);
  const rebinNum = parsePositiveNumber(rebinFactor);
  const sourceReady = fromLightcurve
    ? lightcurveName !== ''
    : selectionError === null && eventList !== '' && dtNum !== null;
  const canRun = sourceReady && segNum !== null && !running && backendAvailable;
  const rebinValid = logRebin ? rebinNum !== null : rebinNum !== null && rebinNum > 1;

  const createParams = fromLightcurve
    ? {
      lightcurve_name: lightcurveName,
      segment_size: segNum,
      norm,
      output_name: outputName.trim() || undefined,
    }
    : {
      event_list_name: eventList,
      ...(selection ? { selection } : {}),
      dt: dtNum,
      segment_size: segNum,
      norm,
      output_name: outputName.trim() || undefined,
    };
  const creationInputs = { operation: 'averaged_power_spectrum', ...createParams };
  const currentInputs = resultInputs?.operation === 'rebin_spectrum'
    ? { ...resultInputs, rebin_factor: rebinNum, log: logRebin, creation_inputs: creationInputs }
    : creationInputs;

  const handleRun = (): void => {
    if (!canRun || !segNum) return;
    const output_name = outputName.trim() || undefined;
    const params = fromLightcurve
      ? { lightcurve_name: lightcurveName, segment_size: segNum, norm, output_name }
      : {
        event_list_name: eventList,
        ...(selection ? { selection } : {}),
        dt: dtNum ?? undefined,
        segment_size: segNum,
        norm,
        output_name,
      };
    void run(() => spectrumApi.createAveragedPowerSpectrum(params), { operation: 'averaged_power_spectrum', ...params });
  };

  const handleRebin = (): void => {
    if (!lastStoredName || !rebinNum || !storedResultAvailable || !rebinOutputName.trim()) return;
    const params = {
      name: lastStoredName,
      expected_result_id: result?.result_id,
      rebin_factor: rebinNum,
      log: logRebin,
      output_name: rebinOutputName.trim(),
    };
    const originalInputs = resultInputs?.operation === 'rebin_spectrum'
      ? resultInputs.creation_inputs : resultInputs;
    void run(() => spectrumApi.rebinSpectrum(params), {
      operation: 'rebin_spectrum',
      ...params,
      creation_inputs: originalInputs,
    });
  };

  const plotData: Data[] = result
    ? [
        {
          x: result.freq,
          y: result.power,
          type: 'scattergl',
          mode: 'lines',
          line: { color: '#00d4aa', width: 1 },
        },
      ]
    : [];

  return (
    <PageTemplate
      title="Averaged Power Spectrum"
      description="Welch-style averaged power spectrum over fixed-length segments"
      category="Frequency Domain"
      status="ready"
    >
      <Grid container spacing={3}>
        <Grid
          size={{
            xs: 12,
            md: 4,
            lg: 3
          }}>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="subtitle2">Parameters</Typography>
                <ToggleButtonGroup
                  size="small"
                  exclusive
                  fullWidth
                  value={source}
                  onChange={(_event, value: 'event_list' | 'lightcurve' | null) => {
                    if (value) setSource(value);
                  }}
                  aria-label="Source"
                >
                  <ToggleButton value="event_list">Event list</ToggleButton>
                  <ToggleButton value="lightcurve">Light curve</ToggleButton>
                </ToggleButtonGroup>
                {fromLightcurve ? (
                  <>
                    <LightcurveSelector
                      label="Light curve"
                      value={lightcurveName}
                      onChange={setLightcurveName}
                    />
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      Uses the light curve&apos;s own bins; rebin it on the Light Curve page to
                      change dt.
                    </Typography>
                  </>
                ) : (
                  <>
                    <EventListSelector label="Event list" value={eventList} onChange={setEventList} />
                    <EventSelectionField
                      eventListName={eventList}
                      value={selectionDraft}
                      onChange={setSelectionDraft}
                    />
                    <TextField
                      label="Time bin dt (s)"
                      size="small"
                      value={dt}
                      onChange={(e) => setDt(e.target.value)}
                      error={dt !== '' && dtNum === null}
                      helperText={dt !== '' && dtNum === null ? 'Must be a positive number' : ' '}
                    />
                  </>
                )}
                <TextField
                  label="Segment size (s)"
                  size="small"
                  value={segmentSize}
                  onChange={(e) => setSegmentSize(e.target.value)}
                  error={segmentSize !== '' && segNum === null}
                  helperText={segmentSize !== '' && segNum === null ? 'Must be a positive number' : ' '}
                />
                <FormControl size="small">
                  <InputLabel id="ps-norm-label">Normalization</InputLabel>
                  <Select
                    labelId="ps-norm-label"
                    label="Normalization"
                    value={norm}
                    onChange={(e) => setNorm(e.target.value)}
                  >
                    {NORM_OPTIONS.map((n) => (
                      <MenuItem key={n} value={n}>
                        {n}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  label="Store as (optional)"
                  size="small"
                  value={outputName}
                  onChange={(e) => setOutputName(e.target.value)}
                  placeholder={eventList ? `${eventList}_aps` : ''}
                  helperText="Required to enable rebinning"
                />
                <Button
                  variant="contained"
                  startIcon={running ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />}
                  disabled={!canRun}
                  onClick={handleRun}
                >
                  Compute
                </Button>
              </Stack>

              {lastStoredName && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Stack spacing={2}>
                    <Typography variant="subtitle2">Rebin '{lastStoredName}'</Typography>
                    <TextField
                      label={logRebin ? 'Log rebin fraction f' : 'Linear rebin factor (× df)'}
                      size="small"
                      value={rebinFactor}
                      onChange={(e) => setRebinFactor(e.target.value)}
                      error={rebinFactor !== '' && !rebinValid}
                      helperText={logRebin ? 'Each bin grows by (1 + f)' : 'Must be > 1'}
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={logRebin}
                          onChange={(e) => {
                            const checked = e.target.checked;
                            setLogRebin(checked);
                            if (!checked && rebinNum !== null && rebinNum <= 1) {
                              setRebinFactor('2');
                            }
                          }}
                        />
                      }
                      label="Logarithmic"
                    />
                    <TextField
                      label="Store rebinned as"
                      size="small"
                      value={rebinOutputName}
                      onChange={(event) => setRebinOutputName(event.target.value)}
                      helperText="Creates a separate stored spectrum available in General I/O."
                    />
                    <Button
                      variant="outlined"
                      disabled={!rebinValid || running || !storedResultAvailable || !rebinOutputName.trim()}
                      onClick={handleRebin}
                    >
                      Rebin
                    </Button>
                  </Stack>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid
          size={{
            xs: 12,
            md: 8,
            lg: 9
          }}>
          <Card variant="outlined">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                  Result
                </Typography>
                {result?.norm && <Chip size="small" label={`norm: ${result.norm}`} />}
                {result && <Chip size="small" label={`${result.n_freq.toLocaleString()} freqs`} variant="outlined" />}
                {typeof result?.n_segments === 'number' && (
                  <Chip size="small" label={`${result.n_segments} segments`} variant="outlined" />
                )}
                {typeof result?.df === 'number' && (
                  <Chip size="small" label={`df = ${result.df.toPrecision(3)} Hz`} variant="outlined" />
                )}
                {Array.isArray(result?.df) || result?.frequency_bin_width ||
                  (result !== null && result.df === undefined && resultInputs?.operation === 'rebin_spectrum' && resultInputs.log === true) ? (
                  <Chip size="small" label="Variable frequency bin widths" variant="outlined" />
                ) : null}
                <FormControlLabel
                  control={<Switch size="small" checked={logX} onChange={(e) => setLogX(e.target.checked)} />}
                  label="log f"
                />
                <FormControlLabel
                  control={<Switch size="small" checked={logY} onChange={(e) => setLogY(e.target.checked)} />}
                  label="log P"
                />
              </Box>
              {error && (
                <Alert severity="error" sx={{ mb: 1 }}>
                  {error}
                </Alert>
              )}
              <AnalysisResultIdentity
                inputs={resultInputs}
                identity={resultIdentity}
                status={resultStatus}
                currentInputs={currentInputs}
                result={result}
              />
              {backingResultMissing ? (
                <Alert severity="warning" sx={{ mb: 1 }}>
                  The stored spectrum was deleted or replaced. This plot is a read-only snapshot.
                </Alert>
              ) : null}
              {existingSpectra.isError && lastStoredName && !resultStale ? (
                <Alert severity="warning" sx={{ mb: 1 }}>
                  The stored spectrum could not be verified. Rebinning is unavailable until its list refreshes.
                </Alert>
              ) : null}
              {result ? (
                <PlotlyChart workspaceKey='QuickLook/AvgPowerSpectrum/index.tsx:chart:1'                   data={plotData}
                  layout={{
                    xaxis: { title: { text: 'Frequency (Hz)' }, type: logX ? 'log' : 'linear' },
                    yaxis: { title: { text: 'Power' }, type: logY ? 'log' : 'linear' },
                  }}
                />
              ) : (
                <Box sx={{ py: 10, textAlign: 'center' }}>
                  <Typography sx={{
                    color: "text.secondary"
                  }}>
                    Choose an event list and compute a power spectrum.
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </PageTemplate>
  );
};

export default AvgPowerSpectrumPage;
