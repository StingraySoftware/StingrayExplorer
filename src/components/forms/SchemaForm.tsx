import React from 'react';
import {
  FormControl,
  FormControlLabel,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select,
  Switch,
  TextField,
} from '@mui/material';
import type { JsonSchemaObject, JsonSchemaProperty } from '@/api/schemaApi';
import { parseSchemaValue } from './schemaValues';

export interface SchemaFieldBinding {
  /** Property name in the request model's schema. */
  name: string;
  value: string | boolean;
  onChange: (value: string | boolean) => void;
}

interface SchemaFieldProps {
  name: string;
  property: JsonSchemaProperty;
  value: string | boolean;
  onChange: (value: string | boolean) => void;
}

/** One MUI control generated from a JSON-schema property. */
export const SchemaField: React.FC<SchemaFieldProps> = ({ name, property, value, onChange }) => {
  const labelId = `schema-field-${name}-${React.useId()}`;
  const label = property.title ?? name;
  if (property.type === 'boolean') {
    return (
      <FormControlLabel
        control={<Switch checked={value === true} onChange={(event) => onChange(event.target.checked)} />}
        label={label}
      />
    );
  }
  if (property.enum) {
    return (
      <FormControl size="small" fullWidth>
        <InputLabel id={labelId}>{label}</InputLabel>
        <Select
          labelId={labelId}
          label={label}
          value={String(value)}
          onChange={(event) => onChange(event.target.value)}
        >
          {property.enum.map((option) => (
            <MenuItem key={String(option)} value={String(option)}>
              {String(option)}
            </MenuItem>
          ))}
        </Select>
        {property.description && <FormHelperText>{property.description}</FormHelperText>}
      </FormControl>
    );
  }
  const { error } = parseSchemaValue(property, value);
  const showError = String(value) !== '' && error !== null;
  return (
    <TextField
      label={label}
      size="small"
      value={String(value)}
      onChange={(event) => onChange(event.target.value)}
      error={showError}
      helperText={showError ? error : property.description ?? ' '}
    />
  );
};

interface SchemaFormProps {
  schema: JsonSchemaObject;
  /** Fields to render, in order, bound to the page's own state. */
  fields: SchemaFieldBinding[];
}

/** Parameter controls generated from a backend request model's JSON schema. */
const SchemaForm: React.FC<SchemaFormProps> = ({ schema, fields }) => (
  <>
    {fields.map((field) => {
      const property = schema.properties[field.name];
      if (!property) return null;
      return (
        <SchemaField
          key={field.name}
          name={field.name}
          property={property}
          value={field.value}
          onChange={field.onChange}
        />
      );
    })}
  </>
);

export default SchemaForm;
