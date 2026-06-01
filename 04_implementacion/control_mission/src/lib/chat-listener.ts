/**
 * Chat Listener — captures agent responses to user chat messages.
 *
 * Strategy: tracks which sessionKeys have pending user chat messages, and also
 * recovers from process restarts by looking for the latest delivered user note
 * without a later assistant note for the active OpenClaw session.
 */
import { getOpenClawClient } from '@/lib/openclaw/client';
import { queryAll } from '@/lib/db';
import { createNote } from '@/lib/task-notes';
import { broadcast } from '@/lib/events';
import type { OpenClawSession } from '@/lib/types';

const REPLY_CAPTURE_WINDOW_MS = 30 * 60 * 1000;
const LISTENER_STATE_KEY = '__chat_listener_state__';

// Sessions awaiting a reply: sessionKey → { taskId, sentAt }
const PENDING_KEY = '__chat_pending_replies__';
if (!(PENDING_KEY in globalThis)) {
  (globalThis as Record<string, unknown>)[PENDING_KEY] = new Map<string, { taskId: string; sentAt: number }>();
}
const pendingReplies = (globalThis as unknown as Record<string, Map<string, { taskId: string; sentAt: number }>>)[PENDING_KEY];

interface ChatEventPayload {
  runId?: string;
  sessionKey?: string;
  seq?: number;
  state?: string;
  message?: string | { role?: string; content?: unknown };
}

interface ChatSendResult {
  response?: {
    text?: unknown;
    assistant_text?: unknown;
  };
  outbound?: {
    text?: unknown;
  };
}

interface AwaitingReply {
  taskId: string;
  sentAt: number;
  source: 'memory' | 'database';
}

interface ChatListenerState {
  client?: ReturnType<typeof getOpenClawClient>;
  chatHandler?: (payload: ChatEventPayload) => void;
  connectedHandler?: () => void;
}

interface TaskRow {
  id: string;
}

interface ReplyNormalization {
  action: 'store' | 'ignore';
  content: string;
  kind: 'normal' | 'completion' | 'prompt_leak' | 'empty';
}

