'use client';

import { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, RefreshCw, ShieldCheck, Trash2, X, XCircle } from 'lucide-react';

interface ApprovalRequest {
  approval_id: string;
  task_id: string;
  status: string;
  diff_summary: string;
  affected_targets: string[];
  step_id_expected: string;
  evidence_source_required: boolean;
  created_at: string;
}

interface ApprovalsResponse {
  status: string;
  approvals: ApprovalRequest[];
  pending_count: number;
  error?: string;
}

function formatCreatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value || 'sin fecha';
  }
  return date.toLocaleString('es-MX', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function OpenClawApprovalsButton() {
  const [open, setOpen] = useState(false);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadApprovals = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/openclaw/approvals', { cache: 'no-store' });
      const payload = (await response.json()) as ApprovalsResponse;
      if (!response.ok || payload.status !== 'ok') {
        throw new Error(payload.error || 'approval_list_failed');
      }
      setApprovals(Array.isArray(payload.approvals) ? payload.approvals : []);
      setPendingCount(Number(payload.pending_count || 0));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'approval_list_failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadApprovals();
    const timer = setInterval(loadApprovals, 30000);
    return () => clearInterval(timer);
  }, [loadApprovals]);

  const updateApproval = async (approvalId: string, status: 'approved' | 'rejected') => {
    try {
      setActionId(approvalId);
      const response = await fetch(`/api/openclaw/approvals/${encodeURIComponent(approvalId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload?.status !== 'ok') {
        throw new Error(payload?.error || 'approval_update_failed');
      }
      await loadApprovals();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'approval_update_failed');
    } finally {
      setActionId(null);
    }
  };

  const clearApprovals = async () => {
    try {
      setActionId('clear');
      const response = await fetch('/api/openclaw/approvals', { method: 'DELETE' });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload?.status !== 'ok') {
        throw new Error(payload?.error || 'approval_clear_failed');
      }
      await loadApprovals();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'approval_clear_failed');
    } finally {
      setActionId(null);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
          loadApprovals();
        }}
        className="relative min-h-11 min-w-11 p-2 hover:bg-mc-bg-tertiary rounded text-mc-text-secondary"
        title="Aprobaciones OpenClaw"
      >
        <ShieldCheck className="w-5 h-5" />
        {pendingCount > 0 && (
          <span className="absolute -right-1 -top-1 min-w-5 h-5 px-1 rounded bg-mc-accent-yellow text-mc-bg text-xs font-semibold flex items-center justify-center">
            {pendingCount > 99 ? '99+' : pendingCount}
          </span>
        )}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-start justify-center p-4 md:p-8">
          <div className="w-full max-w-4xl max-h-[88vh] overflow-hidden rounded border border-mc-border bg-mc-bg-secondary shadow-2xl">
            <div className="h-16 px-4 md:px-5 border-b border-mc-border flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <ShieldCheck className="w-5 h-5 text-mc-accent-cyan shrink-0" />
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold truncate">Aprobaciones OpenClaw</h2>
                  <p className="text-xs text-mc-text-secondary">{pendingCount} pendiente{pendingCount === 1 ? '' : 's'}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={loadApprovals}
                  disabled={loading}
                  className="min-h-10 min-w-10 p-2 rounded border border-mc-border hover:bg-mc-bg-tertiary text-mc-text-secondary disabled:opacity-50"
                  title="Actualizar"
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </button>
                {pendingCount > 0 && (
                  <button
                    type="button"
                    onClick={clearApprovals}
                    disabled={actionId !== null}
                    className="min-h-10 min-w-10 p-2 rounded border border-mc-accent-red/40 hover:bg-mc-accent-red/10 text-mc-accent-red disabled:opacity-50"
                    title="Rechazar todas"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="min-h-10 min-w-10 p-2 rounded hover:bg-mc-bg-tertiary text-mc-text-secondary"
                  title="Cerrar"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="p-4 md:p-5 overflow-y-auto max-h-[calc(88vh-4rem)] space-y-3">
              {error && (
                <div className="rounded border border-mc-accent-red/40 bg-mc-accent-red/10 px-3 py-2 text-sm text-mc-accent-red">
                  {error}
                </div>
              )}

              {approvals.length === 0 ? (
                <div className="rounded border border-mc-border bg-mc-bg px-4 py-8 text-center text-mc-text-secondary">
                  No hay aprobaciones pendientes.
                </div>
              ) : (
                approvals.map((approval) => (
                  <article key={approval.approval_id} className="rounded border border-mc-border bg-mc-bg p-4 space-y-3">
                    <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-mc-text">{approval.approval_id}</span>
                          <span className="text-xs uppercase text-mc-text-secondary border border-mc-border rounded px-2 py-0.5">
                            {approval.status}
                          </span>
                          {approval.evidence_source_required && (
                            <span className="text-xs text-mc-accent-yellow border border-mc-accent-yellow/40 rounded px-2 py-0.5">
                              evidencia requerida
                            </span>
                          )}
                        </div>
                        <div className="mt-1 text-xs text-mc-text-secondary">
                          tarea {approval.task_id} · {formatCreatedAt(approval.created_at)}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          onClick={() => updateApproval(approval.approval_id, 'approved')}
                          disabled={actionId !== null}
                          className="min-h-10 px-3 rounded bg-mc-accent-green/20 border border-mc-accent-green text-mc-accent-green hover:bg-mc-accent-green/30 disabled:opacity-50 flex items-center gap-2"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          Aprobar
                        </button>
                        <button
                          type="button"
                          onClick={() => updateApproval(approval.approval_id, 'rejected')}
                          disabled={actionId !== null}
                          className="min-h-10 px-3 rounded bg-mc-accent-red/10 border border-mc-accent-red/50 text-mc-accent-red hover:bg-mc-accent-red/20 disabled:opacity-50 flex items-center gap-2"
                        >
                          <XCircle className="w-4 h-4" />
                          Rechazar
                        </button>
                      </div>
                    </div>

                    <p className="text-sm text-mc-text-secondary leading-relaxed whitespace-pre-wrap break-words">
                      {approval.diff_summary || 'Sin resumen registrado.'}
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="rounded bg-mc-bg-tertiary border border-mc-border px-3 py-2">
                        <div className="uppercase text-mc-text-secondary mb-1">Step ID esperado</div>
                        <div className="font-mono text-mc-text break-words">{approval.step_id_expected || 'no declarado'}</div>
                      </div>
                      <div className="rounded bg-mc-bg-tertiary border border-mc-border px-3 py-2">
                        <div className="uppercase text-mc-text-secondary mb-1">Objetivos afectados</div>
                        <div className="font-mono text-mc-text break-words">
                          {approval.affected_targets?.length ? approval.affected_targets.join(', ') : 'sin objetivos'}
                        </div>
                      </div>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
