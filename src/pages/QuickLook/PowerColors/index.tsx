import { useWorkspaceState } from '@/api/workspaceSession';
import React, {} from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import type { Data } from 'plotly.js';
import PageTemplate from '@/components/common/PageTemplate';
import PlotlyChart from '@/components/plots/PlotlyChart';
import EventListSelector from '@/components/analysis/EventListSelector';
import AnalysisResultIdentity from '@/components/analysis/AnalysisResultIdentity';
import { ProvenancePanel, UtilityWarnings } from '@/components/utilities/UtilityResult';
import { useAnalysisRunner } from '@/hooks/useAnalysisRunner';
import { timingApi, PowerColorsData } from '@/api/timingApi';
import { parsePositiveNumber } from '@/utils/numbers';
import {
  CANONICAL_POWER_COLOR_BANDS,
  validatePowerColorInputs,
  type PowerColorBandInput,
} from '@/utils/powerColors';

const BAND_COLORS = ['#00d4aa', '#3b82f6', '#f59e0b', '#ef4444'];

const PowerColorsPage: React.FC = () => {
  const [eventList, setEventList] = useWorkspaceState('QuickLook/PowerColors/index.tsx:eventList:1', '');
  const [dt, setDt] = useWorkspaceState('QuickLook/PowerColors/index.tsx:dt:2', '0.015625');
  const [segmentSize, setSegmentSize] = useWorkspaceState('QuickLook/PowerColors/index.tsx:segmentSize:3', '512');
  const [bands, setBands] = useWorkspaceState<PowerColorBandInput[]>('QuickLook/PowerColors/index.tsx:bands:4', CANONICAL_POWER_COLOR_BANDS);
  const {
    result, running, error, warnings, run,
    resultInputs, resultIdentity, resultStatus, backendAvailable,
  } =
    useAnalysisRunner<PowerColorsData>('Power Colors');
  const dtNum = parsePositiveNumber(dt);
  const segNum = parsePositiveNumber(segmentSize);
  const validationError = validatePowerColorInputs(dtNum, segNum, bands);
  const canRun = eventList !== '' && validationError === null && !running && backendAvailable;
  const frequencyRanges = Object.fromEntries(
    bands.map((band) => [band.label, [Number(band.fmin), Number(band.fmax)]])
  ) as Record<string, [number, number]>;
  const requestParams = {
    event_list_name: eventList,
    dt: dtNum,
    segment_size: segNum,
    freq_ranges: frequencyRanges,
  };
  const currentInputs = { operation: 'power_colors', ...requestParams };

  const updateBand = (index: number, field: 'fmin' | 'fmax', value: string): void => {
    setBands((previous) => previous.map((band, i) =>
      i === index ? { ...band, [field]: value } : band
    ));
  };

  const handleRun = (): void => {
    if (!canRun || dtNum === null || segNum === null) return;
    const params = { ...requestParams, dt: dtNum, segment_size: segNum };
    void run(() => timingApi.calculatePowerColors(params), { operation: 'power_colors', ...params });
  };

  // Plot only backend-returned values and immutable result bands. Editing a
  // request cannot reinterpret the preceding result or recompute its ratios.
  const bandTraces: Data[] = result
    ? result.band_order.map((label, index) => ({
        x: result.time,
        y: result.power_colors[label],
        error_y: {
          type: 'data',
          array: result.band_variance_errors[label],
          visible: true,
        },
        type: 'scattergl',
        mode: 'lines+markers',
        marker: { size: 4, color: BAND_COLORS[index] },
        line: { width: 1, color: BAND_COLORS[index] },
        name: `${label}: ${result.freq_ranges[label][0]}–${result.freq_ranges[label][1]} Hz`,
      } as Data))
    : [];
  const scatterTrace: Data[] = result
    ? [{
        x: result.pc1,
        y: result.pc2,
        error_x: { type: 'data', array: result.pc1_err, visible: true },
        error_y: { type: 'data', array: result.pc2_err, visible: true },
        type: 'scattergl',
        mode: 'markers',
        marker: { size: 6, color: '#00d4aa' },
      } as Data]
    : [];

  return (
    <PageTemplate
      title="Power Colors"
      description="Noise-subtracted integrated fractional variances per segment, with Heil PC1 = C/A and PC2 = B/D"
      category="Advanced Analysis"
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
                  onChange={(event) => setDt(event.target.value)}
                  error={dtNum === null}
                  helperText="The complete upper band must fit within the available Fourier bins."
                />
                <TextField
                  label="Segment size (s)"
                  size="small"
                  value={segmentSize}
                  onChange={(event) => setSegmentSize(event.target.value)}
                  error={segNum === null}
                  helperText="512 s matches the paper's periodogram length; longer segments improve low-frequency precision."
                />
                <Typography variant="subtitle2">Frequency bands (Hz)</Typography>
                {bands.map((band, index) => (
                  <Box
                    key={band.label}
                    sx={{ display: 'flex', gap: 1, alignItems: 'center' }}
                  >
                    <Typography
                      sx={{ width: 20, fontFamily: '"JetBrains Mono", monospace' }}
                    >
                      {band.label}
                    </Typography>
                    <TextField
                      size="small"
                      label="f min"
                      value={band.fmin}
                      onChange={(event) => updateBand(index, 'fmin', event.target.value)}
                    />
                    <TextField
                      size="small"
                      label="f max"
                      value={band.fmax}
                      onChange={(event) => updateBand(index, 'fmax', event.target.value)}
                    />
                  </Box>
                ))}
                {validationError ? <Alert severity="warning">{validationError}</Alert> : null}
                <Button
                  variant="contained"
                  startIcon={running
                    ? <CircularProgress size={16} color="inherit" />
                    : <PlayArrowIcon />}
                  disabled={!canRun}
                  onClick={handleRun}
                >
                  Compute
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={8} lg={9}>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                {error ? <Alert severity="error">{error}</Alert> : null}
                <UtilityWarnings warnings={warnings} />
                <AnalysisResultIdentity
                  inputs={resultInputs}
                  identity={resultIdentity}
                  status={resultStatus}
                  currentInputs={currentInputs}
                />
                {result ? (
                  <>
                    <Typography variant="body2">
                      Result for {result.provenance.input_source.name}; dt = {result.dt} s;
                      segment = {result.segment_size} s; df = {result.df} Hz.
                    </Typography>
                    <Typography variant="caption">
                      {result.band_order.map((label) =>
                        `${label}: ${result.freq_ranges[label][0]}–${result.freq_ranges[label][1]} Hz`
                      ).join('; ')}
                    </Typography>
                    <UtilityWarnings warnings={result.warnings} />
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        Integrated band variance vs time
                      </Typography>
                      <PlotlyChart workspaceKey='QuickLook/PowerColors/index.tsx:chart:1'                         data={bandTraces}
                        layout={{
                          showlegend: true,
                          xaxis: { title: { text: 'Time (s)' } },
                          yaxis: {
                            title: { text: 'Fractional variance (rms/mean)²' },
                            type: 'linear',
                          },
                        }}
                        height={320}
                      />
                    </Box>
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        Power-color diagram (PC1 = C/A, PC2 = B/D)
                      </Typography>
                      <Typography variant="body2">
                        Colours require a positive ≥{result.detection_sigma}σ variance
                        detection in all four bands. Null entries retain their time positions.
                        Error bars use covariance-aware propagation of periodogram uncertainties.
                      </Typography>
                      <Typography variant="body2">
                        These are exploratory per-segment estimates relative to the common
                        mean detected rate, with each segment’s ideal Poisson noise subtracted.
                        The published method averages observation spectra and fits the
                        white-noise level; detector dead time and background require separate
                        treatment.
                      </Typography>
                      {result.valid_segments.some(Boolean) ? (
                        <PlotlyChart workspaceKey='QuickLook/PowerColors/index.tsx:chart:2'                           data={scatterTrace}
                          layout={{
                            xaxis: { title: { text: 'PC1 = C/A' }, type: 'log' },
                            yaxis: { title: { text: 'PC2 = B/D' }, type: 'log' },
                          }}
                          height={380}
                        />
                      ) : (
                        <Alert severity="info" sx={{ mt: 1 }}>
                          No segment has a positive ≥{result.detection_sigma}σ variance
                          detection in all four bands. Increase segment length or use data
                          with stronger broadband variability. Band estimates, including
                          negative values, remain visible above.
                        </Alert>
                      )}
                    </Box>
                    <ProvenancePanel provenance={result.provenance} />
                  </>
                ) : (
                  <Box sx={{ py: 10, textAlign: 'center' }}>
                    <Typography color="text.secondary">
                      Compute integrated band variances to populate the power-color diagram.
                    </Typography>
                  </Box>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </PageTemplate>
  );
};

export default PowerColorsPage;
