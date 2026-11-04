import { useWorkspaceState } from '@/api/workspaceSession';
import React, {} from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControlLabel,
  Grid,
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
import { timingApi, TimeLagsData } from '@/api/timingApi';
import { parsePositiveNumber } from '@/utils/numbers';

const TimeLagsPage: React.FC = () => {
  const [eventList1, setEventList1] = useWorkspaceState('QuickLook/TimeLags/index.tsx:eventList1:1', '');
  const [eventList2, setEventList2] = useWorkspaceState('QuickLook/TimeLags/index.tsx:eventList2:2', '');
  const pair = usePairedSelection('QuickLook/TimeLags/index.tsx');
  const effectiveEventList2 = pair.twoBand ? eventList1 : eventList2;
  const [dt, setDt] = useWorkspaceState('QuickLook/TimeLags/index.tsx:dt:3', '0.0625');
  const [segmentSize, setSegmentSize] = useWorkspaceState('QuickLook/TimeLags/index.tsx:segmentSize:4', '16');
  const [freqMin, setFreqMin] = useWorkspaceState('QuickLook/TimeLags/index.tsx:freqMin:5', '');
  const [freqMax, setFreqMax] = useWorkspaceState('QuickLook/TimeLags/index.tsx:freqMax:6', '');
  const [logX, setLogX] = useWorkspaceState('QuickLook/TimeLags/index.tsx:logX:7', true);
  const {
    result, running, error, warnings, run,
    resultInputs, resultIdentity, resultStatus, backendAvailable,
  } = useAnalysisRunner<TimeLagsData>('Time Lags');

  const dtNum = parsePositiveNumber(dt);
  const segNum = parsePositiveNumber(segmentSize);
  const fMin = parsePositiveNumber(freqMin);
  const fMax = parsePositiveNumber(freqMax);
  const freqMinInvalid = freqMin !== '' && fMin === null;
  const freqMaxInvalid = freqMax !== '' && fMax === null;
  const freqRangePartial = (fMin !== null) !== (fMax !== null);
  const freqRangeInverted = fMin !== null && fMax !== null && fMax <= fMin;
  const freqRangeValid =
    !freqMinInvalid && !freqMaxInvalid && !freqRangePartial && !freqRangeInverted;
  const canRun = pair.error === null &&
    eventList1 !== '' &&
    effectiveEventList2 !== '' &&
    dtNum !== null &&
    segNum !== null &&
    freqRangeValid &&
    !running &&
    backendAvailable;
  const requestParams = {
    event_list_1_name: eventList1,
    event_list_2_name: effectiveEventList2,
    ...pair.requestSelections,
    dt: dtNum,
    segment_size: segNum,
    freq_range: freqMin === '' && freqMax === '' ? undefined : [fMin, fMax],
  };

  const currentInputs = { operation: 'time_lags', ...requestParams };
  const freqHelperText = (raw: string, parsed: number | null): string => {
    if (raw !== '' && parsed === null) return 'Must be a positive number';
    if (freqRangePartial) return 'Fill both or leave both blank';
    if (freqRangeInverted) return 'f max must be > f min';
    return ' ';
  };

  const handleRun = (): void => {
    if (!canRun || dtNum === null || segNum === null) return;
    const freq_range: [number, number] | undefined =
      fMin !== null && fMax !== null && fMax > fMin ? [fMin, fMax] : undefined;
    const params = { ...requestParams, dt: dtNum, segment_size: segNum, freq_range };
    void run(() => timingApi.calculateTimeLags(params), { operation: 'time_lags', ...params });
  };

  const traces: Data[] = result
    ? [
        {
          x: result.freq,
          y: result.time_lags,
          type: 'scattergl',
          mode: 'lines+markers',
          marker: { size: 4, color: '#00d4aa' },
          line: { color: '#00d4aa', width: 1 },
          error_y: result.time_lags_err
            ? { type: 'data', array: result.time_lags_err, visible: true, color: 'rgba(0, 212, 170, 0.35)' }
            : undefined,
        } as Data,
      ]
    : [];

  return (
    <PageTemplate
      title="Time Lags"
      description="Frequency-dependent time lags between two energy bands (positive = band 1 lags band 2)"
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
                <TextField
                  label="Segment size (s)"
                  size="small"
                  value={segmentSize}
                  onChange={(e) => setSegmentSize(e.target.value)}
                  error={segmentSize !== '' && segNum === null}
                  helperText={segmentSize !== '' && segNum === null ? 'Must be a positive number' : ' '}
                />
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    label="f min (Hz)"
                    size="small"
                    value={freqMin}
                    onChange={(e) => setFreqMin(e.target.value)}
                    error={freqMinInvalid || freqRangePartial || freqRangeInverted}
                    helperText={freqHelperText(freqMin, fMin)}
                  />
                  <TextField
                    label="f max (Hz)"
                    size="small"
                    value={freqMax}
                    onChange={(e) => setFreqMax(e.target.value)}
                    error={freqMaxInvalid || freqRangePartial || freqRangeInverted}
                    helperText={freqHelperText(freqMax, fMax)}
                  />
                </Box>
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
                {result?.freq_range && (
                  <Chip
                    size="small"
                    label={`${result.freq_range[0]}–${result.freq_range[1]} Hz`}
                    variant="outlined"
                  />
                )}
                <FormControlLabel
                  control={<Switch size="small" checked={logX} onChange={(e) => setLogX(e.target.checked)} />}
                  label="log f"
                />
              </Box>
              {error && (
                <Alert severity="error" sx={{ mb: 1 }}>
                  {error}
                </Alert>
              )}
              <UtilityWarnings warnings={warnings} />
              <AnalysisResultIdentity
                inputs={resultInputs}
                identity={resultIdentity}
                status={resultStatus}
                currentInputs={currentInputs}
              />
              {result ? (
                <PlotlyChart workspaceKey='QuickLook/TimeLags/index.tsx:chart:1'                   data={traces}
                  layout={{
                    xaxis: { title: { text: 'Frequency (Hz)' }, type: logX ? 'log' : 'linear' },
                    yaxis: { title: { text: 'Time lag (s)' } },
                    shapes: [
                      {
                        type: 'line',
                        xref: 'paper',
                        x0: 0,
                        x1: 1,
                        yref: 'y',
                        y0: 0,
                        y1: 0,
                        line: { color: 'rgba(148, 163, 184, 0.5)', width: 1, dash: 'dash' },
                      },
                    ],
                  }}
                />
              ) : (
                <Box sx={{ py: 10, textAlign: 'center' }}>
                  <Typography sx={{
                    color: "text.secondary"
                  }}>
                    Choose two event lists and compute their time lags.
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

export default TimeLagsPage;
