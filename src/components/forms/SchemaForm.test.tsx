import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { JsonSchemaObject, JsonSchemaProperty } from '@/api/schemaApi';
import SchemaForm from './SchemaForm';
import { initialSchemaValue, parseSchemaValue } from './schemaValues';

const schema: JsonSchemaObject = {
  properties: {
    dt: { type: 'number', title: 'Time bin dt (s)', description: 'Bin width', exclusiveMinimum: 0, examples: [0.1] },
    bands: { type: 'integer', title: 'Bands', minimum: 2, maximum: 64, default: 5 },
    norm: { type: 'string', title: 'Normalization', enum: ['none', 'variance'], default: 'none' },
    log: { type: 'boolean', title: 'Logarithmic', default: false },
  },
};

describe('parseSchemaValue', () => {
  const number = schema.properties.dt as JsonSchemaProperty;
  it.each([
    ['0.25', 0.25, null],
    ['0', null, 'Must be a positive number'],
    ['abc', null, 'Must be a positive number'],
  ])('parses %s against exclusiveMinimum', (raw, value, error) => {
    expect(parseSchemaValue(number, raw)).toEqual({ value, error });
  });

  it('enforces integer bounds and enums', () => {
    const bands = schema.properties.bands;
    expect(parseSchemaValue(bands, '1.5').error).toBe('Must be a whole number');
    expect(parseSchemaValue(bands, '1').error).toBe('Must be at least 2');
    expect(parseSchemaValue(bands, '65').error).toBe('Must be at most 64');
    expect(parseSchemaValue(bands, '8')).toEqual({ value: 8, error: null });
    expect(parseSchemaValue(schema.properties.norm, 'other').error).toBe('Choose one of none, variance');
  });

  it('starts from the default, else the first example', () => {
    expect(initialSchemaValue(schema.properties.dt)).toBe('0.1');
    expect(initialSchemaValue(schema.properties.bands)).toBe('5');
    expect(initialSchemaValue(schema.properties.log)).toBe(false);
  });
});

function Harness() {
  const [values, setValues] = React.useState<Record<string, string | boolean>>({
    dt: '0.1', bands: '5', norm: 'none', log: false,
  });
  const bind = (name: string) => ({
    name,
    value: values[name],
    onChange: (value: string | boolean) => setValues((current) => ({ ...current, [name]: value })),
  });
  return (
    <>
      <SchemaForm schema={schema} fields={['dt', 'bands', 'norm', 'log', 'missing'].map(bind)} />
      <output data-testid="values">{JSON.stringify(values)}</output>
    </>
  );
}

describe('SchemaForm', () => {
  it('renders each property as the matching MUI control', async () => {
    render(<Harness />);
    expect(screen.getByLabelText('Time bin dt (s)')).toHaveValue('0.1');
    expect(screen.getByText('Bin width')).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText('Time bin dt (s)'));
    await userEvent.type(screen.getByLabelText('Time bin dt (s)'), '-2');
    expect(screen.getByText('Must be a positive number')).toBeInTheDocument();

    await userEvent.click(screen.getByLabelText('Normalization'));
    await userEvent.click(await screen.findByRole('option', { name: 'variance' }));
    await userEvent.click(screen.getByLabelText('Logarithmic'));
    expect(JSON.parse(screen.getByTestId('values').textContent ?? '{}')).toMatchObject({
      dt: '-2',
      norm: 'variance',
      log: true,
    });
  });
});
