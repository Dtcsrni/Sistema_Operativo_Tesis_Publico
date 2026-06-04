import './setup-test-env';
import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import path from 'path';
import fs from 'fs';

import { run, queryOne, closeDb } from './db';
import { handleStageTransition, handleStageFailure, populateTaskRolesFromAgents } from './workflow-engine';
import { hasStageEvidence } from './task-governance';

// Mock global fetch to avoid network calls during dispatch
const originalFetch = global.fetch;
global.fetch = async (url: string | URL | Request, init?: RequestInit) => {
  const urlStr = url.toString();
  if (urlStr.includes('/api/tasks/') && urlStr.includes('/dispatch')) {
    return {
      ok: true,
      status: 200,
      json: async () => ({ success: true, message: 'Mocked dispatch success' }),
      text: async () => JSON.stringify({ success: true }),
    } as Response;
  }
  return originalFetch(url, init);
};

// Seed workspace, agents and strict template
function seedTestDatabase() {
  run(
    `INSERT OR IGNORE INTO workspaces (id, name, slug, description, created_at, updated_at)
     VALUES ('default', 'Default', 'default', '', datetime('now'), datetime('now'))`
  );
  
  run(`DELETE FROM agents WHERE workspace_id = 'default'`);
  
  run(
    `INSERT OR IGNORE INTO agents (id, name, role, description, avatar_emoji, status, is_master, workspace_id, source, created_at, updated_at)
     VALUES ('builder-id', 'Builder Agent', 'builder', 'Desc', '🛠️', 'standby', 0, 'default', 'local', datetime('now'), datetime('now'))`
  );
  
  run(
    `INSERT OR IGNORE INTO agents (id, name, role, description, avatar_emoji, status, is_master, workspace_id, source, created_at, updated_at)
     VALUES ('tester-id', 'Tester Agent', 'tester', 'Desc', '🧪', 'standby', 0, 'default', 'local', datetime('now'), datetime('now'))`
  );
  
  run(
    `INSERT OR IGNORE INTO agents (id, name, role, description, avatar_emoji, status, is_master, workspace_id, source, created_at, updated_at)
     VALUES ('reviewer-id', 'Reviewer Agent', 'reviewer', 'Desc', '🔎', 'standby', 0, 'default', 'local', datetime('now'), datetime('now'))`
  );

  const stages = [
    { id: 'build', label: 'Build', role: 'builder', status: 'in_progress' },
    { id: 'test', label: 'Test', role: 'tester', status: 'testing' },
    { id: 'review', label: 'Review', role: null, status: 'review' },
    { id: 'verify', label: 'Verify', role: 'reviewer', status: 'verification' },
    { id: 'done', label: 'Done', role: null, status: 'done' }
  ];
  
  const failTargets = {
    testing: 'in_progress',
    review: 'in_progress',
    verification: 'in_progress'
  };

  run(
    `INSERT OR IGNORE INTO workflow_templates (id, workspace_id, name, description, stages, fail_targets, is_default, created_at, updated_at)
     VALUES ('tpl-strict', 'default', 'Strict', 'Strict template', ?, ?, 1, datetime('now'), datetime('now'))`,
    [JSON.stringify(stages), JSON.stringify(failTargets)]
  );
}

// Cleanup database files and deliverables
after(() => {
  global.fetch = originalFetch;
  closeDb();
  
  // Clean up mock deliverable file
  const mockFile = path.join(__dirname, 'mock-deliverable.html');
  if (fs.existsSync(mockFile)) {
    try { fs.unlinkSync(mockFile); } catch {}
  }
  
  // Delete SQLite test database files
  const TEST_DB = path.join(__dirname, 'workflow-integration-test.db');
  for (const ext of ['', '-wal', '-shm']) {
    try {
      fs.unlinkSync(TEST_DB + ext);
    } catch {}
  }
});

