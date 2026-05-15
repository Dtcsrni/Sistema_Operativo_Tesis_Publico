'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Lock, AlertCircle, Loader2, Terminal, ShieldCheck, Zap } from 'lucide-react';
import { extractApprovalRequest, ToolApprovalRequest } from '@/lib/planning-logic';

interface PlanningOption {
  id: string;
  label: string;
}

interface PlanningQuestion {
  question: string;
  options: PlanningOption[];
}

interface PlanningMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface PlanningState {
  taskId: string;
  sessionKey?: string;
  messages: PlanningMessage[];
  currentQuestion?: PlanningQuestion;
  isComplete: boolean;
  dispatchError?: string;
  spec?: {
    title: string;
    summary: string;
    deliverables: string[];
    success_criteria: string[];
    constraints: Record<string, unknown>;
  };
  agents?: Array<{
    name: string;
    role: string;
    avatar_emoji: string;
    soul_md: string;
    instructions: string;
  }>;
  isStarted: boolean;
}

interface PlanningApiResponse extends PlanningState {
  stalePlanning?: boolean;
  hasUpdates?: boolean;
}

interface PlanningTabProps {
  taskId: string;
  onSpecLocked?: () => void;
}

/**
 * Component to show and approve pending tool calls.
 */
function ToolApprovalCard({ 
  approval, 
  onApprove, 
  loading 
}: { 
  approval: ToolApprovalRequest, 
  onApprove: () => Promise<void>, 
  loading: boolean 
}) {
  return (
    <div className="bg-mc-bg-secondary border border-mc-accent/30 rounded-xl overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-300">
      <div className="bg-mc-accent/10 px-4 py-3 flex items-center justify-between border-b border-mc-accent/20">
        <div className="flex items-center gap-2 text-mc-accent">
          <ShieldCheck className="w-5 h-5" />
          <span className="font-bold text-xs tracking-widest uppercase">Autorización Requerida</span>
        </div>
        <div className="flex items-center gap-1.5 text-mc-text-secondary text-[10px] font-mono">
          <span className="w-2 h-2 rounded-full bg-mc-accent animate-pulse" />
          {approval.approvalId}
        </div>
      </div>
      
      <div className="p-6">
        <h3 className="text-xl font-semibold mb-4 text-white">
          Validación de Herramienta en Modo Seguro
        </h3>
        
        <p className="text-mc-text-secondary text-sm mb-6 leading-relaxed">
          El orquestador ha solicitado ejecutar un comando que requiere supervisión humana directa según la política de seguridad actual.
        </p>

        <div className="bg-mc-bg-tertiary rounded-lg p-4 mb-6 border border-mc-border font-mono text-xs">
          <div className="flex items-center gap-2 mb-2 text-mc-text-secondary opacity-60">
            <Terminal className="w-3.5 h-3.5" />
            <span>COMANDO PROPUESTO</span>
          </div>
          <code className="text-mc-accent break-all">
            {approval.draft}
          </code>
        </div>

        <button
          onClick={() => onApprove()}
          disabled={loading}
          className="w-full group relative flex items-center justify-center gap-3 px-6 py-4 bg-mc-accent text-mc-bg rounded-lg font-bold transition-all hover:bg-mc-accent/90 disabled:opacity-50 overflow-hidden"
        >
          {loading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <>
              <Zap className="w-5 h-5 fill-current" />
              <span>APROBAR Y EJECUTAR</span>
            </>
          )}
        </button>
        
        <p className="mt-4 text-center text-[10px] text-mc-text-secondary italic">
          Esta acción quedará registrada en el Ledger de Gobernanza con tu firma digital.
        </p>
      </div>
    </div>
  );
}

