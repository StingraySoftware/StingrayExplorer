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
  Typography,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import type { Data } from 'plotly.js';
import PageTemplate from '@/components/common/PageTemplate';
import PlotlyChart from '@/components/plots/PlotlyChart';
import EventListSelector from '@/components/analysis/EventListSelector';
import AnalysisResultIdentity from '@/components/analysis/AnalysisResultIdentity';
import { useAnalysisRunner } from '@/hooks/useAnalysisRunner';
import { spectrumApi, PowerSpectrumData } from '@/api/spectrumApi';
import { parsePositiveNumber } from '@/utils/numbers';

const NORM_OPTIONS = ['leahy', 'frac', 'abs', 'none'];

const PowerSpectrumPage: React.FC = () => {
  const [eventList, setEventList] = useWorkspaceState('QuickLook/PowerSpectrum/index.tsx:eventList:1', '');
  const [dt, setDt] = useWorkspaceState('QuickLook/PowerSpectrum/index.tsx:dt:2', '0.0625');
  const [norm, setNorm] = useWorkspaceState('QuickLook/PowerSpectrum/index.tsx:norm:3', 'leahy');
  const [outputName, setOutputName] = useWorkspaceState('QuickLook/PowerSpectrum/index.tsx:outputName:4', '');
  const [logX, setLogX] = useWorkspaceState('QuickLook/PowerSpectrum/index.tsx:logX:5', true);
  const [logY, setLogY] = useWorkspaceState('QuickLook/PowerSpectrum/index.tsx:logY:6', true);
  const [rebinFactor, setRebinFactor] = useWorkspaceState('QuickLook/PowerSpectrum/index.tsx:rebinFactor:7', '0.02');
  const [logRebin, setLogRebin] = useWorkspaceState('QuickLook/PowerSpectrum/index.tsx:logRebin:8', true);
  const [rebinOutputName, setRebinOutputName] = useWorkspaceState('QuickLook/PowerSpectrum/index.tsx:rebinOutputName:9', '');
  const queryClient = useQueryClient();
  const { result, running, error, run, resultInputs, resultIdentity, resultStatus, resultStale, backendAvailable } = useAnalysisRunner<PowerSpectrumData>('Power Spectrum');

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
  const rebinNum = parsePositiveNumber(rebinFactor);
  const canRun = eventList !== '' && dtNum !== null && !running && backendAvailable;
  const rebinValid = logRebin ? rebinNum !== null : rebinNum !== null && rebinNum > 1;

  const createParams = {
    event_list_name: eventList,
    dt: dtNum,
    norm,
    output_name: outputName.trim() || undefined,
  };
  const creationInputs = { operation: 'power_spectrum', ...createParams };
  const currentInputs = resultInputs?.operation === 'rebin_spectrum'
    ? { ...resultInputs, rebin_factor: rebinNum, log: logRebin, creation_inputs: creationInputs }
    : creationInputs;

  const handleRun = (): void => {
    if (!dtNum || !backendAvailable) return;
    const params = { ...createParams, dt: dtNum };
    void run(() => spectrumApi.createPowerSpectrum(params), { operation: 'power_spectrum', ...params });
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
      title="Power Spectrum"
      description="Compute a single (non-averaged) power spectrum from an event list"
      category="Frequency Domain"
      status="ready"
    >
      <Grid container spacing={3}>
        <Grid item xs={12} md={4} lg={3}>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="subtitle2">Parameters</Typography>
                <EventListSelector label="Event list" value={eventList} onChange={setEventList} />
                <TextField
                  label="Time bin dt (s)"
                  size="small"
                  value={dt}
                  onChange={(e) => setDt(e.target.value)}
                  error={dt !== '' && dtNum === null}
                  helperText={dt !== '' && dtNum === null ? 'Must be a positive number' : ' '}
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
                  placeholder={eventList ? `${eventList}_ps` : ''}
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

        <Grid item xs={12} md={8} lg={9}>
          <Card variant="outlined">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                  Result
                </Typography>
                {result?.norm && <Chip size="small" label={`norm: ${result.norm}`} />}
                {result && <Chip size="small" label={`${result.n_freq.toLocaleString()} freqs`} variant="outlined" />}
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
                <PlotlyChart workspaceKey='QuickLook/PowerSpectrum/index.tsx:chart:1'                   data={plotData}
                  layout={{
                    xaxis: { title: { text: 'Frequency (Hz)' }, type: logX ? 'log' : 'linear' },
                    yaxis: { title: { text: 'Power' }, type: logY ? 'log' : 'linear' },
                  }}
                />
              ) : (
                <Box sx={{ py: 10, textAlign: 'center' }}>
                  <Typography color="text.secondary">
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

export default PowerSpectrumPage;
