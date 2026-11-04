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
import { varenergyApi, RmsSpectrumData } from '@/api/varenergyApi';
import { parsePositiveNumber } from '@/utils/numbers';

type RmsNorm = 'frac' | 'abs';

const RmsEnergySpectrumPage: React.FC = () => {
  const [eventList, setEventList] = useWorkspaceState('QuickLook/RmsEnergySpectrum/index.tsx:eventList:1', '');
  const [binTime, setBinTime] = useWorkspaceState('QuickLook/RmsEnergySpectrum/index.tsx:binTime:2', '0.1');
  const [segmentSize, setSegmentSize] = useWorkspaceState('QuickLook/RmsEnergySpectrum/index.tsx:segmentSize:3', '8');
  const [freqMin, setFreqMin] = useWorkspaceState('QuickLook/RmsEnergySpectrum/index.tsx:freqMin:4', '0.1');
  const [freqMax, setFreqMax] = useWorkspaceState('QuickLook/RmsEnergySpectrum/index.tsx:freqMax:5', '1');
  const [energyMin, setEnergyMin] = useWorkspaceState('QuickLook/RmsEnergySpectrum/index.tsx:energyMin:6', '0.5');
  const [energyMax, setEnergyMax] = useWorkspaceState('QuickLook/RmsEnergySpectrum/index.tsx:energyMax:7', '10');
  const [nBands, setNBands] = useWorkspaceState('QuickLook/RmsEnergySpectrum/index.tsx:nBands:8', '5');
  const [logBands, setLogBands] = useWorkspaceState('QuickLook/RmsEnergySpectrum/index.tsx:logBands:9', false);
  const [norm, setNorm] = useWorkspaceState<RmsNorm>('QuickLook/RmsEnergySpectrum/index.tsx:norm:10', 'frac');

  const {
    result,
    running,
    error,
    run,
    resultInputs,
    resultIdentity,
    resultStatus,
    backendAvailable,
  } = useAnalysisRunner<RmsSpectrumData>('RMS Energy Spectrum');

  const binTimeNum = parsePositiveNumber(binTime);
  const segNum = parsePositiveNumber(segmentSize);
  const freqMinNum = parsePositiveNumber(freqMin);
  const freqMaxNum = parsePositiveNumber(freqMax);
  const energyMinNum = parsePositiveNumber(energyMin);
  const energyMaxNum = parsePositiveNumber(energyMax);
  const nBandsNum = parsePositiveNumber(nBands);
  const nBandsValid = nBandsNum !== null && Number.isInteger(nBandsNum) && nBandsNum >= 2;

  const freqRangeInverted =
    freqMinNum !== null && freqMaxNum !== null && freqMaxNum <= freqMinNum;
  const energyRangeInverted =
    energyMinNum !== null && energyMaxNum !== null && energyMaxNum <= energyMinNum;

  const currentInputs = {
    operation: 'rms_energy_spectrum',
    event_list_name: eventList,
    bin_time: binTimeNum,
    segment_size: segNum,
    freq_min: freqMinNum,
    freq_max: freqMaxNum,
    energy_min: energyMinNum,
    energy_max: energyMaxNum,
    n_bands: nBandsNum,
    log_bands: logBands,
    norm,
  };

  const canRun =
    backendAvailable &&
    eventList !== '' &&
    binTimeNum !== null &&
    segNum !== null &&
    freqMinNum !== null &&
    freqMaxNum !== null &&
    !freqRangeInverted &&
    energyMinNum !== null &&
    energyMaxNum !== null &&
    !energyRangeInverted &&
    nBandsValid &&
    !running;

  const handleRun = (): void => {
    if (!canRun) return;
    if (
      binTimeNum === null ||
      segNum === null ||
      freqMinNum === null ||
      freqMaxNum === null ||
      energyMinNum === null ||
      energyMaxNum === null ||
      nBandsNum === null
    ) {
      return;
    }
    const parameters = {
      event_list_name: eventList,
      bin_time: binTimeNum,
      segment_size: segNum,
      freq_min: freqMinNum,
      freq_max: freqMaxNum,
      energy_min: energyMinNum,
      energy_max: energyMaxNum,
      n_bands: nBandsNum,
      log_bands: logBands,
      norm,
    };
    void run(
      () => varenergyApi.rmsSpectrum(parameters),
      { operation: 'rms_energy_spectrum', ...parameters }
    );
  };

  const finiteSpectrum = result ? result.spectrum.filter((v): v is number => v !== null) : [];
  const allNull = result !== null && result.spectrum.length > 0 && finiteSpectrum.length === 0;

  const traces: Data[] = result
    ? [
        {
          x: result.energy,
          y: result.spectrum,
          type: 'scattergl',
          mode: 'markers',
          marker: { size: 7, color: '#00d4aa' },
          error_y: {
            type: 'data',
            array: result.spectrum_error,
            visible: true,
            color: 'rgba(0, 212, 170, 0.35)',
          },
        } as Data,
      ]
    : [];

  const yAxisLabel = result?.norm === 'abs' ? 'Absolute rms (counts/s)' : 'Fractional rms';

  return (
    <PageTemplate
      title="RMS Energy Spectrum"
      description="Fractional or absolute rms as a function of energy"
      category="Energy Dependent Analysis"
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
                  value={binTime}
                  onChange={(e) => setBinTime(e.target.value)}
                  error={binTime !== '' && binTimeNum === null}
                  helperText={binTime !== '' && binTimeNum === null ? 'Must be a positive number' : ' '}
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
                    error={(freqMin !== '' && freqMinNum === null) || freqRangeInverted}
                    helperText={
                      freqMin !== '' && freqMinNum === null
                        ? 'Must be a positive number'
                        : freqRangeInverted
                          ? 'f max must be > f min'
                          : ' '
                    }
                  />
                  <TextField
                    label="f max (Hz)"
                    size="small"
                    value={freqMax}
                    onChange={(e) => setFreqMax(e.target.value)}
                    error={(freqMax !== '' && freqMaxNum === null) || freqRangeInverted}
                    helperText={
                      freqMax !== '' && freqMaxNum === null
                        ? 'Must be a positive number'
                        : freqRangeInverted
                          ? 'f max must be > f min'
                          : ' '
                    }
                  />
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    label="Energy min (keV)"
                    size="small"
                    value={energyMin}
                    onChange={(e) => setEnergyMin(e.target.value)}
                    error={(energyMin !== '' && energyMinNum === null) || energyRangeInverted}
                    helperText={
                      energyMin !== '' && energyMinNum === null
                        ? 'Must be a positive number'
                        : energyRangeInverted
                          ? 'max must be > min'
                          : ' '
                    }
                  />
                  <TextField
                    label="Energy max (keV)"
                    size="small"
                    value={energyMax}
                    onChange={(e) => setEnergyMax(e.target.value)}
                    error={(energyMax !== '' && energyMaxNum === null) || energyRangeInverted}
                    helperText={
                      energyMax !== '' && energyMaxNum === null
                        ? 'Must be a positive number'
                        : energyRangeInverted
                          ? 'max must be > min'
                          : ' '
                    }
                  />
                </Box>
                <TextField
                  label="Number of energy bands"
                  size="small"
                  value={nBands}
                  onChange={(e) => setNBands(e.target.value)}
                  error={nBands !== '' && !nBandsValid}
                  helperText={nBands !== '' && !nBandsValid ? 'Must be an integer >= 2' : ' '}
                />
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={logBands}
                      onChange={(e) => setLogBands(e.target.checked)}
                    />
                  }
                  label="Log-spaced energy bands"
                />
                <FormControl size="small" fullWidth>
                  <InputLabel id="rms-norm-label">Normalization</InputLabel>
                  <Select
                    labelId="rms-norm-label"
                    label="Normalization"
                    value={norm}
                    onChange={(e) => setNorm(e.target.value as RmsNorm)}
                  >
                    <MenuItem value="frac">Fractional</MenuItem>
                    <MenuItem value="abs">Absolute</MenuItem>
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
                {result && (
                  <>
                    <Chip
                      size="small"
                      variant="outlined"
                      label={`${result.freq_range[0]}–${result.freq_range[1]} Hz`}
                    />
                    <Chip size="small" variant="outlined" label={`norm: ${result.norm}`} />
                    <Chip
                      size="small"
                      variant="outlined"
                      label={`≈ ${result.n_segments_hint} segments`}
                    />
                  </>
                )}
              </Box>
              <AnalysisResultIdentity
                inputs={resultInputs}
                identity={resultIdentity}
                status={resultStatus}
                currentInputs={currentInputs}
              />
              {error && (
                <Alert severity="error" sx={{ mb: 1 }}>
                  {error}
                </Alert>
              )}
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
                allNull ? (
                  <Box sx={{ py: 10, textAlign: 'center' }}>
                    <Typography sx={{
                      color: "text.secondary"
                    }}>
                      No finite rms values in any energy band. See the warnings above for why (e.g. low
                      count rate) and try a coarser bin, fewer bands, or a wider segment.
                    </Typography>
                  </Box>
                ) : (
                  <PlotlyChart workspaceKey='QuickLook/RmsEnergySpectrum/index.tsx:chart:1'                     data={traces}
                    layout={{
                      xaxis: { title: { text: 'Energy (keV)' } },
                      yaxis: { title: { text: yAxisLabel }, type: 'linear' },
                    }}
                  />
                )
              ) : (
                <Box sx={{ py: 10, textAlign: 'center' }}>
                  <Typography sx={{
                    color: "text.secondary"
                  }}>
                    Choose an event list and compute the rms-energy spectrum.
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

export default RmsEnergySpectrumPage;
