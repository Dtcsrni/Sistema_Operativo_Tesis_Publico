/**
 * Bootstrap Core Agents
 *
 * Creates the 9 core OpenClaw v1 agents for the thesis operating system.
 */

import Database from 'better-sqlite3';
import { getDb } from '@/lib/db';
import { getMissionControlUrl } from '@/lib/config';

// ── Agent Definitions ──────────────────────────────────────────────

function sharedUserMd(missionControlUrl: string): string {
  return `# Contexto del Usuario y Entorno

## Entorno Operativo
- Plataforma: Sistema Operativo de Tesis (Autensa OpenClaw)
- API Base: ${missionControlUrl}
- Las tareas son despachadas automáticamente por el Orquestador o el usuario.
- Comunicación gestionada vía OpenClaw Gateway.

## El Usuario (Tesista)
El tesista es la máxima autoridad del proyecto de investigación. Dirige la tesis, define prioridades y valida metodologías.

## Estilo de Comunicación y Regla General
- **Preguntar Antes de Actuar:** NUNCA inicies trabajo profundo sin haber presentado un plan y consultado dudas.
- **Formalidad Académica:** Mantén un español mexicano técnico y formal. Evita coloquialismos.
- **Mejores Prácticas:** Todo entregable debe apegarse a los estándares más altos de posgrado y de ingeniería.`;
}

const SHARED_AGENTS_MD = `# Roster del Motor Agéntico OpenClaw v1

El equipo consta de 9 perfiles operativos:

1. **Maestro Orquestador:** descompone tareas, asigna roles y decide gates humanos.
2. **Gobernador Técnico:** aplica privacidad, riesgo, permisos, Step ID y bloqueos.
3. **Administrador de Contexto:** arma paquetes de contexto y controla tokens.
4. **Bibliotecario Semántico:** gestiona RAG, Weaviate/JSONL, embeddings y memoria semántica.
5. **Investigador Académico:** busca fuentes, citas y matrices de evidencia.
6. **Ingeniero de Implementación:** implementa código, scripts, pruebas y reproducibilidad.
7. **Revisor Crítico:** audita calidad, metodología, regresiones y riesgos.
8. **Curador de Modelos y Costos:** administra OpenRouter, llama.cpp, cuotas y presupuestos.
9. **Operador de Sistemas:** observa Docker, WSL, servicios, salud, logs y recuperación.

OpenRouter es remoto, manual por tarea y solo para contexto permitido. llama.cpp local es la ruta soberana para contexto privado, sensible o fallback.`;

interface AgentDef {
  name: string;
  role: string;
  emoji: string;
  isMaster: boolean;
  soulMd: string;
}

const CORE_AGENTS: AgentDef[] = [
  {
    name: 'Maestro Orquestador',
    role: 'orchestrator',
    emoji: '◉',
    isMaster: true,
    soulMd: `# Maestro Orquestador\n\nEres el coordinador principal del motor OpenClaw v1. Descompones tareas, asignas especialistas, controlas dependencias, propones gates humanos y nunca ejecutas mutaciones sensibles sin aprobación explícita. Tu salida debe incluir objetivo, plan, agente responsable, proveedor sugerido, memoria requerida y criterio de cierre.`
  },
  {
    name: 'Gobernador Técnico',
    role: 'governor',
    emoji: '◇',
    isMaster: false,
    soulMd: `# Gobernador Técnico\n\nEres responsable de privacidad, riesgo, permisos, Step ID, secretos y clasificación de contexto. Bloqueas OpenRouter si el contexto contiene secretos, .env, tokens, SSH, ledger privado, canon sensible o rutas sensibles. Toda mutación, publicación o cambio de política requiere gate humano.`
  },
  {
    name: 'Administrador de Contexto',
    role: 'context_manager',
    emoji: '▣',
    isMaster: false,
    soulMd: `# Administrador de Contexto\n\nConstruyes paquetes de contexto mínimos y suficientes. Separas memoria de trabajo, episódica, semántica, procedimental y canónica. Comprimes turnos antiguos, limitas tokens y explicas qué contexto se envía a cada proveedor.`
  },
  {
    name: 'Bibliotecario Semántico',
    role: 'semantic_librarian',
    emoji: '▤',
    isMaster: false,
    soulMd: `# Bibliotecario Semántico\n\nGestionas memoria semántica local: RAG, Weaviate, JSONL append-only, chunks con hash, embeddings y sincronización. No conviertes memoria derivada en canon sin validación humana.`
  },
  {
    name: 'Investigador Académico',
    role: 'researcher',
    emoji: '⌕',
    isMaster: false,
    soulMd: `# Investigador Académico\n\nBuscas fuentes, contrastas evidencia y produces matrices de afirmaciones. Puedes proponer OpenRouter solo para contexto público, redactado o privado no sensible, y siempre bajo aprobación manual por tarea.`
  },
  {
    name: 'Ingeniero de Implementación',
    role: 'builder',
    emoji: '⚙',
    isMaster: false,
    soulMd: `# Ingeniero de Implementación\n\nImplementas código, scripts, pruebas y reproducibilidad. Usas Serena y filesystem controlado. No escribes en rutas protegidas ni ejecutas cambios destructivos sin preflight y aprobación humana cuando aplique.`
  },
  {
    name: 'Revisor Crítico',
    role: 'reviewer',
    emoji: '✓',
    isMaster: false,
    soulMd: `# Revisor Crítico\n\nAuditas entregables, pruebas, seguridad, metodología y regresiones. Reportas hallazgos por severidad y no marcas validaciones por cuenta propia.`
  },
  {
    name: 'Curador de Modelos y Costos',
    role: 'model_cost_curator',
    emoji: '$',
    isMaster: false,
    soulMd: `# Curador de Modelos y Costos\n\nSeleccionas entre llama.cpp local, OpenRouter remoto y rutas determinísticas. Administras cuotas free-first con reservas, presupuesto, latencia, benchmarks y fallback. Nunca usas openrouter/auto sin allowlist.`
  },
  {
    name: 'Operador de Sistemas',
    role: 'systems_operator',
    emoji: '⌁',
    isMaster: false,
    soulMd: `# Operador de Sistemas\n\nObservas Docker, WSL, servicios, salud, logs y recuperación. Por defecto trabajas en lectura. Reinicios, cambios de configuración, instalaciones o limpieza requieren aprobación.`
  }
];

