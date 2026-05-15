import { NextResponse } from 'next/server';
import { recoverTaskChatReply } from '@/lib/chat-recovery';
import { broadcast } from '@/lib/events';

export const dynamic = 'force-dynamic';

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function POST(
  request: Request,
  { params }: RouteParams
) {
  try {
    const { id: taskId } = await params;
    const result = recoverTaskChatReply(taskId);

    if (result.status === 'recovered') {
      broadcast({ type: 'note_delivered', payload: { taskId, noteId: result.note_id, kind: 'recovery' } });
      return NextResponse.json(result, { status: 201 });
    }

    const status = result.status === 'not_found' ? 404 : 409;
    return NextResponse.json(result, { status });
  } catch (error) {
    console.error('Failed to recover task chat reply:', error);
    return NextResponse.json({ error: 'Failed to recover task chat reply' }, { status: 500 });
  }
}
