'use client';

import type { AgentHealthState } from '@/lib/types';

interface HealthIndicatorProps {
  state: AgentHealthState;
  size?: 'sm' | 'md';
  showLabel?: boolean;
}

const healthConfig: Record<AgentHealthState, { color: string; pulse: boolean; label: string }> = {
  idle: { color: 'bg-gray-400', pulse: false, label: 'Inactivo' },
  working: { color: 'bg-green-400', pulse: false, label: 'Trabajando' },
  stalled: { color: 'bg-yellow-400', pulse: true, label: 'Estancado' },
  stuck: { color: 'bg-red-400', pulse: true, label: 'Atascado' },
  zombie: { color: 'bg-red-500', pulse: true, label: 'Zombi' },
  offline: { color: 'bg-gray-600', pulse: false, label: 'Desconectado' },
  active_recently: { color: 'bg-green-400', pulse: false, label: 'Activo' },
  working_silently: { color: 'bg-cyan-400', pulse: false, label: 'Trabajando en silencio' },
  awaiting_reply: { color: 'bg-blue-400', pulse: true, label: 'Esperando respuesta' },
  awaiting_model: { color: 'bg-amber-400', pulse: true, label: 'Esperando modelo' },
  model_unavailable: { color: 'bg-red-400', pulse: true, label: 'Sin modelo' },
  waiting_for_delivery: { color: 'bg-amber-400', pulse: true, label: 'Mensaje en cola' },
  completed_not_surfaced: { color: 'bg-amber-400', pulse: true, label: 'Completado oculto' },
  needs_attention: { color: 'bg-yellow-400', pulse: true, label: 'Requiere atención' },
  no_heartbeat: { color: 'bg-red-500', pulse: true, label: 'Sin sesión' },
  genuinely_stuck: { color: 'bg-red-500', pulse: true, label: 'Atascado' },
  blocked: { color: 'bg-red-400', pulse: true, label: 'Bloqueado' },
};

export function HealthIndicator({ state, size = 'sm', showLabel = false }: HealthIndicatorProps) {
  const config = healthConfig[state] || healthConfig.idle;
  const dotSize = size === 'sm' ? 'w-2 h-2' : 'w-3 h-3';

  return (
    <div className="flex items-center gap-1.5">
      <div className={`${dotSize} rounded-full ${config.color} ${config.pulse ? 'animate-pulse' : ''}`} />
      {showLabel && (
        <span className="text-[10px] text-mc-text-secondary uppercase">{config.label}</span>
      )}
    </div>
  );
}
