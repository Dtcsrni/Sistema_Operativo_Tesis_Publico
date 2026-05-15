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
