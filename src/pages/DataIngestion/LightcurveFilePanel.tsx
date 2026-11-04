import React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import GrantedFileField, { GrantedFileSelection } from '@/components/utilities/GrantedFileField';
import { lightcurveApi, LightcurveFileTable } from '@/api/lightcurveApi';
import { useBackendContext } from '@/context/BackendContext';
import { nameError } from '@/utils/derivedName';

const FITS_FILTERS = [
  { name: 'Light-curve FITS', extensions: ['lc', 'fits', 'fit', 'fts', 'lcurve'] },
];

/** Load a mission light curve (NICER, Swift-XRT, RXTE, OGIP tables) from a FITS file. */
const LightcurveFilePanel: React.FC = () => {
  const queryClient = useQueryClient();
  const { generation, isReady } = useBackendContext();
  const backendAvailable = generation === null || isReady;
  const [file, setFile] = React.useState<GrantedFileSelection | null>(null);
  const [tables, setTables] = React.useState<LightcurveFileTable[] | null>(null);
  const [tableIndex, setTableIndex] = React.useState<number | ''>('');
  const [rateColumn, setRateColumn] = React.useState('');
  const [band, setBand] = React.useState<number | ''>('');
  const [mjdref, setMjdref] = React.useState('');
  const [outputName, setOutputName] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [outcome, setOutcome] = React.useState<
    { severity: 'success' | 'error'; message: string } | null
  >(null);

  const table = tables?.find((candidate) => candidate.index === tableIndex) ?? null;
  // Times in seconds need the file's epoch; days-unit files state absolute times.
  const needsEpoch = table !== null && !table.has_mjdref && table.timeunit !== 'd';
  const mjdrefValue = Number(mjdref);
  const mjdrefValid = mjdref.trim() !== '' && Number.isFinite(mjdrefValue);
  const outputProblem = nameError(outputName);

  const chooseFile = async (selection: GrantedFileSelection | null): Promise<void> => {
    setFile(selection);
    setTables(null);
    setTableIndex('');
    setOutcome(null);
    if (!selection) return;
    const response = await lightcurveApi.inspectFile({
      file_path: selection.path,
      file_grant: selection.grant,
    });
    if (response.success && response.data) {
      const found = response.data.tables;
      setTables(found);
      setTableIndex(found[0]?.index ?? '');
      setRateColumn(found[0]?.rate_columns[0] ?? '');
      setBand(found[0] && found[0].n_bands > 1 ? 0 : '');
      if (!outputName) {
        const base = selection.path.split(/[\\/]/).pop() ?? 'lightcurve';
        setOutputName(base.replace(/\.[^.]+$/, '').replace(/[^A-Za-z0-9 _.-]/g, '_').slice(0, 64));
      }
    } else {
      setOutcome({ severity: 'error', message: response.message || 'Not a light-curve file' });
    }
  };

  const canLoad =
    backendAvailable &&
    !busy &&
    file !== null &&
    table !== null &&
    outputProblem === null &&
    (!needsEpoch || mjdrefValid);

  const load = async (): Promise<void> => {
    if (!canLoad || !file || !table) return;
    setBusy(true);
    setOutcome(null);
    const response = await lightcurveApi.loadFromFile({
      file_path: file.path,
      file_grant: file.grant,
      output_name: outputName,
      hdu: table.index,
      rate_column: rateColumn || undefined,
      ...(band === '' ? {} : { band }),
      ...(needsEpoch ? { mjdref: mjdrefValue } : {}),
    });
    setBusy(false);
    if (response.success && response.data) {
      setOutcome({
        severity: 'success',
        message: `${response.message} It is available on every page that uses stored light curves.`,
      });
      void queryClient.invalidateQueries({ queryKey: ['lightcurves'] });
    } else {
      setOutcome({ severity: 'error', message: response.message || response.error || 'Failed' });
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <ShowChartIcon sx={{ fontSize: 32, color: 'primary.main', mr: 1 }} />
        <Typography variant="h6">Load Light Curve</Typography>
      </Box>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
        Read a binned light curve from a mission FITS file (NICER, Swift-XRT, RXTE or any OGIP
        RATE/COUNTS table). TIMEZERO, MJDREF, TIMEUNIT, GTIs and error columns are respected.
      </Typography>
      <Stack spacing={2} sx={{ maxWidth: 640 }}>
        <GrantedFileField
          label="Light-curve FITS file"
          value={file}
          onChange={(selection) => void chooseFile(selection)}
          filters={FITS_FILTERS}
          disabled={!backendAvailable}
        />
        {tables && tables.length > 1 && (
          <FormControl size="small">
            <InputLabel id="lc-file-table">Table</InputLabel>
            <Select
              labelId="lc-file-table"
              label="Table"
              value={tableIndex}
              onChange={(event) => {
                const next = tables.find((candidate) => candidate.index === event.target.value);
                setTableIndex(event.target.value as number);
                setRateColumn(next?.rate_columns[0] ?? '');
                setBand(next && next.n_bands > 1 ? 0 : '');
              }}
            >
              {tables.map((candidate) => (
                <MenuItem key={candidate.index} value={candidate.index}>
                  HDU {candidate.index} · {candidate.name} ({candidate.n_rows} rows)
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
        {table && (
          <>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {[table.telescope, table.instrument].filter(Boolean).join(' / ') || 'Unknown mission'}
              {' · '}HDU {table.index} {table.name} · {table.n_rows} bins · times in{' '}
              {table.timeunit === 'd' ? 'days' : 'seconds'}
            </Typography>
            {table.rate_columns.length > 1 && (
              <FormControl size="small">
                <InputLabel id="lc-file-column">Rate column</InputLabel>
                <Select
                  labelId="lc-file-column"
                  label="Rate column"
                  value={rateColumn}
                  onChange={(event) => setRateColumn(event.target.value)}
                >
                  {table.rate_columns.map((column) => (
                    <MenuItem key={column} value={column}>
                      {column}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            {table.n_bands > 1 && (
              <FormControl size="small">
                <InputLabel id="lc-file-band">Energy band</InputLabel>
                <Select
                  labelId="lc-file-band"
                  label="Energy band"
                  value={band}
                  onChange={(event) => setBand(event.target.value as number)}
                >
                  {Array.from({ length: table.n_bands }, (_, index) => (
                    <MenuItem key={index} value={index}>
                      Band {index}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            {needsEpoch && (
              <TextField
                label="Reference epoch MJDREF"
                size="small"
                value={mjdref}
                onChange={(event) => setMjdref(event.target.value)}
                error={mjdref !== '' && !mjdrefValid}
                helperText="This file has no MJDREF; enter the mission's reference MJD"
              />
            )}
            <TextField
              label="Store as"
              size="small"
              value={outputName}
              onChange={(event) => setOutputName(event.target.value)}
              error={outputName !== '' && outputProblem !== null}
              helperText={outputName !== '' && outputProblem ? outputProblem : ' '}
            />
            <Box>
              <Button
                variant="contained"
                onClick={() => void load()}
                disabled={!canLoad}
                startIcon={busy ? <CircularProgress size={16} color="inherit" /> : <ShowChartIcon />}
              >
                Load light curve
              </Button>
            </Box>
          </>
        )}
        {outcome && <Alert severity={outcome.severity}>{outcome.message}</Alert>}
      </Stack>
    </Box>
  );
};

export default LightcurveFilePanel;
