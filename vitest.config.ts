import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    // Bound concurrent DOM environments so interactive tests retain their
    // existing timeouts on busy development machines and CI runners.
    maxWorkers: 4,
    // Required for @testing-library/react v16 auto-cleanup between tests
    globals: true,
    setupFiles: ['src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
