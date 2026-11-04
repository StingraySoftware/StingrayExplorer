import { useWorkspaceState } from '@/api/workspaceSession';
import { spectralBandsOverlap } from '@/utils/eventSelection';
import { useEventSelection } from './useEventSelection';

/**
 * Selections for a two-input analysis. In two-band mode both inputs are the
 * first EventList, split into a subject band and a reference band.
 */
export function usePairedSelection(pageKey: string) {
  const [twoBand, setTwoBand] = useWorkspaceState(`${pageKey}:twoBand`, false);
  const first = useEventSelection(`${pageKey}:selection1`);
  const second = useEventSelection(`${pageKey}:selection2`);
  const missingBand =
    twoBand && (first.selection === null || second.selection === null)
      ? 'Two-band mode needs both a subject band and a reference band.'
      : null;
  const error = first.error ?? second.error ?? missingBand;
  const overlapLikely =
    twoBand &&
    first.selection !== null &&
    second.selection !== null &&
    spectralBandsOverlap(first.selection, second.selection);
  const requestSelections = {
    ...(first.selection ? { selection_1: first.selection } : {}),
    ...(second.selection ? { selection_2: second.selection } : {}),
  };
  return { twoBand, setTwoBand, first, second, error, overlapLikely, requestSelections };
}

export type PairedSelection = ReturnType<typeof usePairedSelection>;
