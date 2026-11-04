import { useWorkspaceState } from '@/api/workspaceSession';
import {
  EMPTY_SELECTION_DRAFT,
  parseSelectionDraft,
  SelectionDraft,
} from '@/utils/eventSelection';

/** A page's photon-selection draft, kept with its other inputs, and its request form. */
export function useEventSelection(key: string, options: { spectral?: boolean } = {}) {
  const [draft, setDraft] = useWorkspaceState<SelectionDraft>(key, EMPTY_SELECTION_DRAFT);
  const { selection, error } = parseSelectionDraft(draft, options);
  return { draft, setDraft, selection, error };
}
