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
import PairedEventInputs from '@/components/analysis/PairedEventInputs';
import { usePairedSelection } from '@/hooks/usePairedSelection';
import AnalysisResultIdentity from '@/components/analysis/AnalysisResultIdentity';
import { UtilityWarnings } from '@/components/utilities/UtilityResult';
import { useAnalysisRunner } from '@/hooks/useAnalysisRunner';
import { spectrumApi, PowerSpectrumData } from '@/api/spectrumApi';
import { parsePositiveNumber } from '@/utils/numbers';

const NORM_OPTIONS = ['leahy', 'frac', 'abs', 'none'];

const CrossSpectrumPage: React.FC = () => {
  const [eventList1, setEventList1] = useWorkspaceState('QuickLook/CrossSpectrum/index.tsx:eventList1:1', '');
  const [eventList2, setEventList2] = useWorkspaceState('QuickLook/CrossSpectrum/index.tsx:eventList2:2', '');
  const pair = usePairedSelection('QuickLook/CrossSpectrum/index.tsx');
  const effectiveEventList2 = pair.twoBand ? eventList1 : eventList2;
  const [dt, setDt] = useWorkspaceState('QuickLook/CrossSpectrum/index.tsx:dt:3', '0.0625');
  const [norm, setNorm] = useWorkspaceState('QuickLook/CrossSpectrum/index.tsx:norm:4', 'leahy');
  const [outputName, setOutputName] = useWorkspaceState('QuickLook/CrossSpectrum/index.tsx:outputName:5', '');
  const [logX, setLogX] = useWorkspaceState('QuickLook/CrossSpectrum/index.tsx:logX:6', true);
  const [logY, setLogY] = useWorkspaceState('QuickLook/CrossSpectrum/index.tsx:logY:7', true);
  const [rebinFactor, setRebinFactor] = useWorkspaceState('QuickLook/CrossSpectrum/index.tsx:rebinFactor:8', '0.02');
  const [logRebin, setLogRebin] = useWorkspaceState('QuickLook/CrossSpectrum/index.tsx:logRebin:9', true);
  const [rebinOutputName, setRebinOutputName] = useWorkspaceState('QuickLook/CrossSpectrum/index.tsx:rebinOutputName:10', '');
  const queryClient = useQueryClient();
  const { result, running, error, warnings, run, resultInputs, resultIdentity, resultStatus, resultStale, backendAvailable } = useAnalysisRunner<PowerSpectrumData>('Cross Spectrum');

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
  const canRun = pair.error === null && eventList1 !== '' && effectiveEventList2 !== '' && dtNum !== null && !running && backendAvailable;
  const rebinValid = logRebin ? rebinNum !== null : rebinNum !== null && rebinNum > 1;

  const createParams = {
    event_list_1_name: eventList1,
    event_list_2_name: effectiveEventList2,
    ...pair.requestSelections,
    dt: dtNum,
    norm,
    output_name: outputName.trim() || undefined,
  };
  const creationInputs = { operation: 'cross_spectrum', ...createParams };
  const currentInputs = resultInputs?.operation === 'rebin_spectrum'
    ? { ...resultInputs, rebin_factor: rebinNum, log: logRebin, creation_inputs: creationInputs }
    : creationInputs;

  const handleRun = (): void => {
    if (!dtNum || !backendAvailable) return;
    const params = { ...createParams, dt: dtNum };
    void run(() => spectrumApi.createCrossSpectrum(params), { operation: 'cross_spectrum', ...params });
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

  const magnitudeTrace: Data[] = result
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

  const phaseTrace: Data[] =
    result && result.power_phase
      ? [
          {
            x: result.freq,
            y: result.power_phase,
            type: 'scattergl',
            mode: 'markers',
            marker: { color: '#3b82f6', size: 3 },
          },
        ]
      : [];

  return (
    <PageTemplate
      title="Cross Spectrum"
      description="Cross spectrum between two event lists: magnitude and phase"
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
                <PairedEventInputs
                  pair={pair}
                  eventList1={eventList1}
                  onEventList1={setEventList1}
                  eventList2={eventList2}
                  onEventList2={setEventList2}
                />
                <TextField
                  label="Time bin dt (s)"
                  size="small"
                  value={dt}
                  onChange={(e) => setDt(e.target.value)}
                  error={dt !== '' && dtNum === null}
                  helperText={dt !== '' && dtNum === null ? 'Must be a positive number' : ' '}
                />
                <FormControl size="small">
                  <InputLabel id="cs-norm-label">Normalization</InputLabel>
                  <Select
                    labelId="cs-norm-label"
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
                    <Typography variant="subtitle2">Rebin &apos;{lastStoredName}&apos;</Typography>
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
                <FormControlLabel
                  control={<Switch size="small" checked={logX} onChange={(e) => setLogX(e.target.checked)} />}
                  label="log f"
                />
                <FormControlLabel
                  control={<Switch size="small" checked={logY} onChange={(e) => setLogY(e.target.checked)} />}
                  label="log |C|"
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
              <UtilityWarnings warnings={[...warnings, ...(result?.warnings ?? [])]} />
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
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="caption" sx={{
                      color: "text.secondary"
                    }}>
                      Cross-power magnitude
                    </Typography>
                    <PlotlyChart workspaceKey='QuickLook/CrossSpectrum/index.tsx:chart:1'                       data={magnitudeTrace}
                      layout={{
                        xaxis: { title: { text: 'Frequency (Hz)' }, type: logX ? 'log' : 'linear' },
                        yaxis: { title: { text: '|C(f)|' }, type: logY ? 'log' : 'linear' },
                      }}
                      height={320}
                    />
                  </Box>
                  {phaseTrace.length > 0 && (
                    <Box>
                      <Typography variant="caption" sx={{
                        color: "text.secondary"
                      }}>
                        Cross-spectrum phase
                      </Typography>
                      <PlotlyChart workspaceKey='QuickLook/CrossSpectrum/index.tsx:chart:2'                         data={phaseTrace}
                        layout={{
                          xaxis: { title: { text: 'Frequency (Hz)' }, type: logX ? 'log' : 'linear' },
                          yaxis: { title: { text: 'Phase (rad)' }, range: [-3.5, 3.5] },
                        }}
                        height={240}
                      />
                    </Box>
                  )}
                </Stack>
              ) : (
                <Box sx={{ py: 10, textAlign: 'center' }}>
                  <Typography sx={{
                    color: "text.secondary"
                  }}>
                    Choose two event lists and compute their cross spectrum.
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

export default CrossSpectrumPage;
