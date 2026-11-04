import { useQuery } from '@tanstack/react-query';
import { schemaApi, JsonSchemaProperty } from '@/api/schemaApi';

/** Load a backend request model's schema once per session. */
export function useFormSchema(form: string) {
  return useQuery({
    queryKey: ['form-schema', form],
    staleTime: Infinity,
    retry: false,
    queryFn: async () => {
      const response = await schemaApi.getFormSchema(form);
      if (!response.success || !response.data) {
        throw new Error(response.message || `No form schema for ${form}`);
      }
      return response.data;
    },
  });
}

/** The value a fresh form shows: the schema default, else its first example. */
export function initialSchemaValue(property: JsonSchemaProperty): string | boolean {
  const value = property.default ?? property.examples?.[0];
  if (property.type === 'boolean') return value === true;
  return value === undefined || value === null ? '' : String(value);
}

const NUMBER = /^[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$/;

/** Parse and validate a text value against a schema property. */
export function parseSchemaValue(
  property: JsonSchemaProperty,
  raw: string | boolean
): { value: number | string | boolean | null; error: string | null } {
  if (property.type === 'boolean') return { value: raw === true, error: null };
  const text = String(raw).trim();
  if (property.enum) {
    return property.enum.map(String).includes(text)
      ? { value: text, error: null }
      : { value: null, error: `Choose one of ${property.enum.join(', ')}` };
  }
  if (property.type !== 'number' && property.type !== 'integer') {
    return { value: text, error: null };
  }
  if (!NUMBER.test(text)) {
    return {
      value: null,
      error: property.exclusiveMinimum === 0 ? 'Must be a positive number' : 'Must be a number',
    };
  }
  const value = Number(text);
  if (property.type === 'integer' && !Number.isInteger(value)) {
    return { value: null, error: 'Must be a whole number' };
  }
  if (property.exclusiveMinimum !== undefined && !(value > property.exclusiveMinimum)) {
    return {
      value: null,
      error:
        property.exclusiveMinimum === 0
          ? 'Must be a positive number'
          : `Must be greater than ${property.exclusiveMinimum}`,
    };
  }
  if (property.minimum !== undefined && value < property.minimum) {
    return { value: null, error: `Must be at least ${property.minimum}` };
  }
  if (property.exclusiveMaximum !== undefined && !(value < property.exclusiveMaximum)) {
    return { value: null, error: `Must be less than ${property.exclusiveMaximum}` };
  }
  if (property.maximum !== undefined && value > property.maximum) {
    return { value: null, error: `Must be at most ${property.maximum}` };
  }
  return { value, error: null };
}
