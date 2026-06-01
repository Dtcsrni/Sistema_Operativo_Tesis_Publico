import { getOpenClawClient } from './openclaw/client';

export interface ToolApprovalRequest {
  approvalId: string;
  draft: string;
  hint: string;
}

/**
 * Extract JSON from a response that might have markdown code blocks or surrounding text.
 */
export function extractJSON(text: string): Record<string, unknown> | null {
  if (text.length > 1000000) return null;

  try {
    const parsed = JSON.parse(text.trim());
    return typeof parsed === 'object' && parsed !== null ? parsed : null;
  } catch {
    // Continue
  }

  const codeBlock = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (codeBlock) {
    try {
      const parsed = JSON.parse(codeBlock[1].trim());
      return typeof parsed === 'object' && parsed !== null ? parsed : null;
    } catch {
      // Continue
    }
  }

  const firstBrace = text.indexOf('{');
  const lastBrace = text.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    try {
      const parsed = JSON.parse(text.slice(firstBrace, lastBrace + 1));
      return typeof parsed === 'object' && parsed !== null ? parsed : null;
    } catch {
      // Continue
    }
  }

  return null;
}

/**
 * Extract a tool approval request from a message if present.
 */
export function extractApprovalRequest(text: string): ToolApprovalRequest | null {
  if (!text) return null;
  
  const approvalMatch = text.match(/Propuesta creada: (APR-TGM-TOOL-[a-f0-9]+)/);
  if (!approvalMatch) return null;

  const draftMatch = text.match(/Borrador no ejecutado: (.*)/);
  const hintMatch = text.match(/Responde 'sí' para (.*)/);

  return {
    approvalId: approvalMatch[1],
    draft: draftMatch ? draftMatch[1].trim() : 'Comando desconocido',
    hint: hintMatch ? `Responde 'sí' para ${hintMatch[1].trim()}` : 'Requiere aprobación manual',
  };
}

/**
 * Get messages from OpenClaw API for a given session.
 */
export async function getMessagesFromOpenClaw(
  sessionKey: string
): Promise<Array<{ role: string; content: string }>> {
  try {
    const client = getOpenClawClient();
    if (!client.isConnected()) {
      await client.connect();
    }

    const result = await client.call<any>('sessions.history', {
      session_id: sessionKey,
      limit: 50,
    });

    const messages: Array<{ role: string; content: string }> = [];
    const history = Array.isArray(result) ? result : result.messages || [];

    for (const msg of history) {
      const role = msg.role || (msg.direction === 'outbound' ? 'assistant' : 'user');
      if (role === 'assistant') {
        const content = Array.isArray(msg.content)
          ? msg.content.find((c: any) => c.type === 'text')?.text
          : msg.content || msg.text;
        if (content && typeof content === 'string' && content.trim().length > 0) {
          messages.push({ role: 'assistant', content });
        }
      }
    }

    return messages;
  } catch (err) {
    console.error('[Planning Utils] Failed to get messages:', err);
    return [];
  }
}
