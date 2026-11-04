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
  Tab,
  Tabs,
  TextField,
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
import { timingApi, BispectrumData } from '@/api/timingApi';
import { parsePositiveNumber } from '@/utils/numbers';

const SCALE_OPTIONS = ['biased', 'unbiased'];
const WINDOW_OPTIONS = ['uniform', 'parzen', 'hamming', 'hanning', 'triangular', 'welch', 'blackmann', 'flat-top'];
const MAXLAG_CAP = 500;

const BispectrumPage: React.FC = () => {
  const [eventList, setEventList] = useWorkspaceState('QuickLook/Bispectrum/index.tsx:eventList:1', '');
  const { draft: selectionDraft, setDraft: setSelectionDraft, selection, error: selectionError } =
    useEventSelection('QuickLook/Bispectrum/index.tsx:selection');
  const [dt, setDt] = useWorkspaceState('QuickLook/Bispectrum/index.tsx:dt:2', '0.1');
  const [maxlag, setMaxlag] = useWorkspaceState('QuickLook/Bispectrum/index.tsx:maxlag:3', '25');
  const [scale, setScale] = useWorkspaceState('QuickLook/Bispectrum/index.tsx:scale:4', 'unbiased');
  const [windowFn, setWindowFn] = useWorkspaceState('QuickLook/Bispectrum/index.tsx:windowFn:5', 'uniform');
  const [outputName, setOutputName] = useWorkspaceState('QuickLook/Bispectrum/index.tsx:outputName:6', '');
  const [tab, setTab] = useWorkspaceState('QuickLook/Bispectrum/index.tsx:tab:7', 0);
  const [logZ, setLogZ] = useWorkspaceState('QuickLook/Bispectrum/index.tsx:logZ:8', true);
  const {
    result, running, error, run, resultInputs, resultIdentity, resultStatus, backendAvailable,
  } = useAnalysisRunner<BispectrumData>('Bispectrum');

  const dtNum = parsePositiveNumber(dt);
  const maxlagNum = parsePositiveNumber(maxlag);
  const maxlagInt = maxlagNum === null ? null : Math.round(maxlagNum);
  const maxlagValid = maxlagInt !== null && maxlagInt >= 1 && maxlagInt <= MAXLAG_CAP;
  const canRun = selectionError === null && eventList !== '' && dtNum !== null && maxlagValid && !running && backendAvailable;
  const requestParams = {
    event_list_name: eventList,
    ...(selection ? { selection } : {}),
    dt: dtNum,
    maxlag: maxlagInt,
    scale,
    window: windowFn,
    output_name: outputName.trim() || undefined,
  };
  const currentInputs = { operation: 'bispectrum', ...requestParams };

  const handleRun = (): void => {
    if (!canRun || dtNum === null || maxlagInt === null) return;
    const params = { ...requestParams, dt: dtNum, maxlag: maxlagInt };
    void run(() => timingApi.createBispectrum(params), { operation: 'bispectrum', ...params });
  };

  const heatmapData = useMemo<Data[]>(() => {
    if (!result) return [];
    if (tab === 0) {
      const z = logZ
        ? result.bispec_mag.map((row) => row.map((v) => (v > 0 ? Math.log10(v) : null)))
        : result.bispec_mag;
      return [
        {
          z,
          x: result.freq,
          y: result.freq,
          type: 'heatmap',
          colorscale: 'Viridis',
          colorbar: { title: { text: logZ ? 'log10 |B|' : '|B|' } },
        } as Data,
      ];
    }
    return [
      {
        z: result.bispec_phase,
        x: result.freq,
        y: result.freq,
        type: 'heatmap',
        colorscale: 'RdBu',
        zmid: 0,
        colorbar: { title: { text: 'Phase (rad)' } },
      } as Data,
    ];
  }, [result, tab, logZ]);

  return (
    <PageTemplate
      title="Bispectrum"
      description="Third-order spectrum revealing nonlinear interactions and phase coupling"
      category="Advanced Analysis"
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
                <TextField
                  label="Time bin dt (s)"
                  size="small"
                  value={dt}
                  onChange={(e) => setDt(e.target.value)}
                  error={dt !== '' && dtNum === null}
                  helperText={dt !== '' && dtNum === null ? 'Must be a positive number' : ' '}
                />
                <TextField
                  label="Max lag (bins)"
                  size="small"
                  value={maxlag}
                  onChange={(e) => setMaxlag(e.target.value)}
                  error={maxlag !== '' && !maxlagValid}
                  helperText={
                    maxlag !== '' && !maxlagValid
                      ? 'Integer between 1 and 500'
                      : 'Bispectrum size is (2·maxlag+1)²; keep ≤ 100'
                  }
                />
                <FormControl size="small">
                  <InputLabel id="bs-scale-label">Scale</InputLabel>
                  <Select
                    labelId="bs-scale-label"
                    label="Scale"
                    value={scale}
                    onChange={(e) => setScale(e.target.value)}
                  >
                    {SCALE_OPTIONS.map((s) => (
                      <MenuItem key={s} value={s}>
                        {s}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small">
                  <InputLabel id="bs-window-label">Window</InputLabel>
                  <Select
                    labelId="bs-window-label"
                    label="Window"
                    value={windowFn}
                    onChange={(e) => setWindowFn(e.target.value)}
                  >
                    {WINDOW_OPTIONS.map((w) => (
                      <MenuItem key={w} value={w}>
                        {w}
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
                <Tabs value={tab} onChange={(_e, v: number) => setTab(v)} sx={{ flexGrow: 1 }}>
                  <Tab label="Magnitude" />
                  <Tab label="Phase" />
                </Tabs>
                {result && <Chip size="small" label={`maxlag ${result.maxlag}`} variant="outlined" />}
                {result && <Chip size="small" label={result.window} variant="outlined" />}
                {tab === 0 && (
                  <FormControlLabel
                    control={<Switch size="small" checked={logZ} onChange={(e) => setLogZ(e.target.checked)} />}
                    label="log color"
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
              {result ? (
                <PlotlyChart workspaceKey='QuickLook/Bispectrum/index.tsx:chart:1'                   data={heatmapData}
                  layout={{
                    xaxis: { title: { text: 'Frequency f1 (Hz)' } },
                    yaxis: { title: { text: 'Frequency f2 (Hz)' } },
                  }}
                  height={520}
                />
              ) : (
                <Box sx={{ py: 10, textAlign: 'center' }}>
                  <Typography sx={{
                    color: "text.secondary"
                  }}>
                    Compute a bispectrum to see magnitude and phase maps.
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

export default BispectrumPage;
