import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import LogPanel from './LogPanel';
import { useLogStore } from '@/store/logStore';

describe('LogPanel', () => {
  const originalScrollIntoView = Element.prototype.scrollIntoView;

  beforeEach(() => {
    // jsdom does not implement scrolling; the panel auto-scrolls to new logs
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    Element.prototype.scrollIntoView = originalScrollIntoView;
    act(() => {
      useLogStore.getState().clearLogs();
      useLogStore.getState().setSearchFilter('');
      useLogStore.getState().setOpen(false);
    });
  });

  it('renders filtered logs from a selector that builds a new array', () => {
    act(() => {
      useLogStore.getState().setOpen(true);
      useLogStore.getState().addLog({ level: 'info', source: 'python', message: 'Backend ready' });
      useLogStore.getState().addLog({ level: 'error', source: 'frontend', message: 'Plot failed' });
    });

    render(<LogPanel />);
    expect(screen.getByText('Backend ready')).toBeInTheDocument();
    expect(screen.getByText('Plot failed')).toBeInTheDocument();

    act(() => {
      useLogStore.getState().setSearchFilter('plot');
    });
    expect(screen.queryByText('Backend ready')).not.toBeInTheDocument();
    expect(screen.getByText('Plot failed')).toBeInTheDocument();
  });
});
