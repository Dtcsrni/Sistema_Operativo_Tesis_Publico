'use client';

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Check, Clock, Loader, MessageSquare } from 'lucide-react';
import { MentionInput } from '@/components/chat/MentionInput';
import type { TaskNote } from '@/lib/types';

interface TaskChatTabProps {
  taskId: string;
}

export function TaskChatTab({ taskId }: TaskChatTabProps) {
  const [notes, setNotes] = useState<TaskNote[]>([]);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [streamingContent, setStreamingContent] = useState('');
  const [streamType, setStreamType] = useState<'text' | 'thinking' | 'tool_use' | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const loadNotes = useCallback(async () => {
    try {
      const res = await fetch(`/api/tasks/${taskId}/chat`);
      if (res.ok) {
        const data: TaskNote[] = await res.json();
        setNotes(data);
      }
    } catch {
      // Silently fail — will retry on next poll
    }
  }, [taskId]);

  useEffect(() => {
    loadNotes();
    const interval = setInterval(loadNotes, 2000);
    return () => clearInterval(interval);
  }, [loadNotes]);

  // Mark as read when opening
  useEffect(() => {
    fetch(`/api/tasks/${taskId}/read`, { method: 'POST' }).catch(() => {});
  }, [taskId]);

  const latestUserMessage = useMemo(() => {
    return [...notes].reverse().find(note => note.role === 'user');
  }, [notes]);

  const assistantAfterLatestUser = useMemo(() => {
    if (!latestUserMessage) return false;
    const latestUserAt = new Date(latestUserMessage.created_at.endsWith('Z') ? latestUserMessage.created_at : latestUserMessage.created_at + 'Z').getTime();
    return notes.some(note =>
      note.role === 'assistant' &&
      new Date(note.created_at.endsWith('Z') ? note.created_at : note.created_at + 'Z').getTime() > latestUserAt
    );
  }, [latestUserMessage, notes]);

  // Derive "waiting" conservatively.
  // Do not leave a fake typing bubble up for minutes. After the first short
  // grace period, show a truthful delivery/capture state instead.
  const waiting = useMemo(() => {
    if (!latestUserMessage || assistantAfterLatestUser) return false;
    if (latestUserMessage.status === 'pending') return true;

    const age = Date.now() - new Date(latestUserMessage.created_at.endsWith('Z') ? latestUserMessage.created_at : latestUserMessage.created_at + 'Z').getTime();
    return latestUserMessage.status === 'delivered' && age < 15000;
  }, [latestUserMessage, assistantAfterLatestUser]);

  const awaitingCapturedReply = Boolean(
    latestUserMessage &&
    latestUserMessage.status === 'delivered' &&
    !assistantAfterLatestUser &&
    !waiting
  );

  // Real-time stream management
  useEffect(() => {
    if ((waiting || awaitingCapturedReply) && !assistantAfterLatestUser) {
      // Start timer
      if (!timerRef.current) {
        setElapsedSeconds(0);
        timerRef.current = setInterval(() => {
          setElapsedSeconds(s => s + 1);
        }, 1000);
      }

      // Start SSE
      if (!eventSourceRef.current) {
        const es = new EventSource(`/api/tasks/${taskId}/agent-stream`);
        eventSourceRef.current = es;

        es.onmessage = (event) => {
          try {
            if (event.data.startsWith(':')) return;
            const data = JSON.parse(event.data);
            if (data.type === 'agent_stream') {
              setStreamType(data.stream || 'text');
              setStreamingContent(prev => prev + (data.data || ''));
            } else if (data.type === 'message' && data.role === 'assistant') {
              // Message completed, notes poll will pick it up
              loadNotes();
            }
          } catch {}
        };
      }
    } else {
      // Cleanup
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setStreamingContent('');
      setStreamType(null);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, [taskId, waiting, awaitingCapturedReply, assistantAfterLatestUser, loadNotes]);

  // Format seconds to mm:ss
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Auto-scroll on new notes or waiting state change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [notes, waiting]);

  const handleSend = async () => {
    if (!message.trim() || sending) return;
    setError(null);
    setSending(true);

    try {
      const res = await fetch(`/api/tasks/${taskId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message.trim() }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: 'Failed to send' }));
        setError(data.error || 'Failed to send message');
        return;
      }

      setMessage('');
      await loadNotes();
      // Mark as read after sending
      fetch(`/api/tasks/${taskId}/read`, { method: 'POST' }).catch(() => {});
    } catch {
      setError('Network error — please try again');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full min-h-[400px]">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {notes.length === 0 && !waiting && (
          <div className="text-center py-12">
            <MessageSquare className="w-8 h-8 text-mc-text-secondary mx-auto mb-3 opacity-50" />
            <p className="text-mc-text-secondary text-sm">Aún no hay mensajes</p>
            <p className="text-mc-text-secondary/60 text-xs mt-1">
              Envía un mensaje al agente — será despachado automáticamente
            </p>
          </div>
        )}

        {notes.map(note => {
          const isAgent = note.role === 'assistant';
          return (
            <div key={note.id} className={isAgent ? 'mr-8' : 'ml-8'}>
              <div className={`border rounded-lg px-3 py-2 ${
                isAgent
                  ? 'bg-green-500/10 border-green-500/20'
                  : 'bg-blue-500/10 border-blue-500/20'
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-mc-text-secondary">
                    {isAgent ? 'Agente' : 'Tú'}
                  </span>
                  {!isAgent && note.status === 'pending' && (
                    <span className="flex items-center gap-1 text-xs text-amber-400">
                      <Loader className="w-3 h-3 animate-spin" />
                      Enviando
                    </span>
                  )}
                  {!isAgent && note.status === 'delivered' && (
                    <span className="flex items-center gap-1 text-xs text-green-400">
                      <Check className="w-3 h-3" />
                      Entregado
                    </span>
                  )}
                  <span className="ml-auto text-xs text-mc-text-secondary/50">
                    {new Date(note.created_at.endsWith('Z') ? note.created_at : note.created_at + 'Z').toLocaleTimeString()}
                  </span>
                </div>
                <div className="text-sm text-mc-text whitespace-pre-wrap">{note.content}</div>
              </div>
            </div>
          );
        })}

        {/* Thinking bubble — enhanced with live streaming and timer */}
        {(waiting || awaitingCapturedReply) && (
          <div className="mr-8 animate-in fade-in slide-in-from-left-2 duration-300">
            <div className={`
              ${streamType === 'thinking' ? 'bg-purple-500/10 border-purple-500/20' : 'bg-green-500/10 border-green-500/20'}
              border rounded-lg px-3 py-2 flex flex-col gap-1 max-w-[90%]
            `}>
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-mc-text-secondary">
                  {streamType === 'thinking' ? 'Razonando' : 'Agente'}
                </span>
                <div className="flex gap-1 items-center">
                  <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                  <span className="text-[10px] font-mono text-mc-text-secondary/60 tabular-nums">
                    {formatTime(elapsedSeconds)}
                  </span>
                </div>
              </div>
              
              {streamingContent ? (
                <div className={`text-sm ${streamType === 'thinking' ? 'text-purple-200/70 font-mono italic text-xs' : 'text-mc-text'} whitespace-pre-wrap break-words line-clamp-6`}>
                  {streamingContent}
                </div>
              ) : (
                <div className="flex gap-1 py-1">
                  <span className="w-1 h-1 bg-mc-text-secondary/40 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1 h-1 bg-mc-text-secondary/40 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1 h-1 bg-mc-text-secondary/40 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              )}
            </div>
          </div>
        )}

        {awaitingCapturedReply && (
          <div className="mr-8">
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2 text-xs text-amber-200 flex items-start gap-2">
              <Clock className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <div>
                <div className="font-medium">Entregado — esperando respuesta capturada</div>
                <div className="text-amber-200/75 mt-0.5">
                  El agente recibió este mensaje. Si el agente completa la tarea o la entrega sin una respuesta de chat normal, la Grabadora de Vuelo mostrará esa señal en lugar de dejar esto como escritura simulada.
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input area — now with @mention support */}
      <div className="border-t border-mc-border p-3 space-y-2">
        {error && (
          <div className="text-xs text-red-400 px-1">{error}</div>
        )}

        <MentionInput
          taskId={taskId}
          value={message}
          onChange={setMessage}
          onSend={handleSend}
          sending={sending}
          placeholder="Mensaje para el agente... (@ para mencionar, / para comandos)"
          onSlashCommand={(cmd) => {
            window.dispatchEvent(new CustomEvent('commandpalette:open', { detail: { filter: cmd, taskId } }));
          }}
        />
      </div>
    </div>
  );
}