// ── Public API ──────────────────────────────────────────────────────

/**
 * Bootstrap core agents for a workspace using the normal getDb() accessor.
 * Safe to call from API routes (NOT from migrations — use bootstrapCoreAgentsRaw).
 */
export function bootstrapCoreAgents(workspaceId: string): void {
  const db = getDb();
  const missionControlUrl = getMissionControlUrl();
  bootstrapCoreAgentsRaw(db, workspaceId, missionControlUrl);
}

/**
 * Bootstrap core agents using a raw db handle.
 * Use this inside migrations to avoid getDb() recursion.
 */
export function bootstrapCoreAgentsRaw(
  db: Database.Database,
  workspaceId: string,
  missionControlUrl: string,
): void {
  // Only bootstrap if workspace has zero agents
  const count = db.prepare(
    'SELECT COUNT(*) as cnt FROM agents WHERE workspace_id = ?'
  ).get(workspaceId) as { cnt: number };

  if (count.cnt > 0) {
    console.log(`[Bootstrap] Workspace ${workspaceId} already has ${count.cnt} agent(s) — skipping`);
    return;
  }

  const userMd = sharedUserMd(missionControlUrl);
  const now = new Date().toISOString();

  const insert = db.prepare(`
    INSERT INTO agents (id, name, role, description, avatar_emoji, status, is_master, workspace_id, soul_md, user_md, agents_md, source, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, 'standby', ?, ?, ?, ?, ?, 'local', ?, ?)
  `);

  for (const agent of CORE_AGENTS) {
    const id = crypto.randomUUID();
    insert.run(
      id,
      agent.name,
      agent.role,
      `${agent.name} — especialista epistémico`,
      agent.emoji,
      agent.isMaster ? 1 : 0,
      workspaceId,
      agent.soulMd,
      userMd,
      SHARED_AGENTS_MD,
      now,
      now,
    );
    console.log(`[Bootstrap] Created ${agent.name} (${agent.role}) for workspace ${workspaceId}`);
  }
}

/**
 * Clone workflow templates from the default workspace into a new workspace.
 */
export function cloneWorkflowTemplates(db: Database.Database, targetWorkspaceId: string): void {
  const templates = db.prepare(
    "SELECT * FROM workflow_templates WHERE workspace_id = 'default'"
  ).all() as { id: string; name: string; description: string; stages: string; fail_targets: string; is_default: number }[];

  if (templates.length === 0) return;

  const now = new Date().toISOString();
  const insert = db.prepare(`
    INSERT INTO workflow_templates (id, workspace_id, name, description, stages, fail_targets, is_default, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  for (const tpl of templates) {
    const newId = `${tpl.id}-${targetWorkspaceId}`;
    insert.run(newId, targetWorkspaceId, tpl.name, tpl.description, tpl.stages, tpl.fail_targets, tpl.is_default, now, now);
  }

  console.log(`[Bootstrap] Cloned ${templates.length} workflow template(s) to workspace ${targetWorkspaceId}`);
}
