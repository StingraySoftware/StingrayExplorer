import { useQuery } from '@tanstack/react-query';
import { dataApi, EventListSummary } from '@/api/dataApi';
import { useBackendContext } from '@/context/BackendContext';
import { captureBackendEpoch } from '@/api/backendEpoch';

export const EVENT_LISTS_QUERY_KEY = ['eventLists'] as const;

/**
 * Keep each managed backend's dataset list in its own query namespace and wait
 * for readiness. Unmanaged consumers retain the original standalone behavior.
 */
export function useEventLists() {
  const { generation, isReady } = useBackendContext();
  const epoch = captureBackendEpoch().version;
  return useQuery({
    queryKey: generation === null ? EVENT_LISTS_QUERY_KEY : [...EVENT_LISTS_QUERY_KEY, generation, epoch],
    enabled: generation === null || isReady,
    queryFn: async (): Promise<EventListSummary[]> => {
      const res = await dataApi.listEventLists();
      if (!res.success) {
        throw new Error(res.error || res.message || 'Failed to list event lists');
      }
      return res.data ?? [];
    },
    staleTime: 5_000,
  });
}
