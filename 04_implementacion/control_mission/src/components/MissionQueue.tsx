'use client';

import { useEffect, useMemo, useState } from 'react';
import { Plus, ChevronRight, GripVertical, ArrowRightLeft, AlertTriangle, MessageSquare } from 'lucide-react';
import { useMissionControl } from '@/lib/store';
import { triggerAutoDispatch, shouldTriggerAutoDispatch } from '@/lib/auto-dispatch';
import { getConfig } from '@/lib/config';
import { useUnreadCounts } from '@/hooks/useUnreadCounts';
import type { Task, TaskStatus } from '@/lib/types';
import { TaskModal } from './TaskModal';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';

interface MissionQueueProps {
  workspaceId?: string;
  mobileMode?: boolean;
  isPortrait?: boolean;
}

const COLUMNS: { id: TaskStatus; label: string; color: string }[] = [
  { id: 'planning', label: '📋 Planificación', color: 'border-t-mc-accent-purple' },
  { id: 'inbox', label: 'Bandeja de Entrada', color: 'border-t-mc-accent-pink' },
  { id: 'assigned', label: 'Asignado', color: 'border-t-mc-accent-yellow' },
  { id: 'in_progress', label: 'En Progreso', color: 'border-t-mc-accent' },
  { id: 'convoy_active', label: '🚚 Convoy', color: 'border-t-cyan-400' },
  { id: 'testing', label: 'Pruebas', color: 'border-t-mc-accent-cyan' },
  { id: 'review', label: 'Revisión', color: 'border-t-mc-accent-purple' },
  { id: 'verification', label: 'Verificación', color: 'border-t-orange-500' },
  { id: 'done', label: 'Terminado', color: 'border-t-mc-accent-green' },
];

