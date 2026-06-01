import test, { before } from 'node:test';
import assert from 'node:assert/strict';

type RunFn = typeof import('./db').run;
type QueryAllFn = typeof import('./db').queryAll;
type RecoverTaskChatReplyFn = typeof import('./chat-recovery').recoverTaskChatReply;

let run: RunFn;
let queryAll: QueryAllFn;
let recoverTaskChatReply: RecoverTaskChatReplyFn;

before(async () => {
  process.env.DATABASE_PATH = `.tmp/chat-recovery-${process.pid}.db`;
  ({ run, queryAll } = await import('./db'));
  ({ recoverTaskChatReply } = await import('./chat-recovery'));
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

function seedTask() {
  seedWorkspace();
  const agentId = crypto.randomUUID();
  const taskId = crypto.randomUUID();

  run(
    `INSERT INTO agents (id, name, role, avatar_emoji, status, workspace_id, source, created_at, updated_at)
     VALUES (?, 'Builder', 'builder', '🛠️', 'working', 'default', 'local', ?, ?)`,
    [agentId, minutesAgo(20), minutesAgo(1)]
  );

  run(
    `INSERT INTO tasks (id, title, status, priority, assigned_agent_id, workspace_id, business_id, created_at, updated_at)
     VALUES (?, 'Recover chat reply', 'in_progress', 'normal', ?, 'default', 'default', ?, ?)`,
    [taskId, agentId, minutesAgo(20), minutesAgo(1)]
  );

  run(
    `INSERT INTO task_notes (id, task_id, content, mode, role, status, delivered_at, created_at)
     VALUES (?, ?, 'hola', 'direct', 'user', 'delivered', ?, ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(10), minutesAgo(10)]
  );

  return taskId;
}

function assistantNotes(taskId: string) {
  return queryAll<{ content: string }>(
    `SELECT content FROM task_notes WHERE task_id = ? AND role = 'assistant' ORDER BY created_at ASC`,
    [taskId]
  );
}

test('recoverTaskChatReply creates assistant note only when a completion signal exists after user chat', () => {
  const taskId = seedTask();
  run(
    `INSERT INTO task_activities (id, task_id, agent_id, activity_type, message, created_at)
     VALUES (?, ?, NULL, 'completed', 'TASK_COMPLETE: Finished the requested work', ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(5)]
  );

  const result = recoverTaskChatReply(taskId);
  const notes = assistantNotes(taskId);

  assert.equal(result.status, 'recovered');
  assert.equal(notes.length, 1);
  assert.match(notes[0].content, /completion signal/);
  assert.match(notes[0].content, /TASK_COMPLETE/);
});

test('recoverTaskChatReply refuses to invent a reply without post-chat evidence', () => {
  const taskId = seedTask();

  const result = recoverTaskChatReply(taskId);

  assert.equal(result.status, 'no_recoverable_signal');
  assert.equal(assistantNotes(taskId).length, 0);
});

test('recoverTaskChatReply does not duplicate an already answered chat', () => {
  const taskId = seedTask();
  run(
    `INSERT INTO task_notes (id, task_id, content, mode, role, status, delivered_at, created_at)
     VALUES (?, ?, 'ya respondi', 'direct', 'assistant', 'delivered', ?, ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(9), minutesAgo(9)]
  );
  run(
    `INSERT INTO task_activities (id, task_id, agent_id, activity_type, message, created_at)
     VALUES (?, ?, NULL, 'completed', 'TASK_COMPLETE: Finished the requested work', ?)`,
    [crypto.randomUUID(), taskId, minutesAgo(5)]
  );

  const result = recoverTaskChatReply(taskId);

  assert.equal(result.status, 'already_answered');
  assert.equal(assistantNotes(taskId).length, 1);
});
