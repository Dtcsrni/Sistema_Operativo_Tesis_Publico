import test, { after } from 'node:test';
import assert from 'node:assert/strict';

// Prevent background tasks/WebSocket initialization during test
process.env.NODE_ENV = 'test';

import { run, queryOne } from './db';
import {
  hasStageEvidence,
  taskCanBeDone,
  ensureFixerExists,
  getFailureCountInStage,
} from './task-governance';

import fs from 'node:fs';

const seededTaskIds: string[] = [];

function seedTask(id: string, workspace = 'default') {
  seededTaskIds.push(id);
  run(
    `INSERT INTO tasks (id, title, status, priority, workspace_id, business_id, created_at, updated_at)
     VALUES (?, 'T', 'review', 'normal', ?, 'default', datetime('now'), datetime('now'))`,
    [id, workspace]
  );
}

after(() => {
  if (seededTaskIds.length > 0) {
    const placeholders = seededTaskIds.map(() => '?').join(',');
    run(`DELETE FROM task_deliverables WHERE task_id IN (${placeholders})`, seededTaskIds);
    run(`DELETE FROM task_activities WHERE task_id IN (${placeholders})`, seededTaskIds);
    run(`DELETE FROM work_checkpoints WHERE task_id IN (${placeholders})`, seededTaskIds);
    run(`DELETE FROM tasks WHERE id IN (${placeholders})`, seededTaskIds);
  }
});

test('evidence gate requires deliverable + activity', () => {
  const taskId = crypto.randomUUID();
  seedTask(taskId);

  assert.equal(hasStageEvidence(taskId), false);

  run(
    `INSERT INTO task_deliverables (id, task_id, deliverable_type, title, created_at)
     VALUES (lower(hex(randomblob(16))), ?, 'file', 'index.html', datetime('now'))`,
    [taskId]
  );
  assert.equal(hasStageEvidence(taskId), false);

  run(
    `INSERT INTO task_activities (id, task_id, activity_type, message, created_at)
     VALUES (lower(hex(randomblob(16))), ?, 'completed', 'did thing', datetime('now'))`,
    [taskId]
  );

  assert.equal(hasStageEvidence(taskId), true);
});

test('hasStageEvidence verifies physical file existence and non-zero size', () => {
  const taskId = crypto.randomUUID();
  seedTask(taskId);

  // Deliverable with non-existent path
  const nonExistentPath = 'non_existent_file_test.txt';
  run(
    `INSERT INTO task_deliverables (id, task_id, deliverable_type, title, path, created_at)
     VALUES (lower(hex(randomblob(16))), ?, 'file', 'index.html', ?, datetime('now'))`,
    [taskId, nonExistentPath]
  );

  run(
    `INSERT INTO task_activities (id, task_id, activity_type, message, created_at)
     VALUES (lower(hex(randomblob(16))), ?, 'completed', 'did thing', datetime('now'))`,
    [taskId]
  );

  // non-existent file should be invalid
  assert.equal(hasStageEvidence(taskId), false);

  // Create empty file (0 bytes)
  const emptyPath = 'empty_test_file.txt';
  fs.writeFileSync(emptyPath, '');

  run(
    `UPDATE task_deliverables SET path = ? WHERE task_id = ?`,
    [emptyPath, taskId]
  );

  // empty file should be invalid
  assert.equal(hasStageEvidence(taskId), false);

  // Write content to file (> 0 bytes)
  fs.writeFileSync(emptyPath, 'evidence report data');

  // non-empty file should be valid
  assert.equal(hasStageEvidence(taskId), true);

  // Clean up
  try {
    fs.unlinkSync(emptyPath);
  } catch {}
});

test('task cannot be done when status_reason indicates failure', () => {
  const taskId = crypto.randomUUID();
  seedTask(taskId);

  run(`UPDATE tasks SET status_reason = 'Validation failed: CSS broken' WHERE id = ?`, [taskId]);
  run(
    `INSERT INTO task_deliverables (id, task_id, deliverable_type, title, created_at)
     VALUES (lower(hex(randomblob(16))), ?, 'file', 'index.html', datetime('now'))`,
    [taskId]
  );
  run(
    `INSERT INTO task_activities (id, task_id, activity_type, message, created_at)
     VALUES (lower(hex(randomblob(16))), ?, 'completed', 'did thing', datetime('now'))`,
    [taskId]
  );

  assert.equal(taskCanBeDone(taskId), false);
});

test('ensureFixerExists creates fixer when missing', () => {
  // Clean up any pre-existing fixer/senior agents in 'default' workspace
  // to avoid state leakage from other tests that may have seeded agents
  run(`DELETE FROM agents WHERE workspace_id = 'default' AND role IN ('fixer', 'senior')`);

  const fixer = ensureFixerExists('default');
  assert.equal(fixer.created, true);

  const stored = queryOne<{ id: string; role: string }>('SELECT id, role FROM agents WHERE id = ?', [fixer.id]);
  assert.ok(stored);
  assert.equal(stored?.role, 'fixer');
});

test('failure counter reads status_changed failure events', () => {
  const taskId = crypto.randomUUID();
  seedTask(taskId);

  run(
    `INSERT INTO task_activities (id, task_id, activity_type, message, created_at)
     VALUES (lower(hex(randomblob(16))), ?, 'status_changed', 'Stage failed: verification → in_progress (reason: x)', datetime('now'))`,
    [taskId]
  );
  run(
    `INSERT INTO task_activities (id, task_id, activity_type, message, created_at)
     VALUES (lower(hex(randomblob(16))), ?, 'status_changed', 'Stage failed: verification → in_progress (reason: y)', datetime('now'))`,
    [taskId]
  );

  assert.equal(getFailureCountInStage(taskId, 'verification'), 2);
});
