import { useWorkspaceState } from '@/api/workspaceSession';
import React, {} from 'react';
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
  FormLabel,
  Grid,
  InputLabel,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
  useTheme,
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
import { deadtimeApi, PdsCorrectionData, FadCorrectionData } from '@/api/deadtimeApi';
import { parsePositiveNumber } from '@/utils/numbers';
import {
  UNPHYSICAL_DETECTED_RATE_MESSAGE,
  deadTimeLossFraction,
  detectedRateFromIncident,
  incidentRateFromDetected,
  parseNonNegativeNumber,
} from '@/utils/deadtime';

const FAD_NORMS = ['frac', 'leahy', 'abs', 'none'];

/** Leahy white-noise power of a dead-time-free Poisson process. */
const LEAHY_WHITE_NOISE = 2;

const format = (value: number | null, digits: number): string =>
  value === null || !Number.isFinite(value) ? '—' : value.toFixed(digits);

/** Backend advisories rendered inside a warning Alert. */
const WarningLines: React.FC<{ warnings: string[] }> = ({ warnings }) => (
  <>
    {warnings.map((warning, index) => (
      <Typography key={`${index}-${warning}`} variant="body2">
        {warning}
      </Typography>
    ))}
  </>
);

const DeadTimeCorrectionsPage: React.FC = () => {
  const theme = useTheme();
  const referenceLineColor = theme.palette.text.secondary;

  // Panel (a) — client-side rate calculator
  const [rateMode, setRateMode] = useWorkspaceState<'incident' | 'detected'>('QuickLook/DeadTimeCorrections/index.tsx:rateMode:1', 'incident');
  const [knownRate, setKnownRate] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:knownRate:2', '300');
  const [calculatorDeadTime, setCalculatorDeadTime] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:calculatorDeadTime:3', '0.0025');

  // Panel (b) — model (Zhang+95) PDS correction
  const [pdsEventList, setPdsEventList] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:pdsEventList:4', '');
  const pdsSelection = useEventSelection('QuickLook/DeadTimeCorrections/index.tsx:pdsSelection');
  const [pdsDt, setPdsDt] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:pdsDt:5', '0.001');
  const [pdsSegmentSize, setPdsSegmentSize] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:pdsSegmentSize:6', '20');
  const [pdsDeadTime, setPdsDeadTime] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:pdsDeadTime:7', '0.0025');
  const [pdsBackgroundRate, setPdsBackgroundRate] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:pdsBackgroundRate:8', '0');
  const [pdsLimitK, setPdsLimitK] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:pdsLimitK:9', '200');
  const [pdsLogAxes, setPdsLogAxes] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:pdsLogAxes:10', true);

  // Panel (c) — FAD correction
  const [fadEventList1, setFadEventList1] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:fadEventList1:11', '');
  const [fadEventList2, setFadEventList2] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:fadEventList2:12', '');
  const fadSelection1 = useEventSelection('QuickLook/DeadTimeCorrections/index.tsx:fadSelection1');
  const fadSelection2 = useEventSelection('QuickLook/DeadTimeCorrections/index.tsx:fadSelection2');
  const [fadDt, setFadDt] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:fadDt:13', '0.001');
  const [fadSegmentSize, setFadSegmentSize] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:fadSegmentSize:14', '8');
  const [fadNorm, setFadNorm] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:fadNorm:15', 'frac');
  const [fadSmoothingLength, setFadSmoothingLength] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:fadSmoothingLength:16', '');
  const [showCospectrum, setShowCospectrum] = useWorkspaceState('QuickLook/DeadTimeCorrections/index.tsx:showCospectrum:17', false);
  const fadNormLabelId = React.useId();

  const {
    result: pdsResult,
    running: pdsRunning,
    error: pdsError,
    resultInputs: pdsResultInputs,
    resultIdentity: pdsResultIdentity,
    resultStatus: pdsResultStatus,
    backendAvailable: pdsBackendAvailable,
    run: runPds,
  } = useAnalysisRunner<PdsCorrectionData>('Dead-time PDS Correction');
  const {
    result: fadResult,
    running: fadRunning,
    error: fadError,
    resultInputs: fadResultInputs,
    resultIdentity: fadResultIdentity,
    resultStatus: fadResultStatus,
    backendAvailable: fadBackendAvailable,
    run: runFad,
  } = useAnalysisRunner<FadCorrectionData>('FAD Correction');

  // --- Panel (a): pure client-side rate conversions -------------------------
  const knownRateNum = parseNonNegativeNumber(knownRate);
  const calculatorDeadTimeNum = parseNonNegativeNumber(calculatorDeadTime);
  const calculatorInputsValid = knownRateNum !== null && calculatorDeadTimeNum !== null;
  const incidentRate =
    knownRateNum === null || calculatorDeadTimeNum === null
      ? null
      : rateMode === 'incident'
        ? knownRateNum
        : incidentRateFromDetected(knownRateNum, calculatorDeadTimeNum);
  const detectedRate =
    knownRateNum === null || calculatorDeadTimeNum === null
      ? null
      : rateMode === 'detected'
        ? knownRateNum
        : detectedRateFromIncident(knownRateNum, calculatorDeadTimeNum);
  const occupancyUnphysical =
    rateMode === 'detected' && calculatorInputsValid && incidentRate === null;
  const lossFraction =
    incidentRate !== null && detectedRate !== null
      ? deadTimeLossFraction(incidentRate, detectedRate)
      : null;

  // --- Panel (b): model correction ------------------------------------------
  const pdsDtNum = parsePositiveNumber(pdsDt);
  const pdsSegmentNum = parsePositiveNumber(pdsSegmentSize);
  const pdsDeadTimeNum = parsePositiveNumber(pdsDeadTime);
  const pdsBackgroundNum = parseNonNegativeNumber(pdsBackgroundRate);
  const pdsLimitKNum = parsePositiveNumber(pdsLimitK);
  const pdsLimitKValid = pdsLimitKNum !== null && Number.isInteger(pdsLimitKNum);
  const canRunPds =
    pdsSelection.error === null &&
    pdsEventList !== '' &&
    pdsDtNum !== null &&
    pdsSegmentNum !== null &&
    pdsDeadTimeNum !== null &&
    pdsBackgroundNum !== null &&
    pdsLimitKValid &&
    pdsBackendAvailable &&
    !pdsRunning;

  const pdsCurrentInputs = {
    operation: 'pds_correction',
    event_list_name: pdsEventList,
    ...(pdsSelection.selection ? { selection: pdsSelection.selection } : {}),
    dt: pdsDtNum,
    segment_size: pdsSegmentNum,
    dead_time: pdsDeadTimeNum,
    background_rate: pdsBackgroundNum,
    limit_k: pdsLimitKNum,
  };

  const handleRunPds = (): void => {
    if (
      pdsDtNum === null ||
      pdsSegmentNum === null ||
      pdsDeadTimeNum === null ||
      pdsBackgroundNum === null ||
      pdsLimitKNum === null ||
      !canRunPds
    ) {
      return;
    }
    const params = {
      event_list_name: pdsEventList,
      ...(pdsSelection.selection ? { selection: pdsSelection.selection } : {}),
      dt: pdsDtNum,
      segment_size: pdsSegmentNum,
      dead_time: pdsDeadTimeNum,
      background_rate: pdsBackgroundNum,
      limit_k: pdsLimitKNum,
    };
    void runPds(
      () => deadtimeApi.pdsCorrection(params),
      { operation: 'pds_correction', ...params }
    );
  };

  const pdsTraces: Data[] = pdsResult
    ? [
        {
          x: pdsResult.freq,
          y: pdsResult.power_uncorrected,
          type: 'scattergl',
          mode: 'lines',
          line: { width: 1 },
          name: 'Uncorrected',
        } as Data,
        {
          x: pdsResult.freq,
          y: pdsResult.power_corrected,
          type: 'scattergl',
          mode: 'lines',
          line: { width: 1 },
          name: 'Dead-time corrected',
        } as Data,
      ]
    : [];

  // Shape coordinates use raw data values on log axes in this plotly version
  // (verified live: passing log10(2) rendered the line at y=0.3, not y=2).
  const leahyLineY = LEAHY_WHITE_NOISE;

  // --- Panel (c): FAD correction --------------------------------------------
  const fadDtNum = parsePositiveNumber(fadDt);
  const fadSegmentNum = parsePositiveNumber(fadSegmentSize);
  const fadSmoothingNum = parsePositiveNumber(fadSmoothingLength);
  const fadSmoothingInvalid = fadSmoothingLength !== '' && fadSmoothingNum === null;
  const fadListsIdentical = fadEventList1 !== '' && fadEventList1 === fadEventList2;
  const canRunFad =
    fadSelection1.error === null &&
    fadSelection2.error === null &&
    fadEventList1 !== '' &&
    fadEventList2 !== '' &&
    !fadListsIdentical &&
    fadDtNum !== null &&
    fadSegmentNum !== null &&
    !fadSmoothingInvalid &&
    fadBackendAvailable &&
    !fadRunning;

  const fadCurrentInputs = {
    operation: 'fad_correction',
    event_list_1_name: fadEventList1,
    event_list_2_name: fadEventList2,
    ...(fadSelection1.selection ? { selection_1: fadSelection1.selection } : {}),
    ...(fadSelection2.selection ? { selection_2: fadSelection2.selection } : {}),
    dt: fadDtNum,
    segment_size: fadSegmentNum,
    norm: fadNorm,
    smoothing_length: fadSmoothingNum,
  };

  const handleRunFad = (): void => {
    if (fadDtNum === null || fadSegmentNum === null || !canRunFad)
      return;
    const params = {
      event_list_1_name: fadEventList1,
      event_list_2_name: fadEventList2,
      ...(fadSelection1.selection ? { selection_1: fadSelection1.selection } : {}),
      ...(fadSelection2.selection ? { selection_2: fadSelection2.selection } : {}),
      dt: fadDtNum,
      segment_size: fadSegmentNum,
      norm: fadNorm,
      smoothing_length: fadSmoothingNum,
    };
    void runFad(
      () => deadtimeApi.fadCorrection(params),
      { operation: 'fad_correction', ...params }
    );
  };

  const fadTraces: Data[] = fadResult
    ? [
        {
          x: fadResult.freq,
          y: fadResult.pds1,
          type: 'scattergl',
          mode: 'lines',
          line: { width: 1 },
          name: 'PDS 1',
        } as Data,
        {
          x: fadResult.freq,
          y: fadResult.pds2,
          type: 'scattergl',
          mode: 'lines',
          line: { width: 1 },
          name: 'PDS 2',
        } as Data,
        {
          x: fadResult.freq,
          y: fadResult.ptot,
          type: 'scattergl',
          mode: 'lines',
          line: { width: 1 },
          name: 'Total PDS',
        } as Data,
        ...(showCospectrum
          ? [
              {
                x: fadResult.freq,
                y: fadResult.cs_real,
                type: 'scattergl',
                mode: 'lines',
                line: { width: 1 },
                name: 'Re[CS] (signed cospectrum)',
              } as Data,
            ]
          : []),
      ]
    : [];

  const fadSegmentsLow = fadResult !== null && fadResult.n_segments < 30;
  const fadNonCompliant = fadResult !== null && fadResult.is_compliant === false;

  return (
    <PageTemplate
      title="Dead Time Corrections"
      description="Convert incident and detected count rates, correct an averaged power spectrum with the Zhang+95 dead-time model, and cross-correct two detectors with FAD"
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
          <Stack spacing={3}>
            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2}>
                  <Typography variant="subtitle2">Model correction parameters</Typography>
                  <EventListSelector
                    label="Event list"
                    value={pdsEventList}
                    onChange={setPdsEventList}
                  />
                  <EventSelectionField
                    eventListName={pdsEventList}
                    value={pdsSelection.draft}
                    onChange={pdsSelection.setDraft}
                  />
                  <TextField
                    label="PDS dt (s)"
                    size="small"
                    value={pdsDt}
                    onChange={(e) => setPdsDt(e.target.value)}
                    error={pdsDt !== '' && pdsDtNum === null}
                    helperText={pdsDt !== '' && pdsDtNum === null ? 'Must be a positive number' : ' '}
                  />
                  <TextField
                    label="PDS segment size (s)"
                    size="small"
                    value={pdsSegmentSize}
                    onChange={(e) => setPdsSegmentSize(e.target.value)}
                    error={pdsSegmentSize !== '' && pdsSegmentNum === null}
                    helperText={
                      pdsSegmentSize !== '' && pdsSegmentNum === null
                        ? 'Must be a positive number'
                        : 'At least 3 × dt, at most the total exposure'
                    }
                  />
                  <TextField
                    label="Detector dead time (s)"
                    size="small"
                    value={pdsDeadTime}
                    onChange={(e) => setPdsDeadTime(e.target.value)}
                    error={pdsDeadTime !== '' && pdsDeadTimeNum === null}
                    helperText={
                      pdsDeadTime !== '' && pdsDeadTimeNum === null
                        ? 'Must be a positive number'
                        : ' '
                    }
                  />
                  <TextField
                    label="Background rate (c/s)"
                    size="small"
                    value={pdsBackgroundRate}
                    onChange={(e) => setPdsBackgroundRate(e.target.value)}
                    error={pdsBackgroundRate !== '' && pdsBackgroundNum === null}
                    helperText={
                      pdsBackgroundRate !== '' && pdsBackgroundNum === null
                        ? 'Must be zero or a positive number'
                        : ' '
                    }
                  />
                  <TextField
                    label="Correction terms (limit_k)"
                    size="small"
                    value={pdsLimitK}
                    onChange={(e) => setPdsLimitK(e.target.value)}
                    error={pdsLimitK !== '' && !pdsLimitKValid}
                    helperText={
                      pdsLimitK !== '' && !pdsLimitKValid ? 'Must be a positive integer' : ' '
                    }
                  />
                  <Button
                    variant="contained"
                    startIcon={
                      pdsRunning ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />
                    }
                    disabled={!canRunPds}
                    onClick={handleRunPds}
                  >
                    Compute correction
                  </Button>
                </Stack>
              </CardContent>
            </Card>

            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2}>
                  <Typography variant="subtitle2">FAD parameters</Typography>
                  <EventListSelector
                    label="Detector 1 event list"
                    value={fadEventList1}
                    onChange={setFadEventList1}
                  />
                  <EventSelectionField
                    label="Detector 1 photons"
                    eventListName={fadEventList1}
                    value={fadSelection1.draft}
                    onChange={fadSelection1.setDraft}
                  />
                  <EventListSelector
                    label="Detector 2 event list"
                    value={fadEventList2}
                    onChange={setFadEventList2}
                  />
                  <EventSelectionField
                    label="Detector 2 photons"
                    eventListName={fadEventList2}
                    value={fadSelection2.draft}
                    onChange={fadSelection2.setDraft}
                  />
                  {fadListsIdentical && (
                    <Alert severity="warning">
                      FAD needs two independent detectors observing the same source
                      simultaneously; the same list twice is not a valid input, even
                      with different energy bands, because one detector's bands share
                      its dead time.
                    </Alert>
                  )}
                  <TextField
                    label="FAD dt (s)"
                    size="small"
                    value={fadDt}
                    onChange={(e) => setFadDt(e.target.value)}
                    error={fadDt !== '' && fadDtNum === null}
                    helperText={fadDt !== '' && fadDtNum === null ? 'Must be a positive number' : ' '}
                  />
                  <TextField
                    label="FAD segment size (s)"
                    size="small"
                    value={fadSegmentSize}
                    onChange={(e) => setFadSegmentSize(e.target.value)}
                    error={fadSegmentSize !== '' && fadSegmentNum === null}
                    helperText={
                      fadSegmentSize !== '' && fadSegmentNum === null
                        ? 'Must be a positive number'
                        : 'Aim for 30 or more segments'
                    }
                  />
                  <FormControl size="small" fullWidth>
                    <InputLabel id={fadNormLabelId}>FAD normalization</InputLabel>
                    <Select
                      labelId={fadNormLabelId}
                      label="FAD normalization"
                      value={fadNorm}
                      onChange={(e) => setFadNorm(e.target.value)}
                    >
                      {FAD_NORMS.map((norm) => (
                        <MenuItem key={norm} value={norm}>
                          {norm}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <TextField
                    label="Smoothing sigma (bins)"
                    size="small"
                    value={fadSmoothingLength}
                    onChange={(e) => setFadSmoothingLength(e.target.value)}
                    error={fadSmoothingInvalid}
                    helperText={
                      fadSmoothingInvalid
                        ? 'Must be a positive number'
                        : 'Gaussian sigma in frequency bins; blank uses 3 × segment size'
                    }
                  />
                  <Button
                    variant="contained"
                    startIcon={
                      fadRunning ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />
                    }
                    disabled={!canRunFad}
                    onClick={handleRunFad}
                  >
                    Compute FAD
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        </Grid>

        <Grid
          size={{
            xs: 12,
            md: 8,
            lg: 9
          }}>
          <Stack spacing={3}>
            {/* (a) Rate calculator — no backend involved */}
            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2}>
                  <Typography variant="subtitle2">Rate calculator</Typography>
                  <Typography variant="caption" sx={{
                    color: "text.secondary"
                  }}>
                    Non-paralyzable detector: r_det = r_in / (1 + r_in · τ) and r_in = r_det /
                    (1 − r_det · τ). Computed in the browser, no analysis is run.
                  </Typography>
                  <FormControl>
                    <FormLabel id="dead-time-rate-mode">Known rate is</FormLabel>
                    <RadioGroup
                      row
                      aria-labelledby="dead-time-rate-mode"
                      value={rateMode}
                      onChange={(e) => setRateMode(e.target.value as 'incident' | 'detected')}
                    >
                      <FormControlLabel
                        value="incident"
                        control={<Radio size="small" />}
                        label="Incident"
                      />
                      <FormControlLabel
                        value="detected"
                        control={<Radio size="small" />}
                        label="Detected"
                      />
                    </RadioGroup>
                  </FormControl>
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <TextField
                      label="Known rate (c/s)"
                      size="small"
                      value={knownRate}
                      onChange={(e) => setKnownRate(e.target.value)}
                      error={(knownRate !== '' && knownRateNum === null) || occupancyUnphysical}
                      helperText={
                        occupancyUnphysical
                          ? UNPHYSICAL_DETECTED_RATE_MESSAGE
                          : knownRate !== '' && knownRateNum === null
                            ? 'Must be zero or a positive number'
                            : ' '
                      }
                    />
                    <TextField
                      label="Dead time (s)"
                      size="small"
                      value={calculatorDeadTime}
                      onChange={(e) => setCalculatorDeadTime(e.target.value)}
                      error={
                        (calculatorDeadTime !== '' && calculatorDeadTimeNum === null) ||
                        occupancyUnphysical
                      }
                      helperText={
                        calculatorDeadTime !== '' && calculatorDeadTimeNum === null
                          ? 'Must be zero or a positive number'
                          : ' '
                      }
                    />
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip
                      size="small"
                      variant="outlined"
                      label={`Incident: ${format(incidentRate, 2)} c/s`}
                    />
                    <Chip
                      size="small"
                      variant="outlined"
                      label={`Detected: ${format(detectedRate, 2)} c/s`}
                    />
                    <Chip
                      size="small"
                      variant="outlined"
                      label={`Dead-time loss: ${
                        lossFraction === null ? '—' : `${(lossFraction * 100).toFixed(1)}%`
                      }`}
                    />
                  </Box>
                </Stack>
              </CardContent>
            </Card>

            {/* (b) Model correction result */}
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                    Model correction (Zhang+95)
                  </Typography>
                  {pdsResult && (
                    <Chip
                      size="small"
                      variant="outlined"
                      label={`detected rate: ${format(pdsResult.rate, 2)} c/s`}
                    />
                  )}
                  {pdsResult && (
                    <Chip
                      size="small"
                      variant="outlined"
                      label={`${pdsResult.n_segments} segments`}
                    />
                  )}
                  <FormControlLabel
                    control={
                      <Switch
                        size="small"
                        checked={pdsLogAxes}
                        onChange={(e) => setPdsLogAxes(e.target.checked)}
                      />
                    }
                    label="log axes"
                  />
                </Box>
                <Typography variant="caption" sx={{
                  color: "text.secondary"
                }}>
                  Normalization fixed to Leahy (required by the Zhang+95 correction). The dashed
                  line marks the Leahy white-noise level of 2.
                </Typography>
                {pdsError && (
                  <Alert severity="error" sx={{ mt: 1, mb: 1 }}>
                    {pdsError}
                  </Alert>
                )}
                <AnalysisResultIdentity
                  inputs={pdsResultInputs}
                  identity={pdsResultIdentity}
                  status={pdsResultStatus}
                  currentInputs={pdsCurrentInputs}
                />
                {pdsResult && pdsResult.warnings.length > 0 && (
                  <Alert severity="warning" sx={{ mt: 1, mb: 1 }}>
                    <WarningLines warnings={pdsResult.warnings} />
                  </Alert>
                )}
                {pdsRunning && (
                  <Alert severity="info" sx={{ mt: 1, mb: 1 }}>
                    Correcting… the first run of a session also pays a one-off numba compile, so
                    this can take a few seconds.
                  </Alert>
                )}
                {pdsResult ? (
                  <PlotlyChart workspaceKey='QuickLook/DeadTimeCorrections/index.tsx:chart:1'                     data={pdsTraces}
                    layout={{
                      showlegend: true,
                      xaxis: {
                        title: { text: 'Frequency (Hz)' },
                        type: pdsLogAxes ? 'log' : 'linear',
                      },
                      yaxis: {
                        title: { text: 'Power (Leahy)' },
                        type: pdsLogAxes ? 'log' : 'linear',
                      },
                      shapes: [
                        {
                          type: 'line',
                          xref: 'paper',
                          x0: 0,
                          x1: 1,
                          yref: 'y',
                          y0: leahyLineY,
                          y1: leahyLineY,
                          line: { color: referenceLineColor, width: 1, dash: 'dash' },
                        },
                      ],
                    }}
                  />
                ) : (
                  <Box sx={{ py: 8, textAlign: 'center' }}>
                    <Typography sx={{
                      color: "text.secondary"
                    }}>
                      Choose an event list and compute the dead-time-corrected power spectrum.
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>

            {/* (c) FAD correction result */}
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                    FAD correction (two detectors)
                  </Typography>
                  {fadResult && (
                    <Chip
                      size="small"
                      variant="outlined"
                      color={fadSegmentsLow ? 'warning' : 'default'}
                      label={`${fadResult.n_segments} segments`}
                    />
                  )}
                  {fadResult && (
                    <Chip
                      size="small"
                      variant="outlined"
                      label={`FAD Δ: ${format(fadResult.fad_delta, 3)}`}
                    />
                  )}
                  <FormControlLabel
                    control={
                      <Switch
                        size="small"
                        checked={showCospectrum}
                        onChange={(e) => setShowCospectrum(e.target.checked)}
                      />
                    }
                    label="signed cospectrum"
                  />
                </Box>
                <Typography variant="caption" sx={{
                  color: "text.secondary"
                }}>
                  {showCospectrum
                    ? 'Re[CS] is signed, so the y axis is linear with a zero line while it is shown.'
                    : 'Corrected power spectra of each detector and of their sum, on log axes.'}
                </Typography>
                {fadError && (
                  <Alert severity="error" sx={{ mt: 1, mb: 1 }}>
                    {fadError}
                  </Alert>
                )}
                <AnalysisResultIdentity
                  inputs={fadResultInputs}
                  identity={fadResultIdentity}
                  status={fadResultStatus}
                  currentInputs={fadCurrentInputs}
                />
                {fadResult && (fadResult.warnings.length > 0 || fadNonCompliant) && (
                  <Alert
                    severity="warning"
                    variant={fadNonCompliant ? 'filled' : 'standard'}
                    sx={{ mt: 1, mb: 1 }}
                  >
                    {fadNonCompliant && (
                      <AlertTitle>
                        FAD self-check failed — the two event lists are probably not independent
                        simultaneous detectors
                      </AlertTitle>
                    )}
                    <WarningLines warnings={fadResult.warnings} />
                  </Alert>
                )}
                {fadRunning && (
                  <Alert severity="info" sx={{ mt: 1, mb: 1 }}>
                    Running FAD… the first run of a session also pays a one-off numba compile, so
                    this can take a few seconds.
                  </Alert>
                )}
                {fadResult ? (
                  <PlotlyChart workspaceKey='QuickLook/DeadTimeCorrections/index.tsx:chart:2'                     data={fadTraces}
                    layout={{
                      showlegend: true,
                      xaxis: { title: { text: 'Frequency (Hz)' }, type: 'log' },
                      yaxis: {
                        title: {
                          text: showCospectrum
                            ? `Power / Re[CS] (${fadResult.norm})`
                            : `Power (${fadResult.norm})`,
                        },
                        type: showCospectrum ? 'linear' : 'log',
                      },
                      shapes: showCospectrum
                        ? [
                            {
                              type: 'line',
                              xref: 'paper',
                              x0: 0,
                              x1: 1,
                              yref: 'y',
                              y0: 0,
                              y1: 0,
                              line: { color: referenceLineColor, width: 1, dash: 'dash' },
                            },
                          ]
                        : [],
                    }}
                  />
                ) : (
                  <Box sx={{ py: 8, textAlign: 'center' }}>
                    <Typography sx={{
                      color: "text.secondary"
                    }}>
                      Choose two simultaneous detector event lists and compute the FAD-corrected
                      spectra.
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Stack>
        </Grid>
      </Grid>
    </PageTemplate>
  );
};

export default DeadTimeCorrectionsPage;
