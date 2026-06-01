export type OpenClawDispatchStatus =
  | 'ok'
  | 'model_error'
  | 'model_unavailable'
  | 'approval_required'
  | 'delivery_failed';

export interface OpenClawBackendError {
  provider?: string;
  model?: string;
  error?: string;
  base_url?: string;
  [key: string]: unknown;
}

export interface NormalizedOpenClawDispatchResponse {
  status: OpenClawDispatchStatus;
  provider?: string;
  model?: string;
  trace_id?: string;
  assistant_text?: string;
  backend_errors: OpenClawBackendError[];
  raw: unknown;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function stringValue(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined;
}

function normalizeStatus(value: unknown): OpenClawDispatchStatus {
  const status = stringValue(value) || 'delivery_failed';
  if (status === 'ok' || status === 'model_error' || status === 'model_unavailable' || status === 'approval_required') {
    return status;
  }
  if (status === 'error' || status === 'failed' || status === 'delivery_failed') {
    return 'delivery_failed';
  }
  return 'delivery_failed';
}

function normalizeBackendErrors(value: unknown): OpenClawBackendError[] {
  if (!Array.isArray(value)) return [];
  return value.map(item => asRecord(item)).filter(item => Object.keys(item).length > 0) as OpenClawBackendError[];
}

export function normalizeOpenClawDispatchResponse(payload: unknown): NormalizedOpenClawDispatchResponse {
  const outer = asRecord(payload);
  const response = asRecord(outer.response || payload);
  const assistantText = stringValue(response.assistant_text) || (normalizeStatus(response.status) === 'ok' ? stringValue(response.text) : undefined);

  return {
    status: normalizeStatus(response.status),
    provider: stringValue(response.provider) || stringValue(response.selected_provider),
    model: stringValue(response.model) || stringValue(response.selected_model),
    trace_id: stringValue(response.trace_id),
    assistant_text: assistantText,
    backend_errors: normalizeBackendErrors(response.backend_errors),
    raw: payload,
  };
}

export function dispatchResponseHasModelFailure(response: NormalizedOpenClawDispatchResponse): boolean {
  return (
    response.status === 'model_unavailable' ||
    response.status === 'model_error' ||
    response.status === 'delivery_failed'
  ) && !response.assistant_text;
}
