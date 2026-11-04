import React from 'react';
import { Alert, FormControlLabel, Switch } from '@mui/material';
import EventListSelector from './EventListSelector';
import EventSelectionField from './EventSelectionField';
import type { PairedSelection } from '@/hooks/usePairedSelection';

interface PairedEventInputsProps {
  pair: PairedSelection;
  eventList1: string;
  onEventList1: (name: string) => void;
  eventList2: string;
  onEventList2: (name: string) => void;
}

/** Two event lists, or one event list split into a subject and a reference band. */
const PairedEventInputs: React.FC<PairedEventInputsProps> = ({
  pair,
  eventList1,
  onEventList1,
  eventList2,
  onEventList2,
}) => (
  <>
    <FormControlLabel
      control={
        <Switch
          checked={pair.twoBand}
          onChange={(event) => pair.setTwoBand(event.target.checked)}
        />
      }
      label="Two bands of one event list"
    />
    {pair.twoBand ? (
      <>
        <EventListSelector label="Event list" value={eventList1} onChange={onEventList1} />
        <EventSelectionField
          label="Subject band"
          eventListName={eventList1}
          value={pair.first.draft}
          onChange={pair.first.setDraft}
        />
        <EventSelectionField
          label="Reference band"
          eventListName={eventList1}
          value={pair.second.draft}
          onChange={pair.second.setDraft}
        />
        {pair.overlapLikely && (
          <Alert severity="warning">
            These bands can share photons. Shared photons correlate the two bands&apos; Poisson
            noise and bias cross spectra, lags, coherence and cross-correlation; choose disjoint
            bands.
          </Alert>
        )}
      </>
    ) : (
      <>
        <EventListSelector label="Event list 1" value={eventList1} onChange={onEventList1} />
        <EventSelectionField
          label="Event list 1 photons"
          eventListName={eventList1}
          value={pair.first.draft}
          onChange={pair.first.setDraft}
        />
        <EventListSelector label="Event list 2" value={eventList2} onChange={onEventList2} />
        <EventSelectionField
          label="Event list 2 photons"
          eventListName={eventList2}
          value={pair.second.draft}
          onChange={pair.second.setDraft}
        />
      </>
    )}
  </>
);

export default PairedEventInputs;