interface NoteRow {
  id: string;
  role: 'user' | 'assistant';
  status: string;
  content: string;
  created_at: string;
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

/**
 * Mark a session as expecting a reply from the agent.
 * Called by the chat route after sending a message.
 */
export function expectReply(sessionKey: string, taskId: string): void {
  pendingReplies.set(sessionKey, { taskId, sentAt: Date.now() });
  // Auto-expire after the same window used for DB recovery.
  const expiryTimer = setTimeout(() => {
    const entry = pendingReplies.get(sessionKey);
    if (entry && Date.now() - entry.sentAt >= REPLY_CAPTURE_WINDOW_MS) {
      pendingReplies.delete(sessionKey);
    }
  }, REPLY_CAPTURE_WINDOW_MS);
  expiryTimer.unref?.();
}

export function extractContent(message: ChatEventPayload['message']): string {
  if (typeof message === 'string') return message;
  if (!message || typeof message !== 'object') return '';
  if (typeof message.content === 'string') return message.content;
  if (Array.isArray(message.content)) {
    return (message.content as Array<{ type?: string; text?: string }>)
      .filter(c => c.type === 'text' && c.text)
      .map(c => c.text!)
      .join('\n');
  }
  return '';
}

export function normalizeAgentReplyForChat(rawContent: string): ReplyNormalization {
  const content = rawContent.trim();
  if (!content) {
    return { action: 'ignore', content: '', kind: 'empty' };
  }

  const upper = content.toUpperCase();
  const looksLikeDispatchPrompt = upper.includes('NEW TASK ASSIGNED') || upper.includes('OUTPUT DIRECTORY:');

  // Keep protecting the UI from assignment prompt leakage, but do not throw away
  // completion replies. Those are exactly what operators need to see when they ask
  // “what happened?” while a task is running.
  if (looksLikeDispatchPrompt && !upper.includes('TASK_COMPLETE:') && !upper.includes('TEST_PASS:') && !upper.includes('VERIFY_PASS:')) {
    return { action: 'ignore', content: '', kind: 'prompt_leak' };
  }

  if (upper.includes('TASK_COMPLETE:') || upper.includes('TEST_PASS:') || upper.includes('VERIFY_PASS:')) {
    const cleaned = content
      .replace(/^TASK_COMPLETE:\s*/i, '✅ Task complete — ')
      .replace(/^TEST_PASS:\s*/i, '✅ Test passed — ')
      .replace(/^VERIFY_PASS:\s*/i, '✅ Verification passed — ');
    return { action: 'store', content: cleaned, kind: 'completion' };
  }

  return { action: 'store', content, kind: 'normal' };
}

function sessionMatches(sessionKey: string, openclawSessionId: string): boolean {
  return sessionKey === openclawSessionId || sessionKey.endsWith(openclawSessionId);
}

function latestAwaitingReplyForTask(taskId: string): AwaitingReply | null {
  const notes = queryAll<NoteRow>(
    `SELECT id, role, status, content, created_at
     FROM task_notes
     WHERE task_id = ?
     ORDER BY created_at ASC`,
    [taskId]
  );

  const lastUser = [...notes].reverse().find(n => n.role === 'user' && n.status === 'delivered');
  if (!lastUser) return null;

  const lastUserAt = parseTimestampMs(lastUser.created_at);
  if (!lastUserAt) return null;

  const hasAssistantAfter = notes.some(n => n.role === 'assistant' && parseTimestampMs(n.created_at) > lastUserAt);
  if (hasAssistantAfter) return null;

  return { taskId, sentAt: lastUserAt, source: 'database' };
}

function latestAwaitingReplyFromDb(sessionKey: string): AwaitingReply | null {
  const activeSessions = queryAll<OpenClawSession>(
    `SELECT * FROM openclaw_sessions WHERE status = 'active' ORDER BY created_at DESC`
  );

  const session = activeSessions.find(s => sessionMatches(sessionKey, s.openclaw_session_id));
  if (!session) return null;

  if (session.task_id) {
    return latestAwaitingReplyForTask(session.task_id);
  }

  if (!session.agent_id) return null;

  const activeTasks = queryAll<TaskRow>(
    `SELECT id
     FROM tasks
     WHERE assigned_agent_id = ?
       AND status IN ('assigned', 'in_progress', 'testing', 'review', 'verification')
     ORDER BY updated_at DESC`,
    [session.agent_id]
  );

  for (const task of activeTasks) {
    const awaiting = latestAwaitingReplyForTask(task.id);
    if (awaiting) return awaiting;
  }

  return null;
}

function getPendingReply(sessionKey: string): AwaitingReply | null {
  const pending = pendingReplies.get(sessionKey);
  if (pending) return { ...pending, source: 'memory' };
  return latestAwaitingReplyFromDb(sessionKey);
}

function getListenerState(): ChatListenerState {
  if (!(LISTENER_STATE_KEY in globalThis)) {
    (globalThis as Record<string, unknown>)[LISTENER_STATE_KEY] = {};
  }
  return (globalThis as unknown as Record<string, ChatListenerState>)[LISTENER_STATE_KEY];
}

export function processChatEventForReply(payload: ChatEventPayload): 'stored' | 'ignored' {
  if (!payload.sessionKey) return 'ignored';

  // Only process final (complete) messages.
  if (payload.state !== 'final') return 'ignored';

  // Check if this session is expecting a reply; recover from DB if the in-memory
  // pending map was lost by hot reload/restart or an older expectation expired.
  const pending = getPendingReply(payload.sessionKey);
  if (!pending) return 'ignored';

  const normalized = normalizeAgentReplyForChat(extractContent(payload.message));
  if (normalized.action === 'ignore') return 'ignored';

  // Got the reply — store it and clear the pending flag.
  pendingReplies.delete(payload.sessionKey);

  try {
    console.log(`[ChatListener] Agent replied for task ${pending.taskId} (${normalized.kind}, ${pending.source}): ${normalized.content.slice(0, 100)}...`);
    const note = createNote(pending.taskId, normalized.content, 'direct', 'assistant');
    broadcast({ type: 'note_delivered', payload: { taskId: pending.taskId, noteId: note.id, kind: normalized.kind } });
    return 'stored';
  } catch (err) {
    console.error('[ChatListener] Failed to store agent response:', err);
    return 'ignored';
  }
}

export function processChatSendResultForReply(sessionKey: string, taskId: string, result: unknown): 'stored' | 'ignored' {
  if (!sessionKey || !taskId || !result || typeof result !== 'object') return 'ignored';

  const payload = result as ChatSendResult;
  const content =
    (typeof payload.response?.assistant_text === 'string' && payload.response.assistant_text) ||
    (typeof payload.response?.text === 'string' && payload.response.text) ||
    (typeof payload.outbound?.text === 'string' && payload.outbound.text) ||
    '';

  if (!content.trim()) return 'ignored';

  return processChatEventForReply({
    sessionKey,
    state: 'final',
    message: { role: 'assistant', content },
  });
}

export function attachChatListener(): void {
  const client = getOpenClawClient();
  const state = getListenerState();

  if (state.client && state.client !== client) {
    if (state.chatHandler) state.client.removeListener('chat_event', state.chatHandler);
    if (state.connectedHandler) state.client.removeListener('connected', state.connectedHandler);
  }

  if (!state.chatHandler) {
    state.chatHandler = (payload: ChatEventPayload) => {
      processChatEventForReply(payload);
    };
  }

  if (!state.connectedHandler) {
    state.connectedHandler = () => {
      attachChatListener();
    };
  }

  state.client = client;

  if (client.listenerCount('chat_event', state.chatHandler) === 0) {
    client.on('chat_event', state.chatHandler);
    console.log('[ChatListener] Attached to OpenClaw client');
  }

  if (client.listenerCount('connected', state.connectedHandler) === 0) {
    client.on('connected', state.connectedHandler);
  }
}

export const __chatListenerTestUtils = {
  parseTimestampMs,
  latestAwaitingReplyFromDb,
  getListenerState,
  pendingReplies,
};
