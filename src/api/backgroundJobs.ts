import { ApiResponse } from './client';
import { jobApi } from './jobApi';
import type { Job } from '@/types/job';

export interface BackgroundRunHandlers<P> {
  /** Every polled job record, for progress display. */
  onJob?: (job: Job) => void;
  /** The newest partial (preview) result whenever a new one is published. */
  onPartial?: (partial: P) => void;
}

/** The message of the response a cancelled background analysis resolves with. */
export const BACKGROUND_CANCELLED_MESSAGE = 'The background analysis was cancelled';

const POLL_MS = 400;
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Start a background analysis job and resolve with its final response, which
 * is the same response a direct request returns. Cancellation resolves with
 * an unsuccessful response; use jobApi.cancelJob with the reported job id.
 */
export async function runBackgroundAnalysis<T, P = unknown>(
  start: () => Promise<ApiResponse<{ job_id: string }>>,
  handlers: BackgroundRunHandlers<P> = {}
): Promise<ApiResponse<T>> {
  const started = await start();
  if (!started.success || !started.data) {
    return { ...started, data: null } as ApiResponse<T>;
  }
  const jobId = started.data.job_id;
  let seenPartials = 0;
  for (;;) {
    const polled = await jobApi.getJob(jobId);
    if (!polled.success || !polled.data) {
      return { success: false, data: null, message: polled.message, error: polled.error } as ApiResponse<T>;
    }
    const job = polled.data;
    handlers.onJob?.(job);
    if ((job.partial_count ?? 0) > seenPartials && handlers.onPartial) {
      const partials = await jobApi.getJobPartials<P>(jobId);
      if (partials.success && partials.data && partials.data.length > 0) {
        seenPartials = partials.data.length;
        handlers.onPartial(partials.data[partials.data.length - 1]);
      }
    }
    if (job.status === 'completed') return jobApi.getJobResult<T>(jobId);
    if (job.status === 'failed') {
      const message = job.error ?? 'The background analysis failed';
      return { success: false, data: null, message, error: message } as ApiResponse<T>;
    }
    if (job.status === 'cancelled') {
      const message = BACKGROUND_CANCELLED_MESSAGE;
      return { success: false, data: null, message, error: message } as ApiResponse<T>;
    }
    await sleep(POLL_MS);
  }
}
