import { useWorkspaceState } from '@/api/workspaceSession';
import React, { useMemo } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
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
import { spectrumApi, DynamicalPowerSpectrumData } from '@/api/spectrumApi';
import { parsePositiveNumber } from '@/utils/numbers';

const NORM_OPTIONS = ['leahy', 'frac', 'abs', 'none'];

const DynamicalPowerSpectrumPage: React.FC = () => {
  const [eventList, setEventList] = useWorkspaceState('QuickLook/DynamicalPowerSpectrum/index.tsx:eventList:1', '');
  const [dt, setDt] = useWorkspaceState('QuickLook/DynamicalPowerSpectrum/index.tsx:dt:2', '0.0625');
  const [segmentSize, setSegmentSize] = useWorkspaceState('QuickLook/DynamicalPowerSpectrum/index.tsx:segmentSize:3', '8');
  const [norm, setNorm] = useWorkspaceState('QuickLook/DynamicalPowerSpectrum/index.tsx:norm:4', 'leahy');
  const [outputName, setOutputName] = useWorkspaceState('QuickLook/DynamicalPowerSpectrum/index.tsx:outputName:5', '');
  const [logZ, setLogZ] = useWorkspaceState('QuickLook/DynamicalPowerSpectrum/index.tsx:logZ:6', true);
  const { result, running, error, run, resultInputs, resultIdentity, resultStatus, backendAvailable } = useAnalysisRunner<DynamicalPowerSpectrumData>(
    'Dynamical Power Spectrum'
  );

  const dtNum = parsePositiveNumber(dt);
  const segNum = parsePositiveNumber(segmentSize);
  const canRun = eventList !== '' && dtNum !== null && segNum !== null && !running && backendAvailable;

  const currentInputs = {
    operation: 'dynamical_power_spectrum',
    event_list_name: eventList,
    dt: dtNum,
    segment_size: segNum,
    norm,
    output_name: outputName.trim() || undefined,
  };
  const handleRun = (): void => {
    if (!dtNum || !segNum || !backendAvailable) return;
    const params = {
      event_list_name: eventList,
      dt: dtNum,
      segment_size: segNum,
      norm,
      output_name: outputName.trim() || undefined,
    };
    void run(() => spectrumApi.createDynamicalPowerSpectrum(params), {
      operation: 'dynamical_power_spectrum', ...params,
    });
  };

  // dyn_ps rows correspond to frequencies (n_freq x n_times) — matches
  // Plotly's convention that z[i] pairs with y[i].
  const zValues: Array<Array<number | null>> | undefined = useMemo(
    () =>
      result
        ? logZ
          ? result.dyn_ps.map((row) => row.map((v) => (v !== null && v > 0 ? Math.log10(v) : null)))
          : result.dyn_ps
        : undefined,
    [result, logZ]
  );

  const heatmap: Data[] = useMemo<Data[]>(
    () =>
      result && zValues
        ? [
            {
              z: zValues,
              x: result.time,
              y: result.freq,
              type: 'heatmap',
              colorscale: 'Viridis',
              colorbar: { title: { text: logZ ? 'log10 P' : 'Power' } },
            } as Data,
          ]
        : [],
    [result, zValues, logZ]
  );

  return (
    <PageTemplate
      title="Dynamical Power Spectrum"
      description="Time-resolved power spectrum: power as a function of time and frequency"
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
                <EventListSelector label="Event list" value={eventList} onChange={setEventList} />
                <TextField
                  label="Time bin dt (s)"
                  size="small"
                  value={dt}
                  onChange={(e) => setDt(e.target.value)}
                  error={dt !== '' && dtNum === null}
                  helperText={dt !== '' && dtNum === null ? 'Must be a positive number' : ' '}
                />
                <TextField
                  label="Segment size (s)"
                  size="small"
                  value={segmentSize}
                  onChange={(e) => setSegmentSize(e.target.value)}
                  error={segmentSize !== '' && segNum === null}
                  helperText={segmentSize !== '' && segNum === null ? 'Must be a positive number' : ' '}
                />
                <FormControl size="small">
                  <InputLabel id="dps-norm-label">Normalization</InputLabel>
                  <Select
                    labelId="dps-norm-label"
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
                {result && (
                  <Chip
                    size="small"
                    label={`${result.shape[0]} freqs × ${result.shape[1]} segments`}
                    variant="outlined"
                  />
                )}
                <FormControlLabel
                  control={<Switch size="small" checked={logZ} onChange={(e) => setLogZ(e.target.checked)} />}
                  label="log color"
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
              {result ? (
                <PlotlyChart workspaceKey='QuickLook/DynamicalPowerSpectrum/index.tsx:chart:1'                   data={heatmap}
                  layout={{
                    xaxis: { title: { text: 'Time (s)' } },
                    yaxis: { title: { text: 'Frequency (Hz)' } },
                  }}
                  height={500}
                />
              ) : (
                <Box sx={{ py: 10, textAlign: 'center' }}>
                  <Typography sx={{
                    color: "text.secondary"
                  }}>
                    Compute a dynamical power spectrum to see the time-frequency map.
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

export default DynamicalPowerSpectrumPage;
