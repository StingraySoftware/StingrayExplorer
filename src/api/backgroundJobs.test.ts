import { afterEach, describe, expect, it, vi } from 'vitest';

const { getJob, getJobPartials, getJobResult } = vi.hoisted(() => ({
  getJob: vi.fn(),
  getJobPartials: vi.fn(),
  getJobResult: vi.fn(),
}));
vi.mock('./jobApi', () => ({ jobApi: { getJob, getJobPartials, getJobResult } }));
import { runBackgroundAnalysis } from './backgroundJobs';

const job = (status: string, extra = {}) => ({
  success: true,
  data: { id: 'job-1', status, progress: 0.5, progress_message: 'Working', partial_count: 0, ...extra },
});

describe('runBackgroundAnalysis', () => {
  afterEach(() => vi.clearAllMocks());

  it('reports progress and previews, then resolves with the job result', async () => {
    getJob
      .mockResolvedValueOnce(job('running', { partial_count: 1 }))
      .mockResolvedValueOnce(job('completed', { partial_count: 1 }));
    getJobPartials.mockResolvedValue({ success: true, data: [{ preview: true, n_segments: 4 }] });
    getJobResult.mockResolvedValue({ success: true, data: { dyn_ps: [[1]] }, message: 'ok', error: null });
    const onJob = vi.fn();
    const onPartial = vi.fn();
    const result = await runBackgroundAnalysis(
      async () => ({ success: true, data: { job_id: 'job-1' }, message: '', error: null }),
      { onJob, onPartial }
    );
    expect(result).toEqual({ success: true, data: { dyn_ps: [[1]] }, message: 'ok', error: null });
    expect(onPartial).toHaveBeenCalledWith({ preview: true, n_segments: 4 });
    expect(onJob).toHaveBeenCalledTimes(2);
    expect(getJobPartials).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['failed', { error: 'The analysis exceeded the 4096 MB memory cap' }, 'The analysis exceeded the 4096 MB memory cap'],
    ['cancelled', {}, 'The background analysis was cancelled'],
  ])('resolves unsuccessfully when the job is %s', async (status, extra, message) => {
    getJob.mockResolvedValue(job(status, extra));
    const result = await runBackgroundAnalysis(async () => ({
      success: true, data: { job_id: 'job-1' }, message: '', error: null,
    }));
    expect(result).toMatchObject({ success: false, message });
    expect(getJobResult).not.toHaveBeenCalled();
  });

  it('passes a failed start straight through', async () => {
    const result = await runBackgroundAnalysis(async () => ({
      success: false, data: null, message: "EventList 'x' not found", error: null,
    }));
    expect(result).toMatchObject({ success: false, message: "EventList 'x' not found" });
    expect(getJob).not.toHaveBeenCalled();
  });
});
