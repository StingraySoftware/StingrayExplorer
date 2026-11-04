import { apiClient, ApiResponse } from './client';

/** The JSON-schema subset parameter forms are generated from. */
export interface JsonSchemaProperty {
  type?: 'number' | 'integer' | 'string' | 'boolean';
  title?: string;
  description?: string;
  default?: unknown;
  examples?: unknown[];
  enum?: Array<string | number>;
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number;
  exclusiveMaximum?: number;
}

export interface JsonSchemaObject {
  title?: string;
  properties: Record<string, JsonSchemaProperty>;
  required?: string[];
}

export const schemaApi = {
  /** JSON schema of an allowlisted backend request model. */
  getFormSchema(form: string): Promise<ApiResponse<JsonSchemaObject>> {
    return apiClient.get(`/api/schemas/${form}`);
  },
};
