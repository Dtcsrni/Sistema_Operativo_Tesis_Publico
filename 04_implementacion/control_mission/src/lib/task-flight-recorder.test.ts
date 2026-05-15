import test, { before } from 'node:test';
import assert from 'node:assert/strict';

type RunFn = typeof import('./db').run;
type BuildTaskFlightRecorderFn = typeof import('./task-flight-recorder').buildTaskFlightRecorder;

let run: RunFn;
let buildTaskFlightRecorder: BuildTaskFlightRecorderFn;

before(async () => {
  process.env.DATABASE_PATH = `.tmp/task-flight-recorder-${process.pid}.db`;
  ({ run } = await import('./db'));
  ({ buildTaskFlightRecorder } = await import('./task-flight-recorder'));
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

test('flight recorder diagnoses delivered chat with completion but no surfaced assistant reply', () => {
  seedWorkspace();
  const agentId = crypto.randomUUID();
  const taskId = crypto.randomUUID();

  run(
    `INSERT INTO agents (id, name, role, avatar_emoji, status, workspace_id, source, created_at, updated_at)
     VALUES (?, 'Product Mapper', 'mapper', '🧭', 'working', 'default', 'local', ?, ?)`,
    [agentId, minutesAgo(30), minutesAgo(2)]
  );
  run(
    `INSERT INTO tasks (id, title, status, priority, assigned_agent_id, workspace_id, business_id, created_at, updated_at)
     VALUES (?, 'Create a carbon copy of Bloom', 'testing', 'normal', ?, 'default', 'default', ?, ?)`,
    [taskId, agentId, minutesAgo(30), minutesAgo(2)]
  );
  run(
    `INSERT INTO openclaw_sessions (id, agent_id, openclaw_session_id, status, session_type, task_id, created_at, updated_at)
     VALUES (?, ?, ?, 'active', 'persistent', ?, ?, ?)`,
    [crypto.randomUUID(), agentId, `mission-control-product-mapper-${taskId}`, taskId, minutesAgo(20), minutesAgo(20)]
  );
  run(
    `INSERT INTO task_notes (id, task_id, content, mode, role, status, delivered_at, created_at)
     VALUES (?, ?, 'why did the agent stall?', 'direct', 'user', 'delivered', ?, ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(8), minutesAgo(8)]
  );
  run(
    `INSERT INTO task_activities (id, task_id, agent_id, activity_type, message, created_at)
     VALUES (?, ?, ?, 'completed', 'TASK_COMPLETE: Built the discovery package and handed off to Tester Agent', ?)`,
    [crypto.randomUUID(), taskId, agentId, minutesAgo(4)]
  );
  run(
    `INSERT INTO task_deliverables (id, task_id, deliverable_type, title, path, created_at)
     VALUES (?, ?, 'file', 'PRD.md', '/tmp/PRD.md', ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(3)]
  );

  const recorder = buildTaskFlightRecorder(taskId);

  assert.ok(recorder);
  assert.equal(recorder.summary.chat_status, 'reply_not_surfaced');
  assert.equal(recorder.summary.deliverable_count, 1);
  assert.ok(recorder.summary.chat_diagnosis?.includes('no assistant chat note'));
  assert.ok(recorder.events.some(event => event.kind === 'diagnostic' && event.title === 'Chat reply was not surfaced'));
});

test('flight recorder marks latest operator chat as answered when assistant note is captured', () => {
  seedWorkspace();
  const agentId = crypto.randomUUID();
  const taskId = crypto.randomUUID();

  run(
    `INSERT INTO agents (id, name, role, avatar_emoji, status, workspace_id, source, created_at, updated_at)
     VALUES (?, 'Product Mapper', 'mapper', '🧭', 'working', 'default', 'local', ?, ?)`,
    [agentId, minutesAgo(30), minutesAgo(2)]
  );
  run(
    `INSERT INTO tasks (id, title, status, priority, assigned_agent_id, workspace_id, business_id, created_at, updated_at)
     VALUES (?, 'Capture chat answer', 'in_progress', 'normal', ?, 'default', 'default', ?, ?)`,
    [taskId, agentId, minutesAgo(30), minutesAgo(2)]
  );
  run(
    `INSERT INTO openclaw_sessions (id, agent_id, openclaw_session_id, status, session_type, task_id, created_at, updated_at)
     VALUES (?, ?, ?, 'active', 'persistent', ?, ?, ?)`,
    [crypto.randomUUID(), agentId, `mission-control-product-mapper-${taskId}`, taskId, minutesAgo(20), minutesAgo(20)]
  );
  run(
    `INSERT INTO task_notes (id, task_id, content, mode, role, status, delivered_at, created_at)
     VALUES (?, ?, 'sigues ahi?', 'direct', 'user', 'delivered', ?, ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(8), minutesAgo(8)]
  );
  run(
    `INSERT INTO task_notes (id, task_id, content, mode, role, status, delivered_at, created_at)
     VALUES (?, ?, 'Si, sigo trabajando y ya capture respuesta.', 'direct', 'assistant', 'delivered', ?, ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(7), minutesAgo(7)]
  );

  const recorder = buildTaskFlightRecorder(taskId);

  assert.ok(recorder);
  assert.equal(recorder.summary.chat_status, 'answered');
  assert.ok(recorder.summary.chat_diagnosis?.includes('assistant response recorded'));
  assert.equal(recorder.events.some(event => event.kind === 'diagnostic' && event.title === 'Chat reply was not surfaced'), false);
});

test('flight recorder does not treat redispatch as a surfaced completion reply', () => {
  seedWorkspace();
  const agentId = crypto.randomUUID();
  const taskId = crypto.randomUUID();

  run(
    `INSERT INTO agents (id, name, role, avatar_emoji, status, workspace_id, source, created_at, updated_at)
     VALUES (?, 'Product Mapper', 'mapper', '🧭', 'working', 'default', 'local', ?, ?)`,
    [agentId, minutesAgo(30), minutesAgo(1)]
  );
  run(
    `INSERT INTO tasks (id, title, status, priority, assigned_agent_id, workspace_id, business_id, created_at, updated_at)
     VALUES (?, 'Redispatch chat answer', 'in_progress', 'normal', ?, 'default', 'default', ?, ?)`,
    [taskId, agentId, minutesAgo(30), minutesAgo(1)]
  );
  run(
    `INSERT INTO task_notes (id, task_id, content, mode, role, status, delivered_at, created_at)
     VALUES (?, ?, 'sigues ahi?', 'direct', 'user', 'delivered', ?, ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(8), minutesAgo(8)]
  );
  run(
    `INSERT INTO task_activities (id, task_id, agent_id, activity_type, message, created_at)
     VALUES (?, ?, ?, 'status_changed', 'Task dispatched to Product Mapper - Agent is now working on this task', ?)`,
    [crypto.randomUUID(), taskId, agentId, minutesAgo(1)]
  );

  const recorder = buildTaskFlightRecorder(taskId);

  assert.ok(recorder);
  assert.equal(recorder.summary.chat_status, 'awaiting_reply');
  assert.equal(recorder.events.some(event => event.kind === 'diagnostic' && event.title === 'Chat reply was not surfaced'), false);
});

test('flight recorder summary recomputes health instead of trusting stale stored metadata', () => {
  seedWorkspace();
  const agentId = crypto.randomUUID();
  const taskId = crypto.randomUUID();

  run(
    `INSERT INTO agents (id, name, role, avatar_emoji, status, workspace_id, source, created_at, updated_at)
     VALUES (?, 'Product Mapper', 'mapper', '🧭', 'working', 'default', 'local', ?, ?)`,
    [agentId, minutesAgo(90), minutesAgo(1)]
  );
  run(
    `INSERT INTO tasks (id, title, status, priority, assigned_agent_id, workspace_id, business_id, created_at, updated_at)
     VALUES (?, 'Stale health metadata', 'in_progress', 'normal', ?, 'default', 'default', ?, ?)`,
    [taskId, agentId, minutesAgo(90), minutesAgo(1)]
  );
  run(
    `INSERT INTO openclaw_sessions (id, agent_id, openclaw_session_id, status, session_type, task_id, created_at, updated_at)
     VALUES (?, ?, ?, 'active', 'persistent', ?, ?, ?)`,
    [crypto.randomUUID(), agentId, `mission-control-product-mapper-${taskId}`, taskId, minutesAgo(89), minutesAgo(89)]
  );
  run(
    `INSERT INTO task_notes (id, task_id, content, mode, role, status, delivered_at, created_at)
     VALUES (?, ?, 'sigues ahi?', 'direct', 'user', 'delivered', ?, ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(60), minutesAgo(60)]
  );
  run(
    `INSERT INTO agent_health (id, agent_id, task_id, health_state, last_activity_at, consecutive_stall_checks, metadata, updated_at)
     VALUES (?, ?, ?, 'working', ?, 0, ?, ?)`,
    [
      crypto.randomUUID(),
      agentId,
      taskId,
      minutesAgo(1),
      JSON.stringify({
        display_state: 'completed_not_surfaced',
        reason: 'stale metadata from a previous classifier',
      }),
      minutesAgo(1),
    ]
  );

  const recorder = buildTaskFlightRecorder(taskId);

  assert.ok(recorder);
  assert.equal(recorder.summary.chat_status, 'awaiting_reply');
  assert.equal(recorder.summary.health_display_state, 'needs_attention');
  assert.match(recorder.summary.health_reason || '', /no assistant reply/);
});

test('flight recorder reports model_unavailable instead of awaiting_reply when dispatch found no model', () => {
  seedWorkspace();
  const agentId = crypto.randomUUID();
  const taskId = crypto.randomUUID();

  run(
    `INSERT INTO agents (id, name, role, avatar_emoji, status, workspace_id, source, created_at, updated_at)
     VALUES (?, 'Product Mapper', 'mapper', '🧭', 'standby', 'default', 'local', ?, ?)`,
    [agentId, minutesAgo(30), minutesAgo(1)]
  );
  run(
    `INSERT INTO tasks (id, title, status, priority, assigned_agent_id, workspace_id, business_id, created_at, updated_at)
     VALUES (?, 'Capture model unavailable', 'in_progress', 'normal', ?, 'default', 'default', ?, ?)`,
    [taskId, agentId, minutesAgo(30), minutesAgo(1)]
  );
  run(
    `INSERT INTO openclaw_sessions (id, agent_id, openclaw_session_id, status, session_type, task_id, created_at, updated_at)
     VALUES (?, ?, ?, 'active', 'persistent', ?, ?, ?)`,
    [crypto.randomUUID(), agentId, `mission-control-product-mapper-${taskId}`, taskId, minutesAgo(20), minutesAgo(20)]
  );
  run(
    `INSERT INTO task_notes (id, task_id, content, mode, role, status, delivered_at, created_at)
     VALUES (?, ?, 'run diagnostics', 'direct', 'user', 'delivered', ?, ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(8), minutesAgo(8)]
  );
  run(
    `INSERT INTO task_activities (id, task_id, agent_id, activity_type, message, metadata, created_at)
     VALUES (?, ?, ?, 'status_changed', 'Model unavailable; task was not marked as working', ?, ?)`,
    [
      crypto.randomUUID(),
      taskId,
      agentId,
      JSON.stringify({ status: 'model_unavailable', backend_errors: [{ error: 'desktop_runtime_misconfigured:http_404' }] }),
      minutesAgo(1),
    ]
  );

  const recorder = buildTaskFlightRecorder(taskId);

  assert.ok(recorder);
  assert.equal(recorder.summary.chat_status, 'model_unavailable');
  assert.equal(recorder.summary.execution_evidence.model_state, 'awaiting_model');
});
