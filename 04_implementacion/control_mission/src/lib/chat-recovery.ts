import { queryAll, queryOne } from '@/lib/db';
import { createNote } from '@/lib/task-notes';

interface NoteRow {
  id: string;
  role: 'user' | 'assistant';
  status: string;
  content: string;
  created_at: string;
}

interface ActivityRow {
  id: string;
  activity_type: string;
  message: string;
  created_at: string;
}

interface DeliverableRow {
  id: string;
  title: string;
  deliverable_type: string;
  path?: string;
  created_at: string;
}

export interface ChatRecoveryResult {
  status: 'recovered' | 'not_found' | 'no_delivered_user_message' | 'already_answered' | 'no_recoverable_signal';
  note_id?: string;
  reason: string;
}

function parseTimestampMs(value?: string | null): number {
  if (!value) return 0;
  const trimmed = value.trim();
  if (!trimmed) return 0;
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(trimmed);
  const normalized = trimmed.includes('T')
    ? (hasTimezone ? trimmed : `${trimmed}Z`)
    : `${trimmed.replace(' ', 'T')}Z`;
  const parsed = Date.parse(normalized);
  return Number.isFinite(parsed) ? parsed : Date.parse(trimmed);
}

function isCompletionLike(activity: ActivityRow): boolean {
  const msg = activity.message.toLowerCase();
  return activity.activity_type === 'completed'
    || msg.includes('task_complete:')
    || msg.includes('test_pass:')
    || msg.includes('verify_pass:')
    || msg.includes('stage handoff')
    || msg.includes('handed off');
}

function trimDetail(value: string, max = 320): string {
  const trimmed = value.trim();
  return trimmed.length > max ? `${trimmed.slice(0, max - 1)}...` : trimmed;
}

export function recoverTaskChatReply(taskId: string): ChatRecoveryResult {
  const task = queryOne<{ id: string }>('SELECT id FROM tasks WHERE id = ?', [taskId]);
  if (!task) {
    return { status: 'not_found', reason: 'Task not found.' };
  }

  const notes = queryAll<NoteRow>(
    `SELECT id, role, status, content, created_at
     FROM task_notes
     WHERE task_id = ?
     ORDER BY created_at ASC`,
    [taskId]
  );

  const latestUser = [...notes].reverse().find(n => n.role === 'user' && n.status === 'delivered');
  if (!latestUser) {
    return { status: 'no_delivered_user_message', reason: 'No delivered operator chat message exists for this task.' };
  }

  const latestUserAt = parseTimestampMs(latestUser.created_at);
  const hasAssistantAfter = notes.some(n => n.role === 'assistant' && parseTimestampMs(n.created_at) > latestUserAt);
  if (hasAssistantAfter) {
    return { status: 'already_answered', reason: 'The latest delivered operator message already has an assistant note after it.' };
  }

  const activities = queryAll<ActivityRow>(
    `SELECT id, activity_type, message, created_at
     FROM task_activities
     WHERE task_id = ?
     ORDER BY created_at ASC`,
    [taskId]
  ).filter(a => parseTimestampMs(a.created_at) > latestUserAt);

  const completion = activities.find(isCompletionLike);
  if (completion) {
    const note = createNote(
      taskId,
      `Mission Control recovery: the agent emitted a completion signal after your message, but no live chat reply was captured. Signal: ${trimDetail(completion.message)}`,
      'direct',
      'assistant'
    );
    return { status: 'recovered', note_id: note.id, reason: 'Recovered from completion activity after the delivered operator message.' };
  }

  const deliverable = queryOne<DeliverableRow>(
    `SELECT id, title, deliverable_type, path, created_at
     FROM task_deliverables
     WHERE task_id = ?
       AND created_at > ?
     ORDER BY created_at ASC
     LIMIT 1`,
    [taskId, latestUser.created_at]
  );

  if (deliverable) {
    const descriptor = deliverable.path || deliverable.title || deliverable.deliverable_type;
    const note = createNote(
      taskId,
      `Mission Control recovery: the agent registered a deliverable after your message, but no live chat reply was captured. Deliverable: ${trimDetail(descriptor)}`,
      'direct',
      'assistant'
    );
    return { status: 'recovered', note_id: note.id, reason: 'Recovered from deliverable registered after the delivered operator message.' };
  }

  return {
    status: 'no_recoverable_signal',
    reason: 'No completion activity or deliverable was recorded after the latest delivered operator message.',
  };
}
