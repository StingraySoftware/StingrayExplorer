import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '@/test/testUtils';

const { createDynamicalPowerSpectrum, startDynamicalPowerSpectrumJob, getJob, getJobPartials, getJobResult, cancelJob } =
  vi.hoisted(() => ({
    createDynamicalPowerSpectrum: vi.fn(),
    startDynamicalPowerSpectrumJob: vi.fn(),
    getJob: vi.fn(),
    getJobPartials: vi.fn(),
    getJobResult: vi.fn(),
    cancelJob: vi.fn(),
  }));
vi.mock('@/api/dataApi', () => ({
  dataApi: { listEventLists: async () => ({ success: true, data: [{ name: 'obs', n_events: 1000, time_range: [0, 10] }] }) },
}));
vi.mock('@/api/spectrumApi', () => ({
  spectrumApi: { createDynamicalPowerSpectrum, startDynamicalPowerSpectrumJob },
}));
vi.mock('@/api/jobApi', () => ({ jobApi: { getJob, getJobPartials, getJobResult, cancelJob } }));
vi.mock('@/components/plots/PlotlyChart', () => ({
  default: (props: { workspaceKey: string }) => <div data-testid={props.workspaceKey.endsWith('previewChart') ? 'preview' : 'chart'} />,
}));
import DynamicalPowerSpectrumPage from './index';

const final = {
  success: true,
  data: { name: null, freq: [1], time: [0], dyn_ps: [[2]], norm: 'leahy', segment_size: 8, shape: [1, 1] },
  message: 'done',
  error: null,
};

async function prepare() {
  renderWithProviders(<DynamicalPowerSpectrumPage />);
  await userEvent.click(await screen.findByLabelText('Event list'));
  await userEvent.click(await screen.findByRole('option', { name: /obs/ }));
  await userEvent.click(screen.getByLabelText('Run in background (cancellable)'));
}

describe('DynamicalPowerSpectrumPage background jobs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    startDynamicalPowerSpectrumJob.mockResolvedValue({ success: true, data: { job_id: 'job-1' }, message: '', error: null });
    getJobPartials.mockResolvedValue({
      success: true,
      data: [{ preview: true, n_segments: 2, freq: [1], time: [0, 8], dyn_ps: [[1, 2]] }],
    });
  });

  it('shows progress and a preview, then the final result', async () => {
    let polls = 0;
    getJob.mockImplementation(async () => {
      polls += 1;
      return {
        success: true,
        data: {
          id: 'job-1',
          status: polls < 3 ? 'running' : 'completed',
          progress: 0.3,
          progress_message: 'Computing the dynamical power spectrum',
          partial_count: 1,
        },
      };
    });
    getJobResult.mockResolvedValue(final);
    await prepare();
    await userEvent.click(screen.getByRole('button', { name: 'Compute' }));
    expect(await screen.findByText('Computing the dynamical power spectrum')).toBeInTheDocument();
    expect(await screen.findByTestId('preview')).toBeInTheDocument();
    expect(await screen.findByTestId('chart', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(startDynamicalPowerSpectrumJob).toHaveBeenCalledWith(
      expect.objectContaining({ event_list_name: 'obs', dt: 0.0625, segment_size: 8 })
    );
    expect(createDynamicalPowerSpectrum).not.toHaveBeenCalled();
  });

  it('cancels a running job', async () => {
    let cancelled = false;
    cancelJob.mockImplementation(async () => {
      cancelled = true;
      return { success: true, data: null, message: '', error: null };
    });
    getJob.mockImplementation(async () => ({
      success: true,
      data: {
        id: 'job-1',
        status: cancelled ? 'cancelled' : 'running',
        progress: 0.3,
        progress_message: 'Computing the dynamical power spectrum',
        partial_count: 0,
      },
    }));
    await prepare();
    await userEvent.click(screen.getByRole('button', { name: 'Compute' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Cancel' }));
    expect(cancelJob).toHaveBeenCalledWith('job-1');
    expect(await screen.findByText('The background analysis was cancelled', {}, { timeout: 3000 })).toBeInTheDocument();
  });

  async function computeOnceThenRunAgain(secondStatus: 'cancelled' | 'failed') {
    let run = 0;
    let cancelled = false;
    startDynamicalPowerSpectrumJob.mockImplementation(async () => {
      run += 1;
      return { success: true, data: { job_id: `job-${run}` }, message: '', error: null };
    });
    cancelJob.mockImplementation(async () => {
      cancelled = true;
      return { success: true, data: null, message: '', error: null };
    });
    getJob.mockImplementation(async (jobId: string) => ({
      success: true,
      data: {
        id: jobId,
        status: jobId === 'job-1' ? 'completed' : secondStatus === 'failed' ? 'failed' : cancelled ? 'cancelled' : 'running',
        progress: 0.3,
        progress_message: 'Computing the dynamical power spectrum',
        partial_count: 0,
        error: secondStatus === 'failed' ? 'MemoryError: the segment is too large' : null,
      },
    }));
    getJobResult.mockResolvedValue(final);
    await prepare();
    await userEvent.click(screen.getByRole('button', { name: 'Compute' }));
    expect(await screen.findByTestId('chart', {}, { timeout: 3000 })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Compute' }));
    if (secondStatus === 'cancelled') {
      await userEvent.click(await screen.findByRole('button', { name: 'Cancel' }));
    }
  }

  it('shows only the cancelled state when a later job is cancelled', async () => {
    await computeOnceThenRunAgain('cancelled');
    const cancelledAlert = (await screen.findByText('The background analysis was cancelled', {}, { timeout: 3000 })).closest('[role="alert"]');
    expect(cancelledAlert).toHaveClass('MuiAlert-colorInfo');
    expect(screen.queryByText(/The latest request failed/)).not.toBeInTheDocument();
    expect(screen.getByTestId('chart')).toBeInTheDocument();
  });

  it('still reports a real failure next to the previous result', async () => {
    await computeOnceThenRunAgain('failed');
    expect(await screen.findByText('MemoryError: the segment is too large', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText('MemoryError: the segment is too large').closest('[role="alert"]')).toHaveClass('MuiAlert-colorError');
    expect(screen.getByText(/The latest request failed/)).toBeInTheDocument();
  });
});
