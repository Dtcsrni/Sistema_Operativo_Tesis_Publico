import test from 'node:test';
import assert from 'node:assert/strict';
import { dispatchResponseHasModelFailure, normalizeOpenClawDispatchResponse } from './dispatch-response';

test('normalizes gateway response with assistant text', () => {
  const normalized = normalizeOpenClawDispatchResponse({
    response: {
      status: 'ok',
      provider: 'pc_native_llamacpp',
      model: 'mistral-nemo:12b',
      trace_id: 'CHAT-123',
      assistant_text: 'TASK_COMPLETE: listo',
      backend_errors: [],
    },
  });

  assert.equal(normalized.status, 'ok');
  assert.equal(normalized.provider, 'pc_native_llamacpp');
  assert.equal(normalized.model, 'mistral-nemo:12b');
  assert.equal(normalized.trace_id, 'CHAT-123');
  assert.equal(normalized.assistant_text, 'TASK_COMPLETE: listo');
  assert.equal(dispatchResponseHasModelFailure(normalized), false);
});

test('normalizes model_unavailable as a non-working dispatch failure', () => {
  const normalized = normalizeOpenClawDispatchResponse({
    response: {
      status: 'model_unavailable',
      provider: 'pc_native_llamacpp',
      model: '',
      trace_id: 'CHAT-456',
      backend_errors: [{ provider: 'pc_native_llamacpp', model: 'mistral-nemo:12b', error: 'desktop_runtime_misconfigured:http_404', base_url: 'http://ollama-pc:11434' }],
    },
  });

  assert.equal(normalized.status, 'model_unavailable');
  assert.equal(normalized.assistant_text, undefined);
  assert.equal(normalized.backend_errors[0].error, 'desktop_runtime_misconfigured:http_404');
  assert.equal(dispatchResponseHasModelFailure(normalized), true);
});

test('falls back to text as assistant_text only for ok status', () => {
  const ok = normalizeOpenClawDispatchResponse({ response: { status: 'ok', text: 'respuesta visible' } });
  const failed = normalizeOpenClawDispatchResponse({ response: { status: 'model_error', text: 'diagnostico interno' } });

  assert.equal(ok.assistant_text, 'respuesta visible');
  assert.equal(failed.assistant_text, undefined);
});

test('treats OpenClaw executor error as non-working dispatch failure', () => {
  const normalized = normalizeOpenClawDispatchResponse({
    response: {
      status: 'error',
      provider: 'opencode-executor',
      model: 'opencode',
      text: 'OpenCode executor fallo para TASK-001.',
      exit_code: 1,
    },
  });

  assert.equal(normalized.status, 'delivery_failed');
  assert.equal(normalized.assistant_text, undefined);
  assert.equal(dispatchResponseHasModelFailure(normalized), true);
});
