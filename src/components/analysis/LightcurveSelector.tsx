import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert, FormControl, InputLabel, MenuItem, Select } from '@mui/material';
import { lightcurveApi } from '@/api/lightcurveApi';
import { useBackendContext } from '@/context/BackendContext';
import { captureBackendEpoch } from '@/api/backendEpoch';

interface LightcurveSelectorProps {
  label: string;
  value: string;
  onChange: (name: string) => void;
}

/** Dropdown of light curves stored in the backend (computed or loaded from files). */
const LightcurveSelector: React.FC<LightcurveSelectorProps> = ({ label, value, onChange }) => {
  const { generation, isReady } = useBackendContext();
  const epoch = captureBackendEpoch().version;
  const labelId = `lightcurve-selector-${React.useId()}`;
  const { data, isError, error } = useQuery({
    queryKey: ['lightcurves', generation, epoch],
    enabled: generation === null || isReady,
    queryFn: async () => {
      const response = await lightcurveApi.listLightcurves();
      if (!response.success) throw new Error(response.error || response.message);
      return response.data ?? [];
    },
  });
  if (isError) return <Alert severity="error">{error.message}</Alert>;
  if (data && data.length === 0) {
    return (
      <Alert severity="info">
        No light curves stored. Generate one on the Light Curve page or load one in Data
        Ingestion.
      </Alert>
    );
  }
  return (
    <FormControl size="small" fullWidth>
      <InputLabel id={labelId}>{label}</InputLabel>
      <Select
        labelId={labelId}
        label={label}
        value={data?.some((curve) => curve.name === value) ? value : ''}
        onChange={(event) => onChange(event.target.value)}
      >
        {(data ?? []).map((curve) => (
          <MenuItem key={curve.name} value={curve.name}>
            {curve.name} ({curve.n_bins.toLocaleString()} bins, dt = {curve.dt} s)
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

export default LightcurveSelector;
