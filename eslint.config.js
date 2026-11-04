import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'dist-electron', 'node_modules'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      react.configs.flat.recommended,
      reactHooks.configs.flat.recommended,
    ],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { ...globals.browser, ...globals.node, ...globals.es2022 },
    },
    settings: {
      react: { version: 'detect' },
    },
    rules: {
      // Vite's automatic JSX runtime makes React imports unnecessary
      'react/react-in-jsx-scope': 'off',
      // TypeScript types make prop-types redundant
      'react/prop-types': 'off',
      // Downgraded: existing code uses `any` in a few places; flag without failing the build
      '@typescript-eslint/no-explicit-any': 'warn',
      // Downgraded: existing code has unused vars; `_`-prefix is the in-repo convention
      // for intentionally unused bindings, so ignore those entirely
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      // Stylistic: literal quotes in JSX prose are fine in this app
      'react/no-unescaped-entities': 'off',
    },
  },
);
