import test, { before } from 'node:test';
import assert from 'node:assert/strict';
import type { EventEmitter } from 'node:events';

type RunFn = typeof import('./db').run;
type QueryAllFn = typeof import('./db').queryAll;
type ChatListenerModule = typeof import('./chat-listener');
type GetOpenClawClientFn = typeof import('./openclaw/client').getOpenClawClient;

let run: RunFn;
let queryAll: QueryAllFn;
let listener: ChatListenerModule;
let getOpenClawClient: GetOpenClawClientFn;

before(async () => {
  process.env.DATABASE_PATH = `.tmp/chat-listener-${process.pid}.db`;
  ({ run, queryAll } = await import('./db'));
  listener = await import('./chat-listener');
  ({ getOpenClawClient } = await import('./openclaw/client'));
});

function minutesAgo(minutes: number): string {
  return new Date(Date.now() - minutes * 60000).toISOString();
}

function seedWorkspace() {
  run(
    `INSERT OR IGNORE INTO workspaces (id, name, slug, icon, created_at, updated_at)
     VALUES ('default', 'Default', 'default', '📁', ?, ?)`,
    [minutesAgo(0), minutesAgo(0)]
  );
}

function seedAgentTask(opts: { taskId?: string; agentId?: string; sessionId?: string } = {}) {
  seedWorkspace();
  const taskId = opts.taskId || crypto.randomUUID();
  const agentId = opts.agentId || crypto.randomUUID();
  const sessionId = opts.sessionId || `session-${taskId}`;

  run(
    `INSERT INTO agents (id, name, role, avatar_emoji, status, workspace_id, source, created_at, updated_at)
     VALUES (?, 'Builder', 'builder', '🛠️', 'working', 'default', 'local', ?, ?)`,
    [agentId, minutesAgo(20), minutesAgo(1)]
  );

  run(
    `INSERT INTO tasks (id, title, status, priority, assigned_agent_id, workspace_id, business_id, created_at, updated_at)
     VALUES (?, 'Capture chat reply', 'in_progress', 'normal', ?, 'default', 'default', ?, ?)`,
    [taskId, agentId, minutesAgo(20), minutesAgo(1)]
  );

  run(
    `INSERT INTO openclaw_sessions (id, agent_id, openclaw_session_id, status, session_type, task_id, created_at, updated_at)
     VALUES (?, ?, ?, 'active', 'persistent', ?, ?, ?)`,
    [crypto.randomUUID(), agentId, sessionId, taskId, minutesAgo(10), minutesAgo(1)]
  );

  run(
    `INSERT INTO task_notes (id, task_id, content, mode, role, status, delivered_at, created_at)
     VALUES (?, ?, 'hola', 'direct', 'user', 'delivered', ?, ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(5), minutesAgo(5)]
  );

  return { taskId, agentId, sessionId, sessionKey: `agent:main:${sessionId}` };
}

function assistantNotes(taskId: string) {
  return queryAll<{ content: string }>(
    `SELECT content FROM task_notes WHERE task_id = ? AND role = 'assistant' ORDER BY created_at ASC`,
    [taskId]
  );
}

test('completion-style agent replies are captured for Chat instead of swallowed', () => {
  const normalized = listener.normalizeAgentReplyForChat('TASK_COMPLETE: Built the app and handed off to Tester Agent');

  assert.equal(normalized.action, 'store');
  assert.equal(normalized.kind, 'completion');
  assert.match(normalized.content, /Task complete/);
  assert.match(normalized.content, /Built the app/);
});

test('dispatch prompt leakage is still ignored', () => {
  const normalized = listener.normalizeAgentReplyForChat('NEW TASK ASSIGNED\nOUTPUT DIRECTORY: /tmp/work\nDo the thing');

  assert.equal(normalized.action, 'ignore');
  assert.equal(normalized.kind, 'prompt_leak');
});

test('final chat event stores a normal assistant reply when a reply is expected in memory', () => {
  const { taskId, sessionKey } = seedAgentTask();

  listener.expectReply(sessionKey, taskId);
  const result = listener.processChatEventForReply({
    sessionKey,
    state: 'final',
    message: { role: 'assistant', content: 'Ya avance y deje evidencia.' },
  });

  const notes = assistantNotes(taskId);
  assert.equal(result, 'stored');
  assert.equal(notes.length, 1);
  assert.equal(notes[0].content, 'Ya avance y deje evidencia.');
});

test('final completion event is visible as an assistant reply', () => {
  const { taskId, sessionKey } = seedAgentTask();

  listener.expectReply(sessionKey, taskId);
  const result = listener.processChatEventForReply({
    sessionKey,
    state: 'final',
    message: 'TASK_COMPLETE: Built the package and handed off to verification',
  });

  const notes = assistantNotes(taskId);
  assert.equal(result, 'stored');
  assert.equal(notes.length, 1);
  assert.match(notes[0].content, /Task complete/);
  assert.match(notes[0].content, /Built the package/);
});

test('chat.send RPC result stores final assistant reply when gateway does not emit chat_event', () => {
  const { taskId, sessionKey } = seedAgentTask();

  listener.expectReply(sessionKey, taskId);
  const result = listener.processChatSendResultForReply(sessionKey, taskId, {
    response: {
      status: 'ok',
      text: 'OpenClaw es la capa operativa local-first del sistema.',
      assistant_text: 'OpenClaw es la capa operativa local-first del sistema.',
    },
  });

  const notes = assistantNotes(taskId);
  assert.equal(result, 'stored');
  assert.equal(notes.length, 1);
  assert.equal(notes[0].content, 'OpenClaw es la capa operativa local-first del sistema.');
});

test('final chat event recovers awaiting reply from database when memory is empty', () => {
  const { taskId, sessionKey } = seedAgentTask();

  const result = listener.processChatEventForReply({
    sessionKey,
    state: 'final',
    message: 'Respuesta recuperada desde la sesion activa.',
  });

  const notes = assistantNotes(taskId);
  assert.equal(result, 'stored');
  assert.equal(notes.length, 1);
  assert.equal(notes[0].content, 'Respuesta recuperada desde la sesion activa.');
});

test('duplicate final chat event does not create duplicate assistant notes', () => {
  const { taskId, sessionKey } = seedAgentTask();
  const payload = {
    sessionKey,
    state: 'final' as const,
    message: 'Respuesta unica.',
  };

  assert.equal(listener.processChatEventForReply(payload), 'stored');
  assert.equal(listener.processChatEventForReply(payload), 'ignored');
  assert.equal(assistantNotes(taskId).length, 1);
});

test('chat listener reattaches without duplicating after listener loss', () => {
  const client = getOpenClawClient() as EventEmitter;
  listener.attachChatListener();

  const state = listener.__chatListenerTestUtils.getListenerState();
  assert.ok(state.chatHandler);
  assert.equal(client.listenerCount('chat_event', state.chatHandler), 1);

  listener.attachChatListener();
  assert.equal(client.listenerCount('chat_event', state.chatHandler), 1);

  client.removeListener('chat_event', state.chatHandler);
  assert.equal(client.listenerCount('chat_event', state.chatHandler), 0);

  client.emit('connected');
  assert.equal(client.listenerCount('chat_event', state.chatHandler), 1);
});
