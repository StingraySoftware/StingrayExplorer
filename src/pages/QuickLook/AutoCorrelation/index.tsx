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
  Grid,
  Stack,
  Typography,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import type { Data } from 'plotly.js';
import PageTemplate from '@/components/common/PageTemplate';
import PlotlyChart from '@/components/plots/PlotlyChart';
import EventListSelector from '@/components/analysis/EventListSelector';
import EventSelectionField from '@/components/analysis/EventSelectionField';
import { useEventSelection } from '@/hooks/useEventSelection';
import AnalysisResultIdentity from '@/components/analysis/AnalysisResultIdentity';
import { useAnalysisRunner } from '@/hooks/useAnalysisRunner';
import { correlationApi, CorrelationData } from '@/api/correlationApi';
import SchemaForm from '@/components/forms/SchemaForm';
import { parseSchemaValue, useFormSchema } from '@/components/forms/schemaValues';

const AutoCorrelationPage: React.FC = () => {
  const [eventList, setEventList] = useWorkspaceState('QuickLook/AutoCorrelation/index.tsx:eventList:1', '');
  const { draft: selectionDraft, setDraft: setSelectionDraft, selection, error: selectionError } =
    useEventSelection('QuickLook/AutoCorrelation/index.tsx:selection');
  const [dt, setDt] = useWorkspaceState('QuickLook/AutoCorrelation/index.tsx:dt:2', '0.1');
  const [mode, setMode] = useWorkspaceState<'same' | 'full'>('QuickLook/AutoCorrelation/index.tsx:mode:3', 'same');
  const [norm, setNorm] = useWorkspaceState<'none' | 'variance'>('QuickLook/AutoCorrelation/index.tsx:norm:4', 'none');

  const {
    result, running, error, run, resultInputs, resultIdentity, resultStatus, backendAvailable,
  } = useAnalysisRunner<CorrelationData>('Auto Correlation');

  const formSchema = useFormSchema('auto_correlation');
  // Parameter controls and their validation come from the backend schema.
  const dtNum = formSchema.data
    ? (parseSchemaValue(formSchema.data.properties.dt, dt).value as number | null)
    : null;
  const canRun = selectionError === null && eventList !== '' && dtNum !== null && !running && backendAvailable;
  const requestParams = {
    event_list_name: eventList,
    ...(selection ? { selection } : {}),
    dt: dtNum,
    mode,
    norm,
  };

  const currentInputs = { operation: 'auto_correlation', ...requestParams };
  const handleRun = (): void => {
    if (!canRun || dtNum === null) return;
    const params = { ...requestParams, dt: dtNum };
    void run(() => correlationApi.autoCorrelation(params), { operation: 'auto_correlation', ...params });
  };

  const traces: Data[] = result
    ? [
        {
          x: result.time_lags,
          y: result.corr,
          type: 'scattergl',
          mode: 'lines',
          line: { width: 1 },
        } as Data,
      ]
    : [];

  return (
    <PageTemplate
      title="Auto Correlation"
      description="Compute the auto-correlation function of a single event list"
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
                <EventListSelector label="Event list" value={eventList} onChange={setEventList} />
                <EventSelectionField
                  eventListName={eventList}
                  value={selectionDraft}
                  onChange={setSelectionDraft}
                />
                <Typography variant="caption" sx={{
                  color: "text.secondary"
                }}>
                  Requires one continuous good-time interval. For an observation with gaps, use GTI
                  Utilities to select a continuous interval first.
                </Typography>
                {formSchema.data ? (
                  <SchemaForm
                    schema={formSchema.data}
                    fields={[
                      { name: 'dt', value: dt, onChange: (value) => setDt(String(value)) },
                      { name: 'mode', value: mode, onChange: (value) => setMode(value as 'same' | 'full') },
                      { name: 'norm', value: norm, onChange: (value) => setNorm(value as 'none' | 'variance') },
                    ]}
                  />
                ) : formSchema.isError ? (
                  <Alert severity="error">{formSchema.error.message}</Alert>
                ) : (
                  <CircularProgress size={20} />
                )}
                <Typography variant="caption" sx={{
                  color: "text.secondary"
                }}>
                  {norm === 'variance'
                    ? "Variance normalization scales the correlation to roughly [-1, 1]."
                    : "Counts² scale (unnormalized correlation)."}
                  {' '}The time shift is always 0 for an auto-correlation by construction &mdash; it
                  is not shown as a measurement here.
                </Typography>
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
                  <>
                    <Chip size="small" label={`n = ${result.n}`} variant="outlined" />
                    <Chip size="small" label={`dt = ${result.dt} s`} variant="outlined" />
                    <Chip size="small" label={`mode: ${result.mode}`} variant="outlined" />
                  </>
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
                <PlotlyChart workspaceKey='QuickLook/AutoCorrelation/index.tsx:chart:1'                   data={traces}
                  layout={{
                    xaxis: { title: { text: 'Time lag (s)' } },
                    yaxis: {
                      title: { text: result.norm === 'variance' ? 'Correlation (normalized)' : 'Correlation (counts²)' },
                    },
                    shapes: [
                      {
                        type: 'line',
                        xref: 'x',
                        x0: 0,
                        x1: 0,
                        yref: 'paper',
                        y0: 0,
                        y1: 1,
                        line: { width: 1, dash: 'dash' },
                      },
                    ],
                  }}
                />
              ) : (
                <Box sx={{ py: 10, textAlign: 'center' }}>
                  <Typography sx={{
                    color: "text.secondary"
                  }}>
                    Choose an event list and compute its auto-correlation.
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

export default AutoCorrelationPage;