test('E2E Mission Control Workflow Engine Integration Test', async () => {
  try {
    seedTestDatabase();

  const taskId = 'integration-task-uuid-123';
  const now = new Date().toISOString();

  // Create mock deliverable file to satisfy hasStageEvidence checks
  const mockDeliverablePath = path.join(__dirname, 'mock-deliverable.html');
  fs.writeFileSync(mockDeliverablePath, 'mock HTML payload content');

  // 1. Create a task in 'inbox' status
  run(
    `INSERT INTO tasks (id, title, status, priority, workspace_id, business_id, created_at, updated_at)
     VALUES (?, 'Test Integration Task', 'inbox', 'normal', 'default', 'default', ?, ?)`,
    [taskId, now, now]
  );

  populateTaskRolesFromAgents(taskId, 'default');

  const t1 = queryOne<{ status: string }>('SELECT status FROM tasks WHERE id = ?', [taskId]);
  assert.equal(t1?.status, 'inbox');

  // 2. Assign to builder agent (Inbox -> In Progress)
  run(`UPDATE tasks SET status = 'in_progress', assigned_agent_id = 'builder-id', updated_at = ? WHERE id = ?`, [now, taskId]);
  const transition1 = await handleStageTransition(taskId, 'in_progress');
  assert.ok(transition1.success);
  assert.ok(transition1.handedOff);
  assert.equal(transition1.newAgentId, 'builder-id');

  // 3. Complete work: Add deliverable + activity note and transition (In Progress -> Testing)
  run(`UPDATE tasks SET status = 'in_progress', updated_at = ? WHERE id = ?`, [now, taskId]);
  
  run(
    `INSERT INTO task_deliverables (id, task_id, deliverable_type, title, path, created_at)
     VALUES ('del-1', ?, 'file', 'mock-deliverable.html', ?, datetime('now'))`,
    [taskId, mockDeliverablePath]
  );
  
  run(
    `INSERT INTO task_activities (id, task_id, activity_type, message, created_at)
     VALUES ('act-1', ?, 'completed', 'Implemented basic features', datetime('now'))`,
    [taskId]
  );

  assert.ok(hasStageEvidence(taskId));

  run(`UPDATE tasks SET status = 'testing', updated_at = ? WHERE id = ?`, [now, taskId]);
  const transition2 = await handleStageTransition(taskId, 'testing');
  assert.ok(transition2.success);
  assert.ok(transition2.handedOff);
  assert.equal(transition2.newAgentId, 'tester-id');

  const taskAfterTesting = queryOne<{ assigned_agent_id: string; status: string }>('SELECT assigned_agent_id, status FROM tasks WHERE id = ?', [taskId]);
  assert.equal(taskAfterTesting?.assigned_agent_id, 'tester-id');
  assert.equal(taskAfterTesting?.status, 'testing');

  // 4. Testing fails: Loopback to In Progress and reassign to Builder
  const failTransition = await handleStageFailure(taskId, 'testing', 'Broken styles');
  assert.ok(failTransition.success);
  assert.ok(failTransition.handedOff);
  assert.equal(failTransition.newAgentId, 'builder-id');

  const taskAfterFailure = queryOne<{ assigned_agent_id: string; status: string; status_reason: string }>('SELECT assigned_agent_id, status, status_reason FROM tasks WHERE id = ?', [taskId]);
  assert.equal(taskAfterFailure?.assigned_agent_id, 'builder-id');
  assert.equal(taskAfterFailure?.status, 'in_progress');
  assert.equal(taskAfterFailure?.status_reason, 'Failed: Broken styles');

  // 5. Correct issue, advance back to testing and then to review (Testing -> Review)
  // Review has role = null, so it should auto-drain to verification and assign reviewer
  run(`UPDATE tasks SET status = 'testing', updated_at = ? WHERE id = ?`, [now, taskId]);
  await handleStageTransition(taskId, 'testing');
  
  run(`UPDATE tasks SET status = 'review', updated_at = ? WHERE id = ?`, [now, taskId]);
  const transitionToReview = await handleStageTransition(taskId, 'review');
  // It enters queue stage, triggers drainQueue and advances to verification
  assert.ok(transitionToReview.success);
  assert.equal(transitionToReview.handedOff, false); // review stage has no role

  const taskAfterReview = queryOne<{ assigned_agent_id: string; status: string }>('SELECT assigned_agent_id, status FROM tasks WHERE id = ?', [taskId]);
  assert.equal(taskAfterReview?.assigned_agent_id, 'reviewer-id');
  assert.equal(taskAfterReview?.status, 'verification');

  // 6. Verification passes, mark task as done (Verification -> Done)
  run(`UPDATE tasks SET status = 'done', updated_at = ? WHERE id = ?`, [now, taskId]);
  const transitionToDone = await handleStageTransition(taskId, 'done');
  assert.ok(transitionToDone.success);

  const taskAfterDone = queryOne<{ status: string }>('SELECT status FROM tasks WHERE id = ?', [taskId]);
  assert.equal(taskAfterDone?.status, 'done');
  } catch (err) {
    console.error('[ERROR IN TEST]', err);
    throw err;
  }
});
