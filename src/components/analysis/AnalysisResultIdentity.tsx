import React from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Stack,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

interface ResultIdentity {
  resultId: string | null;
  backendGeneration: number | null;
  completedAt: string;
}

interface AnalysisResultIdentityProps {
  inputs: Readonly<Record<string, unknown>> | null;
  identity?: ResultIdentity | null;
  status: 'empty' | 'current' | 'previous' | 'stale';
  currentInputs?: Readonly<Record<string, unknown>> | null;
  result?: {
    name?: string | null;
    result_id?: string;
    backend_session_id?: string;
    inputs?: unknown;
    parameters?: unknown;
  } | null;
}

/** Canonicalize request values so key order and omitted optional fields agree. */
function canonicalValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([, item]) => item !== undefined)
        .sort(([first], [second]) => first.localeCompare(second))
        .map(([key, item]) => [key, canonicalValue(item)])
    );
  }
  return value;
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return 'Not specified';
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
}

/** Display the submitted snapshot, independent of the currently edited controls. */
const AnalysisResultIdentity: React.FC<AnalysisResultIdentityProps> = ({
  inputs,
  identity,
  status,
  currentInputs,
  result,
}) => {
  if (inputs === null || status === 'empty') return null;
  const inputsChanged = currentInputs !== null && currentInputs !== undefined &&
    JSON.stringify(canonicalValue(inputs)) !== JSON.stringify(canonicalValue(currentInputs));

  return (
    <Stack
      component="section"
      role="region"
      aria-label="Result identity"
      data-testid="analysis-result-identity"
      spacing={1}
      sx={{ mb: 1.5 }}
    >
      {status === 'stale' ? (
        <Alert severity="warning">
          This result belongs to a previous backend session and is read-only. Recompute it before
          using backend objects.
        </Alert>
      ) : status === 'previous' ? (
        <Alert severity="info">
          The latest request failed. Showing the previous successful result and its original inputs.
        </Alert>
      ) : null}
      {inputsChanged ? (
        <Alert severity="info">Inputs have changed since this result.</Alert>
      ) : null}
      {identity?.resultId ? (
        <Typography variant="caption" sx={{ overflowWrap: 'anywhere' }}>
          Result ID: {identity.resultId}
        </Typography>
      ) : null}
      {result?.name ? (
        <Typography variant="caption">Stored result: {result.name}</Typography>
      ) : null}
      {result?.backend_session_id ? (
        <Typography variant="caption" sx={{ overflowWrap: 'anywhere' }}>
          Backend session: {result.backend_session_id}
        </Typography>
      ) : null}
      <Accordion disableGutters elevation={0} variant="outlined">
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-label="Original calculation inputs"
        >
          <Typography variant="body2">Original calculation inputs</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Stack component="dl" spacing={1} sx={{ m: 0 }}>
            {Object.entries(inputs).filter(([, value]) => value !== undefined).map(([key, value]) => (
              <Box key={key}>
                <Typography component="dt" variant="caption" color="text.secondary">
                  {key.replace(/_/g, ' ')}
                </Typography>
                <Typography
                  component="dd"
                  variant="body2"
                  sx={{ m: 0, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: 160, overflow: 'auto' }}
                >
                  {displayValue(value)}
                </Typography>
              </Box>
            ))}
            {result?.inputs !== undefined ? (
              <Box>
                <Typography component="dt" variant="caption" color="text.secondary">
                  Captured input datasets
                </Typography>
                <Typography component="dd" variant="body2" sx={{ m: 0, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: 160, overflow: 'auto' }}>
                  {displayValue(result.inputs)}
                </Typography>
              </Box>
            ) : null}
            {result?.parameters !== undefined ? (
              <Box>
                <Typography component="dt" variant="caption" color="text.secondary">
                  Effective calculation settings
                </Typography>
                <Typography component="dd" variant="body2" sx={{ m: 0, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: 160, overflow: 'auto' }}>
                  {displayValue(result.parameters)}
                </Typography>
              </Box>
            ) : null}
          </Stack>
        </AccordionDetails>
      </Accordion>
    </Stack>
  );
};

export default AnalysisResultIdentity;
