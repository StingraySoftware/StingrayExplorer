import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

const repositoryRoot = process.cwd();

function productionRendererFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) return productionRendererFiles(path);
    if (!/\.tsx?$/.test(path) || /\.test\.tsx?$/.test(path)) return [];
    return [path];
  });
}

describe('packaged renderer assets', () => {
  it('allows the inlined data: font subsets in the content security policy', () => {
    const html = readFileSync(join(repositoryRoot, 'index.html'), 'utf8');
    const policy = html.match(/http-equiv="Content-Security-Policy" content="([^"]+)"/)?.[1] ?? '';
    const fontSources = policy.split(';').map((part) => part.trim()).find((part) => part.startsWith('font-src'));
    expect(fontSources?.split(/\s+/)).toEqual(expect.arrayContaining(["'self'", 'data:']));
  });

  it('imports renderer images instead of referencing root /assets/ paths absent from dist', () => {
    const offenders = productionRendererFiles(join(repositoryRoot, 'src'))
      .filter((path) => /["'`(]\/assets\//.test(readFileSync(path, 'utf8')))
      .map((path) => relative(repositoryRoot, path));
    expect(offenders).toEqual([]);
  });
});