export function PlanningTab({ taskId, onSpecLocked }: PlanningTabProps) {
  const [state, setState] = useState<PlanningState | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [canceling, setCanceling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [otherText, setOtherText] = useState('');
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [retryingDispatch, setRetryingDispatch] = useState(false);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [stalePlanning, setStalePlanning] = useState(false);
  const [forceCompleting, setForceCompleting] = useState(false);
  const [noNewMessageCount, setNoNewMessageCount] = useState(0);
  const [pendingApproval, setPendingApproval] = useState<ToolApprovalRequest | null>(null);

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollingWarningTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollingHardTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isPollingRef = useRef(false);
  const currentQuestionRef = useRef<string | undefined>(undefined);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    if (pollingWarningTimeoutRef.current) {
      clearTimeout(pollingWarningTimeoutRef.current);
      pollingWarningTimeoutRef.current = null;
    }
    if (pollingHardTimeoutRef.current) {
      clearTimeout(pollingHardTimeoutRef.current);
      pollingHardTimeoutRef.current = null;
    }
    setIsWaitingForResponse(false);
  }, []);

  const pollForUpdates = useCallback(async () => {
    if (isPollingRef.current) return;
    isPollingRef.current = true;

    try {
      const res = await fetch(`/api/tasks/${taskId}/planning/poll`);
      if (res.ok) {
        const data: PlanningApiResponse = await res.json();

        if (data.stalePlanning) setStalePlanning(true);

        if (!data.hasUpdates && isWaitingForResponse) {
          setNoNewMessageCount(prev => {
            const next = prev + 1;
            if (next >= 15) setStalePlanning(true);
            return next;
          });
        }

        if (data.hasUpdates) {
          setError(null);
          setStalePlanning(false);
          setNoNewMessageCount(0);

          const freshRes = await fetch(`/api/tasks/${taskId}/planning`);
          if (freshRes.ok) {
            const freshData: PlanningState = await freshRes.json();
            setState(freshData);
            
            const assistantMessages = freshData.messages.filter((m: PlanningMessage) => m.role === 'assistant');
            if (assistantMessages.length > 0) {
              const lastMsg = assistantMessages[assistantMessages.length - 1].content;
              setPendingApproval(extractApprovalRequest(lastMsg));
            }
          }

          if (data.currentQuestion) {
            setIsSubmittingAnswer(false);
            setSubmitting(false);
          }

          if (data.isComplete && onSpecLocked) onSpecLocked();

          if (data.currentQuestion || data.isComplete || data.dispatchError) {
            setIsWaitingForResponse(false);
            stopPolling();
          }
        }
      }
    } catch (err) {
      console.error('Failed to poll:', err);
    } finally {
      isPollingRef.current = false;
    }
  }, [taskId, onSpecLocked, stopPolling, isWaitingForResponse]);

  const startPolling = useCallback(() => {
    stopPolling();
    setIsWaitingForResponse(true);
    pollingIntervalRef.current = setInterval(pollForUpdates, 2000);
    pollingWarningTimeoutRef.current = setTimeout(() => setError('Aún procesando...'), 90000);
    pollingHardTimeoutRef.current = setTimeout(() => stopPolling(), 300000);
  }, [pollForUpdates, stopPolling]);

  const loadState = useCallback(async () => {
    try {
      const res = await fetch(`/api/tasks/${taskId}/planning`);
      if (res.ok) {
        const data: PlanningState = await res.json();
        setState(data);
        const assistantMessages = data.messages.filter((m: PlanningMessage) => m.role === 'assistant');
        if (assistantMessages.length > 0) {
          setPendingApproval(extractApprovalRequest(assistantMessages[assistantMessages.length - 1].content));
        }
      }
    } catch (err) {
      setError('Error al cargar estado');
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    loadState();
    return () => stopPolling();
  }, [loadState, stopPolling]);

  useEffect(() => {
    if (state?.isStarted && !state.isComplete && !state.currentQuestion && !isWaitingForResponse) {
      startPolling();
    }
  }, [state, isWaitingForResponse, startPolling]);

  const startPlanning = async () => {
    setStarting(true);
    try {
      const res = await fetch(`/api/tasks/${taskId}/planning`, { method: 'POST' });
      if (res.ok) {
        await loadState();
        startPolling();
      }
    } catch (err) {
      setError('Error al iniciar');
    } finally {
      setStarting(false);
    }
  };

  const submitAnswer = async (answer: string, other?: string) => {
    setSubmitting(true);
    try {
      const res = await fetch(`/api/tasks/${taskId}/planning/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer, otherText: other }),
      });
      if (res.ok) startPolling();
    } catch (err) {
      setError('Error al enviar respuesta');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>;

  if (state?.isComplete && state?.spec) {
    return (
      <div className="p-6 space-y-4">
        <div className="flex items-center gap-2 text-green-400 font-bold"><ShieldCheck /> PLANIFICACIÓN COMPLETADA</div>
        <div className="bg-mc-bg-secondary p-4 rounded-lg border border-mc-border">
          <h3 className="text-xl font-bold mb-2">{state.spec.title}</h3>
          <p className="text-mc-text-secondary">{state.spec.summary}</p>
        </div>
      </div>
    );
  }

  if (!state?.isStarted) {
    return (
      <div className="p-12 flex flex-col items-center gap-6">
        <h2 className="text-2xl font-bold">Configurar Misión</h2>
        <button onClick={startPlanning} disabled={starting} className="px-8 py-4 bg-mc-accent text-mc-bg rounded-xl font-bold text-lg hover:scale-105 transition-transform">
          {starting ? 'Iniciando...' : '🚀 INICIAR PLANIFICACIÓN'}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-mc-bg">
      <div className="flex-1 overflow-y-auto p-6">
        {pendingApproval ? (
          <div className="max-w-xl mx-auto">
            <ToolApprovalCard 
              approval={pendingApproval}
              loading={submitting}
              onApprove={async () => {
                setSubmitting(true);
                try {
                  const res = await fetch(`/api/tasks/${taskId}/planning/answer`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ answer: 'sí' }),
                  });
                  if (res.ok) {
                    setPendingApproval(null);
                    startPolling();
                  }
                } finally {
                  setSubmitting(false);
                }
              }}
            />
          </div>
        ) : state?.currentQuestion ? (
          <div className="max-w-xl mx-auto space-y-6">
            <h3 className="text-2xl font-bold">{state.currentQuestion.question}</h3>
            <div className="grid gap-3">
              {state.currentQuestion.options.map(opt => (
                <button 
                  key={opt.id}
                  onClick={() => submitAnswer(opt.label)}
                  disabled={submitting}
                  className="p-4 bg-mc-bg-secondary border border-mc-border rounded-xl text-left hover:border-mc-accent hover:bg-mc-accent/5 transition-all"
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-mc-text-secondary">
            <Loader2 className="animate-spin w-8 h-8 text-mc-accent" />
            <p className="animate-pulse">Sincronizando con el orquestador...</p>
          </div>
        )}
      </div>
      
      {error && (
        <div className="m-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      )}
    </div>
  );
}
