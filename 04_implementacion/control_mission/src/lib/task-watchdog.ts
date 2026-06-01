import { queryAll, queryOne, run } from '@/lib/db';
import { nudgeAgent } from '@/lib/agent-health';
import { getAgentByPreferredRoles } from '@/lib/agent-catalog-sync';

const WATCH_INTERVAL_MS = Number(process.env.TASK_WATCHDOG_INTERVAL_MS || 30_000);
const STALE_MINUTES = Number(process.env.TASK_WATCHDOG_STALE_MINUTES || 5);
const MAX_ATTEMPTS = Number(process.env.TASK_WATCHDOG_MAX_ATTEMPTS || 3);
const BACKOFF_MINUTES = Number(process.env.TASK_WATCHDOG_BACKOFF_MINUTES || 2); // base minutes for exponential backoff

const ACTIVE_TASK_STATUSES = ['assigned', 'in_progress', 'testing', 'verification'];

function minutesSinceIso(value?: string | null): number {
  if (!value) return Infinity;
  const ms = Date.parse(value);
  if (!Number.isFinite(ms)) return Infinity;
  return (Date.now() - ms) / 60000;
}

async function checkAndRecoverTask(task: any) {
  try {
    const age = minutesSinceIso(task.updated_at);
    if (age < STALE_MINUTES) return;

    // Ensure watchdog state table exists (persistent attempts counter)
    try {
      run(`CREATE TABLE IF NOT EXISTS watchdog_state (task_id TEXT PRIMARY KEY, attempts INTEGER DEFAULT 0, last_attempt_at TEXT)`);
    } catch (e) {
      // best-effort: if table creation fails, continue with in-memory behavior
    }

    // Load watchdog state
    const state = queryOne<{ task_id: string; attempts: number; last_attempt_at: string }>(
      `SELECT task_id, attempts, last_attempt_at FROM watchdog_state WHERE task_id = ?`,
      [task.id]
    );

    const attempts = state?.attempts || 0;
    const lastAttemptMinutes = state?.last_attempt_at ? minutesSinceIso(state.last_attempt_at) : Infinity;

    // Backoff: only proceed if enough time passed since last attempt
    if (attempts > 0 && lastAttemptMinutes < BACKOFF_MINUTES * Math.pow(2, Math.max(0, attempts - 1))) {
      return; // respect exponential backoff
    }

    // If assigned agent exists, try to nudge it first
    if (task.assigned_agent_id) {
      const nudge = await nudgeAgent(task.assigned_agent_id);
      if (nudge.success) {
        run(
          `INSERT INTO task_activities (id, task_id, agent_id, activity_type, message, created_at) VALUES (lower(hex(randomblob(16))), ?, ?, 'status_changed', ?, datetime('now'))`,
          [task.id, task.assigned_agent_id, 'Watchdog: Agent nudged automatically']
        );
        // reset attempts on success
        try { run(`DELETE FROM watchdog_state WHERE task_id = ?`, [task.id]); } catch (e) {}
        return;
      }
      // nudge failed — proceed to reassign
    }

    // Attempt to find another agent by preferred roles
    const preferred = ['orchestrator', 'builder', 'learner', 'advisor', 'tester'];
    const candidate = getAgentByPreferredRoles(task.id, preferred);
    if (candidate && candidate.id) {
      run(
        `UPDATE tasks SET assigned_agent_id = ?, updated_at = datetime('now') WHERE id = ?`,
        [candidate.id, task.id]
      );

      // increment attempt counter (upsert)
      const newAttempts = attempts + 1;
      try {
        run(`INSERT INTO watchdog_state (task_id, attempts, last_attempt_at) VALUES (?, ?, datetime('now')) ON CONFLICT(task_id) DO UPDATE SET attempts = ?, last_attempt_at = datetime('now')`, [task.id, newAttempts, newAttempts]);
      } catch (e) {
        try { run(`UPDATE watchdog_state SET attempts = ?, last_attempt_at = datetime('now') WHERE task_id = ?`, [newAttempts, task.id]); } catch (ee) {}
      }

      // If attempts exceeded threshold, mark for manual intervention
      if (newAttempts > MAX_ATTEMPTS) {
        run(
          `UPDATE tasks SET planning_dispatch_error = ?, status_reason = ?, updated_at = datetime('now') WHERE id = ?`,
          ['Watchdog: max recovery attempts exceeded', 'Manual intervention required: watchdog exhausted', task.id]
        );
        run(
          `INSERT INTO task_activities (id, task_id, activity_type, message, created_at) VALUES (lower(hex(randomblob(16))), ?, 'status_changed', ?, datetime('now'))`,
          [task.id, `Watchdog: exceeded max attempts (${newAttempts}) — manual recovery required`]
        );
        return;
      }

      // Trigger dispatch via API
      const mc = process.env.MISSION_CONTROL_URL || `http://localhost:${process.env.PORT || 4000}`;
      try {
        await fetch(`${mc}/api/tasks/${task.id}/dispatch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: AbortSignal.timeout(120_000),
        });
        run(
          `INSERT INTO task_activities (id, task_id, agent_id, activity_type, message, created_at) VALUES (lower(hex(randomblob(16))), ?, ?, 'status_changed', ?, datetime('now'))`,
          [task.id, candidate.id, `Watchdog: Reassigned to ${candidate.name} and dispatched (attempt ${newAttempts})`]
        );
        // reset attempts on success
        try { run(`DELETE FROM watchdog_state WHERE task_id = ?`, [task.id]); } catch (e) {}
        return;
      } catch (err) {
        run(
          `INSERT INTO task_activities (id, task_id, activity_type, message, created_at) VALUES (lower(hex(randomblob(16))), ?, 'status_changed', ?, datetime('now'))`,
          [task.id, `Watchdog dispatch to ${candidate.id} failed: ${(err as Error).message}`]
        );
      }
    }

    // Last resort: mark planning_dispatch_error so operators see it
    run(
      `UPDATE tasks SET planning_dispatch_error = ?, status_reason = ?, updated_at = datetime('now') WHERE id = ?`,
      ['Watchdog: no available agent to recover', 'Watchdog recovery needed', task.id]
    );
    run(
      `INSERT INTO task_activities (id, task_id, activity_type, message, created_at) VALUES (lower(hex(randomblob(16))), ?, 'status_changed', ?, datetime('now'))`,
      [task.id, 'Watchdog: No recovery path found — manual intervention required']
    );
  } catch (err) {
    console.error('[Watchdog] Failed to recover task', task.id, (err as Error).message);
  }
}

export function ensureTaskWatchdogScheduled(): void {
  if (process.env.NODE_ENV === 'test') return;
  const g = globalThis as unknown as { __mcTaskWatchdog?: NodeJS.Timeout };
  if (g.__mcTaskWatchdog) return;

  g.__mcTaskWatchdog = setInterval(async () => {
    try {
      const tasks = queryAll<any>(
        `SELECT id, title, status, assigned_agent_id, updated_at FROM tasks WHERE status IN (${ACTIVE_TASK_STATUSES.map(() => '?').join(',')})`,
        [...ACTIVE_TASK_STATUSES]
      );
      for (const t of tasks) {
        // fire-and-forget per task but sequential to avoid DB contention
        // eslint-disable-next-line no-await-in-loop
        await checkAndRecoverTask(t);
      }
    } catch (err) {
      console.error('[Watchdog] scan failed:', (err as Error).message);
    }
  }, WATCH_INTERVAL_MS);
}

export default ensureTaskWatchdogScheduled;
