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
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
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
import { useAnalysisRunner } from '@/hooks/useAnalysisRunner';
import { correlationApi, CorrelationData } from '@/api/correlationApi';
import { parsePositiveNumber } from '@/utils/numbers';

const MODE_OPTIONS = ['same', 'full'];
const NORM_OPTIONS = ['none', 'variance'];

const CrossCorrelationPage: React.FC = () => {
  const [eventList1, setEventList1] = useWorkspaceState('QuickLook/CrossCorrelation/index.tsx:eventList1:1', '');
  const [eventList2, setEventList2] = useWorkspaceState('QuickLook/CrossCorrelation/index.tsx:eventList2:2', '');
  const [dt, setDt] = useWorkspaceState('QuickLook/CrossCorrelation/index.tsx:dt:3', '0.1');
  const [mode, setMode] = useWorkspaceState('QuickLook/CrossCorrelation/index.tsx:mode:4', 'same');
  const [norm, setNorm] = useWorkspaceState('QuickLook/CrossCorrelation/index.tsx:norm:5', 'none');
  const {
    result, running, error, run, resultInputs, resultIdentity, resultStatus, backendAvailable,
  } = useAnalysisRunner<CorrelationData>('Cross Correlation');

  const dtNum = parsePositiveNumber(dt);
  const canRun = eventList1 !== '' && eventList2 !== '' && dtNum !== null && !running && backendAvailable;
  const requestParams = {
    event_list_1_name: eventList1,
    event_list_2_name: eventList2,
    dt: dtNum,
    mode,
    norm,
  };

  const currentInputs = { operation: 'cross_correlation', ...requestParams };
  const handleRun = (): void => {
    if (!canRun || dtNum === null) return;
    const params = { ...requestParams, dt: dtNum };
    void run(() => correlationApi.crossCorrelation(params), { operation: 'cross_correlation', ...params });
  };

  const traces: Data[] = result
    ? [
        {
          x: result.time_lags,
          y: result.corr,
          type: 'scattergl',
          mode: 'lines',
          line: { color: '#00d4aa', width: 1 },
        } as Data,
      ]
    : [];

  const hasTimeShift = result != null && result.time_shift !== null;

  return (
    <PageTemplate
      title="Cross Correlation"
      description="Compute the cross-correlation function between two event lists and locate the time shift between them"
      category="Correlation Analysis"
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
                <EventListSelector label="Event list 1" value={eventList1} onChange={setEventList1} />
                <EventListSelector label="Event list 2" value={eventList2} onChange={setEventList2} />
                <Typography variant="caption" sx={{
                  color: "text.secondary"
                }}>
                  Requires compatible timing references and one continuous common good-time interval.
                  For observations with gaps, use GTI Utilities to select a continuous interval first.
                </Typography>
                <TextField
                  label="Time bin dt (s)"
                  size="small"
                  value={dt}
                  onChange={(e) => setDt(e.target.value)}
                  error={dt !== '' && dtNum === null}
                  helperText={dt !== '' && dtNum === null ? 'Must be a positive number' : ' '}
                />
                <FormControl size="small">
                  <InputLabel id="cc-mode-label">Mode</InputLabel>
                  <Select
                    labelId="cc-mode-label"
                    label="Mode"
                    value={mode}
                    onChange={(e) => setMode(e.target.value)}
                  >
                    {MODE_OPTIONS.map((m) => (
                      <MenuItem key={m} value={m}>
                        {m}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small">
                  <InputLabel id="cc-norm-label">Normalization</InputLabel>
                  <Select
                    labelId="cc-norm-label"
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
                {result && <Chip size="small" label={`n: ${result.n.toLocaleString()}`} variant="outlined" />}
                {result && <Chip size="small" label={`dt: ${result.dt} s`} variant="outlined" />}
                {result && <Chip size="small" label={`mode: ${result.mode}`} variant="outlined" />}
                {hasTimeShift && result && (
                  <Chip
                    size="small"
                    color="secondary"
                    label={`time shift: ${result.time_shift?.toFixed(4)} s`}
                  />
                )}
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
              />
              {result && result.warnings.length > 0 && (
                <Alert severity="warning" sx={{ mb: 1 }}>
                  <Stack spacing={0.5}>
                    {result.warnings.map((w, i) => (
                      <Typography key={i} variant="body2">
                        {w}
                      </Typography>
                    ))}
                  </Stack>
                </Alert>
              )}
              {result ? (
                <>
                  <PlotlyChart workspaceKey='QuickLook/CrossCorrelation/index.tsx:chart:1'                     data={traces}
                    layout={{
                      xaxis: { title: { text: 'Time lag (s)' } },
                      yaxis: { title: { text: 'Correlation' } },
                      shapes: hasTimeShift
                        ? [
                            {
                              type: 'line',
                              xref: 'x',
                              x0: result.time_shift as number,
                              x1: result.time_shift as number,
                              yref: 'paper',
                              y0: 0,
                              y1: 1,
                              line: { color: 'rgba(148, 163, 184, 0.7)', width: 1, dash: 'dash' },
                            },
                          ]
                        : [],
                    }}
                  />
                  <Typography
                    variant="caption"
                    sx={{
                      color: "text.secondary",
                      display: 'block',
                      mt: 1
                    }}>
                    Positive shift means the first list lags the second.
                  </Typography>
                </>
              ) : (
                <Box sx={{ py: 10, textAlign: 'center' }}>
                  <Typography sx={{
                    color: "text.secondary"
                  }}>
                    Choose two event lists and compute their cross-correlation.
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

export default CrossCorrelationPage;
