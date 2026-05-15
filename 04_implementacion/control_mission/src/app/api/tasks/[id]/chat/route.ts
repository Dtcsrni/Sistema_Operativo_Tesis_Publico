import { NextRequest, NextResponse } from 'next/server';
import { createNote, getTaskNotes, getActiveSessionForTask, markNotesDelivered } from '@/lib/task-notes';
import { getOpenClawClient } from '@/lib/openclaw/client';
import { getMissionControlUrl } from '@/lib/config';
import { attachChatListener, expectReply, processChatSendResultForReply } from '@/lib/chat-listener';
import { queryOne } from '@/lib/db';
import { broadcast } from '@/lib/events';
import type { Task } from '@/lib/types';

export const dynamic = 'force-dynamic';

interface RouteParams {
  params: Promise<{ id: string }>;
}

// GET /api/tasks/[id]/chat — Get chat history
export async function GET(
  request: NextRequest,
  { params }: RouteParams
) {
  try {
    // Ensure reply listener is attached even when the task chat UI is used without
    // an SSE subscriber. TaskChatTab polls /api/tasks/:id/chat directly and may
    // never open /api/events/stream, so relying only on SSE causes replies to be missed.
    attachChatListener();

    const { id } = await params;
    const notes = getTaskNotes(id);
    return NextResponse.json(notes);
  } catch (error) {
    console.error('Failed to fetch task notes:', error);
    return NextResponse.json({ error: 'Failed to fetch task notes' }, { status: 500 });
  }
}

// POST /api/tasks/[id]/chat — Send a message to the agent
export async function POST(
  request: NextRequest,
  { params }: RouteParams
) {
  try {
    attachChatListener();

    const { id: taskId } = await params;
    const body = await request.json();
    const { message } = body as { message?: string };

    if (!message || !message.trim()) {
      return NextResponse.json({ error: 'Message is required' }, { status: 400 });
    }

    // Check task exists and is in a dispatchable state
    const task = queryOne<Task>('SELECT * FROM tasks WHERE id = ?', [taskId]);
    if (!task) {
      return NextResponse.json({ error: 'Task not found' }, { status: 404 });
    }

    // Store the user message
    const note = createNote(taskId, message.trim(), 'direct', 'user');
    broadcast({ type: 'note_queued', payload: { taskId, noteId: note.id } });

    // Try to deliver to the agent
    let delivered = false;
    const sessionInfo = getActiveSessionForTask(taskId);

    if (sessionInfo) {
      try {
        const client = getOpenClawClient();
        if (!client.isConnected()) {
          await client.connect();
        }

        const sendPromise = client.call('chat.send', {
          sessionKey: sessionInfo.sessionKey,
          message: message.trim(),
          idempotencyKey: `chat-${note.id}`
        }, 300_000);

        delivered = true;
        markNotesDelivered([note.id]);
        expectReply(sessionInfo.sessionKey, taskId);
        void sendPromise
          .then((sendResult) => {
            processChatSendResultForReply(sessionInfo.sessionKey, taskId, sendResult);
          })
          .catch((err) => {
            console.warn('[Chat] chat.send failed after delivery handoff:', err);
          });
        console.log(`[Chat] Message handed off via chat.send to ${sessionInfo.sessionKey}`);
      } catch (err) {
        console.log('[Chat] chat.send handoff failed — will try dispatch fallback', err);
      }
    }

    // Fall back to dispatch only if:
    // 1. Message wasn't delivered via chat.send
    // 2. Task is in a state where dispatch makes sense (not done, not already in_progress)
    if (!delivered && ['assigned', 'inbox', 'testing', 'review', 'verification'].includes(task.status)) {
      try {
        const missionControlUrl = getMissionControlUrl();
        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (process.env.MC_API_TOKEN) {
          headers['Authorization'] = `Bearer ${process.env.MC_API_TOKEN}`;
        }

        const dispatchRes = await fetch(`${missionControlUrl}/api/tasks/${taskId}/dispatch`, {
          method: 'POST',
          headers,
          signal: AbortSignal.timeout(30_000),
        });

        if (dispatchRes.ok) {
          delivered = true;
          markNotesDelivered([note.id]);
          // Track the session for reply capture
          const freshSession = getActiveSessionForTask(taskId);
          if (freshSession) expectReply(freshSession.sessionKey, taskId);
          console.log(`[Chat] Message delivered via dispatch for task ${taskId}`);
        } else {
          const errText = await dispatchRes.text();
          console.warn(`[Chat] Dispatch fallback failed (${dispatchRes.status}):`, errText);
        }
      } catch (err) {
        console.error('[Chat] Dispatch fallback error:', err);
      }
    }

    if (!delivered) {
      console.log(`[Chat] Message queued as pending note for task ${taskId} (status: ${task.status})`);
    }

    // Return the saved note
    const updatedNote = getTaskNotes(taskId).find(n => n.id === note.id) || note;
    return NextResponse.json(updatedNote, { status: 201 });
  } catch (error) {
    console.error('Failed to send chat message:', error);
    return NextResponse.json({ error: 'Failed to send message' }, { status: 500 });
  }
}