export function MissionQueue({ workspaceId, mobileMode = false, isPortrait = true }: MissionQueueProps) {
  const { tasks, updateTaskStatus, addEvent } = useMissionControl();
  const [compactEmptyColumns, setCompactEmptyColumns] = useState(true);
  const unreadCounts = useUnreadCounts();

  const taskSerials = useMemo(() => {
    const orderedTasks = [...tasks].sort((left, right) => {
      const leftTime = new Date(left.created_at).getTime();
      const rightTime = new Date(right.created_at).getTime();
      if (leftTime !== rightTime) return leftTime - rightTime;
      return left.id.localeCompare(right.id);
    });

    return new Map(orderedTasks.map((task, index) => [task.id, index + 1]));
  }, [tasks]);

  useEffect(() => {
    const cfg = getConfig();
    setCompactEmptyColumns(cfg.kanbanCompactEmptyColumns ?? true);
  }, []);

  const getDesktopColumnWidth = (taskCount: number): string => {
    if (!compactEmptyColumns) return '280px';
    if (taskCount === 0) return 'fit-content';
    // Slightly grow busy columns while keeping a sane cap
    const widthPx = Math.min(380, 250 + taskCount * 14);
    return `${widthPx}px`;
  };
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [draggedTask, setDraggedTask] = useState<Task | null>(null);
  const [mobileStatus, setMobileStatus] = useState<TaskStatus>('planning');
  const [statusMoveTask, setStatusMoveTask] = useState<Task | null>(null);
  const [pendingMove, setPendingMove] = useState<{ task: Task; targetStatus: TaskStatus } | null>(null);

  const getTasksByStatus = (status: TaskStatus) => tasks.filter((task) => task.status === status);

  // Active pipeline states where manual moves are dangerous
  const ACTIVE_PIPELINE_STATES: TaskStatus[] = ['assigned', 'in_progress', 'convoy_active', 'testing', 'review', 'verification'];

  const getPipelineWarning = (task: Task, targetStatus: TaskStatus): string | null => {
    if (!ACTIVE_PIPELINE_STATES.includes(task.status)) return null;
    // Moving to the same status or to done is less dangerous
    if (task.status === targetStatus) return null;

    const stateLabels: Record<string, string> = {
      assigned: 'en cola para despacho',
      in_progress: 'siendo procesado por un agente',
      convoy_active: 'ejecutándose como convoy',
      testing: 'en fase de pruebas por un agente',
      review: 'en la cola de revisión',
      verification: 'en fase de verificación por un agente',
    };

    const current = stateLabels[task.status] || task.status;
    return `Esta tarea está actualmente ${current}. Moverla manualmente interrumpirá el flujo de automatización y podría causar que el agente pierda el contexto. ¿Estás seguro de que deseas anularlo?`;
  };

  const attemptMove = async (task: Task, targetStatus: TaskStatus) => {
    const warning = getPipelineWarning(task, targetStatus);
    if (warning) {
      setPendingMove({ task, targetStatus });
      return;
    }
    await updateTaskStatusWithPersist(task, targetStatus);
  };

  const confirmPendingMove = async () => {
    if (!pendingMove) return;
    const { task, targetStatus } = pendingMove;
    setPendingMove(null);
    setStatusMoveTask(null);
    await updateTaskStatusWithPersist(task, targetStatus);
  };

  const updateTaskStatusWithPersist = async (task: Task, targetStatus: TaskStatus) => {
    if (task.status === targetStatus) return;

    updateTaskStatus(task.id, targetStatus);

    try {
      const res = await fetch(`/api/tasks/${task.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: targetStatus }),
      });

      if (res.ok) {
        addEvent({
          id: task.id + '-' + Date.now(),
          type: targetStatus === 'done' ? 'task_completed' : 'task_status_changed',
          task_id: task.id,
          message: `Tarea "${task.title}" movida a ${targetStatus}`,
          created_at: new Date().toISOString(),
        });

        if (shouldTriggerAutoDispatch(task.status, targetStatus, task.assigned_agent_id)) {
          const result = await triggerAutoDispatch({
            taskId: task.id,
            taskTitle: task.title,
            agentId: task.assigned_agent_id,
            agentName: task.assigned_agent?.name || 'Unknown Agent',
            workspaceId: task.workspace_id,
          });

          if (!result.success) {
            console.error('Auto-dispatch failed:', result.error);
          }
        }
      }
    } catch (error) {
      console.error('Failed to update task status:', error);
      updateTaskStatus(task.id, task.status);
    }
  };

  const handleDragStart = (e: React.DragEvent, task: Task) => {
    if (mobileMode) return;
    setDraggedTask(task);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    if (mobileMode) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e: React.DragEvent, targetStatus: TaskStatus) => {
    if (mobileMode) return;
    e.preventDefault();
    if (!draggedTask || draggedTask.status === targetStatus) {
      setDraggedTask(null);
      return;
    }

    await attemptMove(draggedTask, targetStatus);
    setDraggedTask(null);
  };

  const mobileTasks = getTasksByStatus(mobileStatus);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="p-3 border-b border-mc-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ChevronRight className="w-4 h-4 text-mc-text-secondary" />
          <span className="text-sm font-medium uppercase tracking-wider">Cola de Misiones</span>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 min-h-11 bg-mc-accent-pink text-mc-bg rounded text-sm font-medium hover:bg-mc-accent-pink/90"
        >
          <Plus className="w-4 h-4" />
          Nueva Tarea
        </button>
      </div>

      {!mobileMode ? (
        <div className="mission-queue-scroll-x flex-1 flex gap-3 p-3 overflow-x-auto">
          {COLUMNS.map((column) => {
            const columnTasks = getTasksByStatus(column.id);
            const hasTasks = columnTasks.length > 0;
            return (
              <div
                key={column.id}
                style={{ width: getDesktopColumnWidth(columnTasks.length) }}
                className={`flex-none ${compactEmptyColumns ? (hasTasks ? 'min-w-[240px]' : 'min-w-[110px] max-w-[180px]') : 'min-w-[250px] max-w-[320px]'} flex flex-col bg-mc-bg rounded-lg border border-mc-border/50 border-t-2 transition-[width] duration-200 ${column.color}`}
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, column.id)}
              >
                <div className="p-2 border-b border-mc-border flex items-center justify-between gap-2">
                  <span className="text-xs font-medium uppercase text-mc-text-secondary whitespace-nowrap">{column.label}</span>
                  <span className="text-xs bg-mc-bg-tertiary px-2 py-0.5 rounded text-mc-text-secondary">{columnTasks.length}</span>
                </div>

                <div className={`flex-1 overflow-y-auto p-2 ${hasTasks ? 'space-y-2' : ''}`}>
                  {columnTasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      serialNumber={taskSerials.get(task.id) || 0}
                      onDragStart={handleDragStart}
                      onClick={() => setEditingTask(task)}
                      onMoveStatus={() => setStatusMoveTask(task)}
                      isDragging={draggedTask?.id === task.id}
                      mobileMode={false}
                      portraitMode={false}
                      unreadCount={unreadCounts[task.id] || 0}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className={`flex-1 overflow-y-auto ${isPortrait ? 'p-3 pb-[calc(1rem+env(safe-area-inset-bottom))]' : 'p-2.5 pb-[calc(0.75rem+env(safe-area-inset-bottom))]'}`}>
          <div className={`flex gap-2 overflow-x-auto ${isPortrait ? 'pb-3' : 'pb-2'}`}>
            {COLUMNS.map((column) => {
              const count = getTasksByStatus(column.id).length;
              const selected = mobileStatus === column.id;
              return (
                <button
                  key={column.id}
                  onClick={() => setMobileStatus(column.id)}
                  className={`min-h-11 px-4 rounded-full border whitespace-nowrap ${isPortrait ? 'text-sm' : 'text-xs'} ${
                    selected
                      ? 'bg-mc-accent text-mc-bg border-mc-accent font-medium'
                      : 'bg-mc-bg-secondary border-mc-border text-mc-text-secondary'
                  }`}
                >
                  {column.label} ({count})
                </button>
              );
            })}
          </div>

          <div className={`min-w-0 ${isPortrait ? 'space-y-3' : 'space-y-2'}`}>
            {mobileTasks.length === 0 ? (
              <div className="text-sm text-mc-text-secondary bg-mc-bg-secondary border border-mc-border rounded-lg p-4">
                No hay tareas en este estado.
              </div>
            ) : (
              mobileTasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  serialNumber={taskSerials.get(task.id) || 0}
                  onDragStart={handleDragStart}
                  onClick={() => setEditingTask(task)}
                  onMoveStatus={() => setStatusMoveTask(task)}
                  isDragging={false}
                  mobileMode
                  portraitMode={isPortrait}
                  unreadCount={unreadCounts[task.id] || 0}
                />
              ))
            )}
          </div>
        </div>
      )}

      {showCreateModal && <TaskModal onClose={() => setShowCreateModal(false)} workspaceId={workspaceId} />}
      {editingTask && <TaskModal task={editingTask} onClose={() => setEditingTask(null)} workspaceId={workspaceId} />}

      {mobileMode && statusMoveTask && (
        <div className="fixed inset-0 z-50 bg-black/60 p-4 flex items-end sm:items-center sm:justify-center" onClick={() => setStatusMoveTask(null)}>
          <div
            className="w-full sm:max-w-md bg-mc-bg-secondary border border-mc-border rounded-t-xl sm:rounded-xl p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-sm text-mc-text-secondary mb-2">Mover tarea</div>
            <div className="font-medium mb-4 line-clamp-2">{statusMoveTask.title}</div>
            <div className="space-y-2 max-h-[50vh] overflow-y-auto">
              {COLUMNS.map((column) => (
                <button
                  key={column.id}
                  onClick={async () => {
                    await attemptMove(statusMoveTask, column.id);
                    if (!getPipelineWarning(statusMoveTask, column.id)) {
                      setStatusMoveTask(null);
                    }
                  }}
                  disabled={statusMoveTask.status === column.id}
                  className="w-full min-h-11 px-4 rounded-lg border border-mc-border bg-mc-bg text-left text-sm disabled:opacity-40"
                >
                  {column.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Pipeline override warning dialog */}
      {pendingMove && (
        <div className="fixed inset-0 z-[60] bg-black/60 p-4 flex items-center justify-center" onClick={() => setPendingMove(null)}>
          <div
            className="w-full max-w-md bg-mc-bg-secondary border border-amber-500/30 rounded-xl p-5 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-amber-500/10">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h3 className="font-semibold text-mc-text">¿Anular automatización?</h3>
                <p className="text-sm text-mc-text-secondary mt-1">
                  {getPipelineWarning(pendingMove.task, pendingMove.targetStatus)}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 p-3 bg-mc-bg rounded-lg border border-mc-border text-sm">
              <span className="text-mc-text-secondary">Moviendo:</span>
              <span className="font-medium text-mc-text truncate">{pendingMove.task.title}</span>
              <span className="text-mc-text-secondary mx-1">&rarr;</span>
              <span className="font-medium text-mc-text">{COLUMNS.find(c => c.id === pendingMove.targetStatus)?.label || pendingMove.targetStatus}</span>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setPendingMove(null)}
                className="min-h-11 px-4 rounded-lg text-sm text-mc-text-secondary hover:text-mc-text hover:bg-mc-bg-tertiary"
              >
                Cancelar
              </button>
              <button
                onClick={confirmPendingMove}
                className="min-h-11 px-4 rounded-lg text-sm font-medium bg-amber-500 text-black hover:bg-amber-400"
              >
                Anular y Mover
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ModelExecutionBadge({ task, portraitMode }: { task: Task; portraitMode: boolean }) {
  const [flightSummary, setFlightSummary] = useState<any | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await fetch(`/api/tasks/${task.id}/flight-recorder`);
        if (!res.ok) return;
        const data = await res.json();
        if (mounted && data?.summary) setFlightSummary(data.summary);
      } catch {
        // Best-effort badge only.
      }
    })();
    return () => { mounted = false; };
  }, [task.id, task.status, task.updated_at, task.assigned_agent_id]);

  const evidence = flightSummary?.execution_evidence;
  const state = evidence?.model_state || 'no_model';
  const spacing = portraitMode ? 'mb-2' : 'mb-1.5';

  if (state === 'no_model') {
    return (
      <div className={`flex items-center gap-2 ${spacing}`}>
        <span className="text-[10px] px-1.5 py-0.5 bg-mc-bg-tertiary rounded border border-mc-border/20 text-mc-text-secondary">Sin modelo</span>
      </div>
    );
  }

  if (state === 'awaiting_approval') {
    return (
      <div className={`flex items-center gap-2 ${spacing}`}>
        <span className="text-[10px] px-1.5 py-0.5 bg-amber-500/10 rounded border border-amber-500/30 text-amber-300">Esperando aprobación</span>
      </div>
    );
  }

  if (state === 'awaiting_model') {
    return (
      <div className={`flex items-center gap-2 ${spacing}`}>
        <span className="text-[10px] px-1.5 py-0.5 bg-red-500/10 rounded border border-red-500/30 text-red-300">Sin modelo disponible</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${spacing}`}>
      <span className="text-[10px] px-1.5 py-0.5 bg-green-500/10 rounded border border-green-500/30 text-green-300">Ejecutando modelo{evidence?.model ? `: ${String(evidence.model).slice(0, 24)}` : ''}</span>
    </div>
  );
}

function ActiveTaskStatusBadge({ task, portraitMode }: { task: Task; portraitMode: boolean }) {
  const [retrying, setRetrying] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const updatedAt = new Date(task.updated_at).getTime();
  const staleMs = Date.now() - updatedAt;
  const staleThresholdMinutes = task.status === 'assigned' ? 2 : 15;
  const isStale = staleMs > staleThresholdMinutes * 60 * 1000;

  const handleRetryDispatch = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Don't open the task modal
    setRetrying(true);
    setActionError(null);
    try {
      const endpoint = task.status === 'assigned'
        ? `/api/tasks/${task.id}/dispatch`
        : task.assigned_agent_id
          ? `/api/agents/${task.assigned_agent_id}/health/nudge`
          : null;

      if (!endpoint) {
        setActionError('No se encontró agente asignado para reactivar la tarea.');
        return;
      }

      const res = await fetch(endpoint, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        console.error('Retry dispatch failed:', data.error);
        setActionError(typeof data.error === 'string' ? data.error : 'No se pudo reactivar la tarea.');
      }
    } catch (err) {
      console.error('Retry dispatch error:', err);
      setActionError('Error de red al intentar reactivar la tarea.');
    } finally {
      setRetrying(false);
    }
  };

  if (isStale) {
    const staleMinutes = Math.floor(staleMs / 60000);
    const title = task.status === 'assigned'
      ? `Atascado en asignado por ${staleMinutes}m`
      : `En progreso sin avance por ${staleMinutes}m`;
    const actionLabel = task.status === 'assigned' ? '↻ Reintentar despacho' : '↻ Reanudar trabajo';
    return (
      <div className={`${portraitMode ? 'mb-3 py-2 px-3' : 'mb-2 py-1.5 px-2.5'} bg-amber-500/10 rounded-md border border-amber-500/30`}>
        <div className="flex items-center gap-2 mb-1.5">
          <div className="w-2 h-2 bg-amber-400 rounded-full flex-shrink-0" />
          <span className="text-xs text-amber-200">{title}</span>
        </div>
        <div className="text-[11px] text-amber-300/90 mb-1.5">
          Última señal real: {formatDistanceToNow(new Date(task.updated_at), { addSuffix: true, locale: es })}
        </div>
        <button
          onClick={handleRetryDispatch}
          disabled={retrying}
          className="text-[11px] px-2 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 rounded border border-amber-500/30 disabled:opacity-50"
        >
          {retrying ? 'Despachando...' : actionLabel}
        </button>
        {actionError && (
          <div className="text-[11px] text-red-300 mt-1.5">{actionError}</div>
        )}
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${portraitMode ? 'mb-3 py-2 px-3' : 'mb-2 py-1.5 px-2.5'} bg-yellow-500/10 rounded-md border border-yellow-500/30`}>
      <div className="w-2 h-2 bg-yellow-400 rounded-full flex-shrink-0" />
      <div className="min-w-0">
        <div className="text-xs text-yellow-200">
          {task.status === 'assigned'
            ? 'Asignado y validando — el inicio automático lo moverá a En Progreso.'
            : 'En progreso y registrando señales — el flujo seguirá mientras haya actividad.'}
        </div>
        <div className="text-[11px] text-yellow-300/80 mt-0.5">
          Última señal real: {formatDistanceToNow(new Date(task.updated_at), { addSuffix: true, locale: es })}
        </div>
      </div>
    </div>
  );
}

interface TaskCardProps {
  task: Task;
  serialNumber: number;
  onDragStart: (e: React.DragEvent, task: Task) => void;
  onClick: () => void;
  onMoveStatus: () => void;
  isDragging: boolean;
  mobileMode: boolean;
  portraitMode?: boolean;
  unreadCount?: number;
}

function TaskCard({ task, serialNumber, onDragStart, onClick, onMoveStatus, isDragging, mobileMode, portraitMode = true, unreadCount = 0 }: TaskCardProps) {
  const priorityStyles = {
    low: 'text-mc-text-secondary',
    normal: 'text-mc-accent',
    high: 'text-mc-accent-yellow',
    urgent: 'text-mc-accent-red',
  };

  const priorityDots = {
    low: 'bg-mc-text-secondary/40',
    normal: 'bg-mc-accent',
    high: 'bg-mc-accent-yellow',
    urgent: 'bg-mc-accent-red',
  };

  const isPlanning = task.status === 'planning';
  const isConvoyActive = task.status === 'convoy_active';
  const isSubtask = !!task.is_subtask;
  const isAssigned = task.status === 'assigned';
  const dispatchError = task.planning_dispatch_error;

  return (
    <div
      draggable={!mobileMode}
      onDragStart={(e) => onDragStart(e, task)}
      onClick={onClick}
      className={`group bg-mc-bg-secondary border rounded-lg cursor-pointer transition-all hover:shadow-lg hover:shadow-black/20 ${
        isDragging ? 'opacity-50 scale-95' : ''
      } ${isPlanning ? 'border-purple-500/40 hover:border-purple-500' : 'border-mc-border/50 hover:border-mc-accent/40'}`}
    >
      {!mobileMode && (
        <div className="flex items-center justify-center py-1.5 border-b border-mc-border/30 opacity-0 group-hover:opacity-100 transition-opacity">
          <GripVertical className="w-4 h-4 text-mc-text-secondary/50 cursor-grab" />
        </div>
      )}

      <div className={portraitMode ? 'p-4' : 'p-3'}>
        <div className="flex items-start justify-between gap-1.5">
          <div className="min-w-0 flex-1">
            <div className={`inline-flex items-center gap-1 rounded-full border border-mc-border/70 bg-mc-bg-tertiary px-2 py-0.5 text-[10px] font-semibold tracking-[0.18em] text-mc-text-secondary ${portraitMode ? 'mb-2' : 'mb-1.5'}`}>
              <span>SERIE</span>
              <span className="text-mc-accent">#{String(serialNumber).padStart(3, '0')}</span>
            </div>
            <h4 className={`font-medium leading-snug line-clamp-2 ${portraitMode ? 'text-sm mb-3' : 'text-xs mb-2'}`}>{task.title}</h4>
          </div>
          {unreadCount > 0 && (
            <span className="flex-shrink-0 flex items-center gap-1 px-1.5 py-0.5 bg-mc-accent/15 text-mc-accent rounded text-[10px] font-medium" title={`${unreadCount} mensaje${unreadCount !== 1 ? 's' : ''} sin leer`}>
              <MessageSquare className="w-2.5 h-2.5" />
              {unreadCount}
            </span>
          )}
        </div>

        {isPlanning && (
          <div className={`flex items-center gap-2 ${portraitMode ? 'mb-3 py-2 px-3' : 'mb-2 py-1.5 px-2.5'} bg-purple-500/10 rounded-md border border-purple-500/20`}>
            <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse flex-shrink-0" />
            <span className="text-xs text-purple-400 font-medium">Continuar planificación</span>
          </div>
        )}

        {isConvoyActive && (
          <div className={`flex items-center gap-2 ${portraitMode ? 'mb-3 py-2 px-3' : 'mb-2 py-1.5 px-2.5'} bg-cyan-500/10 rounded-md border border-cyan-500/20`}>
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse flex-shrink-0" />
            <span className="text-xs text-cyan-300 font-medium">Convoy activo — sub-tareas ejecutándose</span>
          </div>
        )}

        {isSubtask && (
          <div className={`flex items-center gap-1 ${portraitMode ? 'mb-2' : 'mb-1.5'}`}>
            <span className="text-[10px] px-1.5 py-0.5 bg-cyan-500/15 text-cyan-400 rounded border border-cyan-500/20">SUB-TAREA</span>
          </div>
        )}

        {isAssigned && dispatchError && (
          <div className={`flex items-start gap-2 ${portraitMode ? 'mb-3 py-2 px-3' : 'mb-2 py-1.5 px-2.5'} bg-red-500/10 rounded-md border border-red-500/30`}>
            <div className="w-2 h-2 bg-red-400 rounded-full mt-1 flex-shrink-0" />
            <span className="text-xs text-red-300">Asignado, pero bloqueado: {dispatchError}</span>
          </div>
        )}

        {(isAssigned || task.status === 'in_progress') && !dispatchError && (
          <ActiveTaskStatusBadge task={task} portraitMode={portraitMode} />
        )}
        {(isAssigned || task.status === 'in_progress') && (
          <ModelExecutionBadge task={task} portraitMode={portraitMode} />
        )}

        {task.status === 'inbox' && !task.assigned_agent_id && (
          <div className={`flex items-center gap-2 ${portraitMode ? 'mb-3 py-2 px-3' : 'mb-2 py-1.5 px-2.5'} bg-amber-500/10 rounded-md border border-amber-500/30`}>
            <div className="w-2 h-2 bg-amber-400 rounded-full flex-shrink-0" />
            <span className="text-xs text-amber-200">Requiere agente — asignar para iniciar</span>
          </div>
        )}

        {['testing', 'verification'].includes(task.status) && dispatchError && (
          <div className={`flex items-start gap-2 ${portraitMode ? 'mb-3 py-2 px-3' : 'mb-2 py-1.5 px-2.5'} bg-red-500/10 rounded-md border border-red-500/30`}>
            <div className="w-2 h-2 bg-red-400 rounded-full mt-1 flex-shrink-0" />
            <span className="text-xs text-red-300">{dispatchError}</span>
          </div>
        )}

        {task.status === 'review' && !dispatchError && (
          <div className={`flex items-center gap-2 ${portraitMode ? 'mb-3 py-2 px-3' : 'mb-2 py-1.5 px-2.5'} bg-cyan-500/10 rounded-md border border-cyan-500/30`}>
            <div className="w-2 h-2 bg-cyan-400 rounded-full flex-shrink-0" />
            <span className="text-xs text-cyan-200">En cola — esperando verificación</span>
          </div>
        )}

        {task.assigned_agent && (
          <div className={`flex items-center gap-2 ${portraitMode ? 'mb-3 py-1.5 px-2' : 'mb-2 py-1 px-2'} bg-mc-bg-tertiary/50 rounded`}>
            <span className="text-base">{(task.assigned_agent as unknown as { avatar_emoji: string }).avatar_emoji}</span>
            <span className="text-xs text-mc-text-secondary truncate">{(task.assigned_agent as unknown as { name: string }).name}</span>
          </div>
        )}

        {task.workspace_path && (
          <div className={`flex items-center gap-1.5 ${portraitMode ? 'mb-2' : 'mb-1.5'}`}>
            <span className="text-[10px] px-1.5 py-0.5 bg-purple-500/15 text-purple-400 rounded border border-purple-500/20">
              {task.workspace_strategy === 'worktree' ? '\u{1F500}' : '\u{1F512}'} AISLADO
            </span>
          </div>
        )}

        <div className="flex items-center justify-between gap-2 pt-2 border-t border-mc-border/20">
          <div className="flex items-center gap-1.5">
            <div className={`w-1.5 h-1.5 rounded-full ${priorityDots[task.priority]}`} />
            <span className={`text-xs capitalize ${priorityStyles[task.priority]}`}>
              {task.priority === 'low' ? 'baja' : 
               task.priority === 'normal' ? 'normal' : 
               task.priority === 'high' ? 'alta' : 
               task.priority === 'urgent' ? 'urgente' : task.priority}
            </span>
            {task.jira_issue_key && (
              <span className="text-[10px] font-medium text-blue-400" title={`Linked: ${task.jira_issue_key}`}>
                JIRA
              </span>
            )}
          </div>
            <span className="text-[10px] text-mc-text-secondary/60" title="Última actualización">
              {formatDistanceToNow(new Date(task.updated_at), { addSuffix: true, locale: es })}
            </span>
        </div>

        {mobileMode && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMoveStatus();
            }}
            className={`w-full min-h-11 rounded-md border border-mc-border bg-mc-bg flex items-center justify-center gap-2 text-mc-text-secondary ${portraitMode ? 'mt-3 text-sm' : 'mt-2 text-xs'}`}
          >
            <ArrowRightLeft className="w-4 h-4" />
            Mover Estado
          </button>
        )}
      </div>
    </div>
  );
}
