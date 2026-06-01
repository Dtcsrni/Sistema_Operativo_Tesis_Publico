import { NextRequest, NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';
import { queryOne, queryAll, run } from '@/lib/db';
import { getOpenClawClient } from '@/lib/openclaw/client';
import { broadcast } from '@/lib/events';
import { getProjectsPath, getMissionControlUrl } from '@/lib/config';
import { getRelevantKnowledge, formatKnowledgeForDispatch } from '@/lib/learner';
import { getTaskWorkflow } from '@/lib/workflow-engine';
import { syncGatewayAgentsToCatalog } from '@/lib/agent-catalog-sync';
import { pickDynamicAgent } from '@/lib/task-governance';
import { buildCheckpointContext } from '@/lib/checkpoint';
import { formatMailForDispatch } from '@/lib/mailbox';
import { createNote, getPendingNotesForDispatch } from '@/lib/task-notes';
import { createTaskWorkspace, determineIsolationStrategy } from '@/lib/workspace-isolation';
import { dispatchResponseHasModelFailure, normalizeOpenClawDispatchResponse } from '@/lib/openclaw/dispatch-response';
import type { Task, Agent, Product, OpenClawSession, WorkflowStage, TaskImage } from '@/lib/types';

export const dynamic = 'force-dynamic';
interface RouteParams {
  params: Promise<{ id: string }>;
}

function recordDispatchError(taskId: string, error: string): void {
  const now = new Date().toISOString();

  run(
    'UPDATE tasks SET planning_dispatch_error = ?, status_reason = ?, updated_at = ? WHERE id = ?',
    [error, `Dispatch failed: ${error}`, now, taskId]
  );

  const updatedTask = queryOne<Task>('SELECT * FROM tasks WHERE id = ?', [taskId]);
  if (updatedTask) {
    broadcast({ type: 'task_updated', payload: updatedTask });
  }
}

function dispatchErrorResponse(taskId: string, error: string, status: number) {
  recordDispatchError(taskId, error);
  return NextResponse.json({ error }, { status });
}

function recordDispatchActivity(taskId: string, agentId: string, message: string, metadata?: unknown): void {
  run(
    `INSERT INTO task_activities (id, task_id, agent_id, activity_type, message, metadata, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
    [crypto.randomUUID(), taskId, agentId, 'status_changed', message, metadata ? JSON.stringify(metadata) : null, new Date().toISOString()]
  );
}

function completionClaimed(text?: string | null): boolean {
  return /\b(?:TASK_COMPLETE|TEST_PASS|VERIFY_PASS)\s*:/i.test(text || '');
}

function stageEvidenceCounts(taskId: string): { deliverables: number; completedActivities: number } {
  const deliverable = queryOne<{ count: number }>('SELECT COUNT(*) as count FROM task_deliverables WHERE task_id = ?', [taskId]);
  const activity = queryOne<{ count: number }>(
    `SELECT COUNT(*) as count
     FROM task_activities
     WHERE task_id = ? AND activity_type IN ('completed','file_created','updated')`,
    [taskId]
  );
  return {
    deliverables: Number(deliverable?.count || 0),
    completedActivities: Number(activity?.count || 0),
  };
}

function expectedAgentForCurrentStage(taskId: string, status: string): { id: string; name: string; role: string } | null {
  const workflow = getTaskWorkflow(taskId);
  const stage = workflow?.stages.find(s => s.status === status);
  if (!stage?.role) return null;

  const roleAgent = queryOne<{ id: string; name: string; role: string }>(
    `SELECT a.id, a.name, a.role
     FROM task_roles tr
     JOIN agents a ON a.id = tr.agent_id
     WHERE tr.task_id = ? AND tr.role = ? AND a.status != 'offline'
     LIMIT 1`,
    [taskId, stage.role]
  );
  if (roleAgent) return roleAgent;

  return queryOne<{ id: string; name: string; role: string }>(
    `SELECT id, name, role
     FROM agents
     WHERE role = ? AND status != 'offline'
     ORDER BY status = 'standby' DESC, updated_at DESC
     LIMIT 1`,
    [stage.role]
  ) || null;
}

/**
 * POST /api/tasks/[id]/dispatch
 * 
 * Dispatches a task to its assigned agent's OpenClaw session.
 * Creates session if needed, sends task details to agent.
 */
export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;

    // Keep canonical agent catalog synced before every dispatch (best-effort)
    await syncGatewayAgentsToCatalog({ reason: 'dispatch' }).catch(err => {
      console.warn('[Dispatch] agent catalog sync failed:', err);
    });

    // Get task with agent info
    const task = queryOne<Task & { assigned_agent_name?: string; workspace_id: string }>(
      `SELECT t.*, a.name as assigned_agent_name, a.is_master
       FROM tasks t
       LEFT JOIN agents a ON t.assigned_agent_id = a.id
       WHERE t.id = ?`,
      [id]
    );

    if (!task) {
      return NextResponse.json({ error: 'Task not found' }, { status: 404 });
    }

    let assignedAgentId = task.assigned_agent_id;
    const expectedStageAgent = expectedAgentForCurrentStage(id, task.status);
    if (expectedStageAgent && assignedAgentId !== expectedStageAgent.id) {
      const previousAgentId = assignedAgentId;
      assignedAgentId = expectedStageAgent.id;
      run('UPDATE tasks SET assigned_agent_id = ?, updated_at = datetime(\'now\') WHERE id = ?', [assignedAgentId, id]);
      recordDispatchActivity(
        id,
        assignedAgentId,
        `Workflow corrected dispatch target to ${expectedStageAgent.name} for current stage role ${expectedStageAgent.role}`,
        { previous_agent_id: previousAgentId, expected_role: expectedStageAgent.role, task_status: task.status }
      );
      if (previousAgentId) {
        run(
          `UPDATE agents SET status = 'standby', updated_at = datetime('now')
           WHERE id = ? AND status = 'working'
             AND NOT EXISTS (
               SELECT 1 FROM tasks
               WHERE assigned_agent_id = ? AND id != ? AND status IN ('assigned','in_progress','testing','review','verification')
             )`,
          [previousAgentId, previousAgentId, id]
        );
      }
    }
    if (!assignedAgentId) {
      const statusRoleMap: Record<string, string> = {
        assigned: 'builder',
        in_progress: 'builder',
        testing: 'tester',
        review: 'reviewer',
        verification: 'reviewer',
      };
      const dynamicAgent = pickDynamicAgent(id, statusRoleMap[task.status] || 'builder');
      if (dynamicAgent) {
        assignedAgentId = dynamicAgent.id;
        run('UPDATE tasks SET assigned_agent_id = ?, updated_at = datetime(\'now\') WHERE id = ?', [assignedAgentId, id]);
      }
    }

    if (!assignedAgentId) {
      return dispatchErrorResponse(id, 'Task has no routable agent', 400);
    }

    // Get agent details
    const agent = queryOne<Agent>(
      'SELECT * FROM agents WHERE id = ?',
      [assignedAgentId]
    );

    if (!agent) {
      return dispatchErrorResponse(id, 'Assigned agent not found', 404);
    }

    // Check if dispatching to the master agent while there are other orchestrators available
    if (agent.is_master) {
      // Check for other master agents in the same workspace (excluding this one)
      const otherOrchestrators = queryAll<{
        id: string;
        name: string;
        role: string;
      }>(
        `SELECT id, name, role
         FROM agents
         WHERE is_master = 1
         AND id != ?
         AND workspace_id = ?
         AND status != 'offline'`,
        [agent.id, task.workspace_id]
      );

      if (otherOrchestrators.length > 0) {
        const message = `There ${otherOrchestrators.length === 1 ? 'is' : 'are'} ${otherOrchestrators.length} other orchestrator${otherOrchestrators.length === 1 ? '' : 's'} available in this workspace: ${otherOrchestrators.map(o => o.name).join(', ')}. Consider assigning this task to them instead.`;
        recordDispatchError(id, `Other orchestrators available: ${message}`);

        return NextResponse.json({
          success: false,
          warning: 'Other orchestrators available',
          message,
          otherOrchestrators,
        }, { status: 409 }); // 409 Conflict - indicating there's an alternative
      }
    }

    // Connect to OpenClaw Gateway
    const client = getOpenClawClient();
    if (!client.isConnected()) {
      try {
        await client.connect();
      } catch (err) {
        console.error('Failed to connect to OpenClaw Gateway:', err);
        client.forceReconnect();
        return dispatchErrorResponse(id, 'Failed to connect to OpenClaw Gateway', 503);
      }
    }

    // Get or create OpenClaw session for this agent + task combination
    let session = queryOne<OpenClawSession>(
      'SELECT * FROM openclaw_sessions WHERE agent_id = ? AND task_id = ? AND status = ?',
      [agent.id, id, 'active']
    );
    const reusedExistingSession = Boolean(session);

    const now = new Date().toISOString();

    if (!session) {
      // Create session record
      const sessionId = uuidv4();
      const openclawSessionId = `mission-control-${agent.name.toLowerCase().replace(/\s+/g, '-')}-${id}`;
      
      run(
        `INSERT INTO openclaw_sessions (id, agent_id, openclaw_session_id, task_id, channel, status, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        [sessionId, agent.id, openclawSessionId, id, 'mission-control', 'active', now, now]
      );

      session = queryOne<OpenClawSession>(
        'SELECT * FROM openclaw_sessions WHERE id = ?',
        [sessionId]
      );

      // Log session creation
      run(
        `INSERT INTO events (id, type, agent_id, message, created_at)
         VALUES (?, ?, ?, ?, ?)`,
        [uuidv4(), 'agent_status_changed', agent.id, `${agent.name} session created`, now]
      );
    }

    if (!session) {
      return dispatchErrorResponse(id, 'Failed to create agent session', 500);
    }

    console.info('[Dispatch] Agent session resolved for task dispatch', JSON.stringify({
      taskId: id,
      taskStatus: task.status,
      agentId: agent.id,
      agentName: agent.name,
      reusedExistingSession,
      sessionId: session.openclaw_session_id,
      sessionCreatedAt: session.created_at,
      sessionUpdatedAt: session.updated_at,
    }));

    // Cost cap warning check
    let costCapWarning: string | undefined;
    if (task.product_id) {
      const product = queryOne<Product>('SELECT * FROM products WHERE id = ?', [task.product_id]);
      if (product?.cost_cap_monthly) {
        const monthStart = new Date();
        monthStart.setDate(1);
        monthStart.setHours(0, 0, 0, 0);
        const monthlySpend = queryOne<{ total: number }>(
          `SELECT COALESCE(SUM(cost_usd), 0) as total FROM cost_events
           WHERE product_id = ? AND created_at >= ?`,
          [task.product_id, monthStart.toISOString()]
        );
        if (monthlySpend && monthlySpend.total >= product.cost_cap_monthly) {
          costCapWarning = `Monthly cost cap reached: $${monthlySpend.total.toFixed(2)}/$${product.cost_cap_monthly.toFixed(2)}`;
          console.warn(`[Dispatch] ${costCapWarning} for product ${product.name}`);
        }
      }
    }

    // Build task message for agent
    const priorityEmoji = {
      low: '🔵',
      normal: '⚪',
      high: '🟡',
      urgent: '🔴'
    }[task.priority] || '⚪';

    // Get project path for deliverables — with workspace isolation if needed
    const projectsPath = getProjectsPath();
    const projectDir = task.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    let taskProjectDir = `${projectsPath}/${projectDir}`;
    const missionControlUrl = getMissionControlUrl();

    // Create isolated workspace if parallel builds are possible
    // Only for builder dispatches (assigned/in_progress), not tester/reviewer
    let workspaceIsolated = false;
    let workspaceBranchName: string | undefined;
    let workspacePort: number | undefined;
    const isolationStrategy = determineIsolationStrategy(task as Task);
    const isBuilderDispatch = task.status === 'assigned' || task.status === 'in_progress' || task.status === 'inbox';
    if (isolationStrategy && isBuilderDispatch) {
      try {
        const workspace = await createTaskWorkspace(task as Task);
        taskProjectDir = workspace.path;
        workspaceIsolated = true;
        workspaceBranchName = workspace.branch;
        workspacePort = workspace.port;
        console.log(`[Dispatch] Created ${workspace.strategy} workspace for task ${task.id}: ${workspace.path}`);
      } catch (err) {
        console.warn(`[Dispatch] Workspace isolation failed, using default path:`, (err as Error).message);
      }
    }

    // Parse planning_spec and planning_agents if present (stored as JSON text on the task row)
    const rawTask = task as Task & { assigned_agent_name?: string; workspace_id: string; planning_spec?: string; planning_agents?: string };
    let planningSpecSection = '';
    let agentInstructionsSection = '';

    if (rawTask.planning_spec) {
      try {
        const spec = JSON.parse(rawTask.planning_spec);
        // planning_spec may be an object with spec_markdown, or a raw string
        const specText = typeof spec === 'string' ? spec : (spec.spec_markdown || JSON.stringify(spec, null, 2));
        planningSpecSection = `\n---\n**📋 PLANNING SPECIFICATION:**\n${specText}\n`;
      } catch {
        // If not valid JSON, treat as plain text
        planningSpecSection = `\n---\n**📋 PLANNING SPECIFICATION:**\n${rawTask.planning_spec}\n`;
      }
    }

    if (rawTask.planning_agents) {
      try {
        const agents = JSON.parse(rawTask.planning_agents);
        if (Array.isArray(agents)) {
          // Find instructions for this specific agent, or include all if none match
          const myInstructions = agents.find(
            (a: { agent_id?: string; name?: string; instructions?: string }) =>
              a.agent_id === agent.id || a.name === agent.name
          );
          if (myInstructions?.instructions) {
            agentInstructionsSection = `\n**🎯 YOUR INSTRUCTIONS:**\n${myInstructions.instructions}\n`;
          } else {
            // Include all agent instructions for context
            const allInstructions = agents
              .filter((a: { instructions?: string }) => a.instructions)
              .map((a: { name?: string; role?: string; instructions?: string }) =>
                `- **${a.name || a.role || 'Agent'}:** ${a.instructions}`
              )
              .join('\n');
            if (allInstructions) {
              agentInstructionsSection = `\n**🎯 AGENT INSTRUCTIONS:**\n${allInstructions}\n`;
            }
          }
        }
      } catch {
        // Ignore malformed planning_agents JSON
      }
    }

    // Inject relevant knowledge from the learner knowledge base
    let knowledgeSection = '';
    try {
      const knowledge = getRelevantKnowledge(task.workspace_id, task.title);
      knowledgeSection = formatKnowledgeForDispatch(knowledge);
    } catch {
      // Knowledge injection is best-effort
    }

    // Inject matched product skills (proven procedures from previous tasks)
    let skillsSection = '';
    if (task.product_id) {
      try {
        const { getMatchedSkills, formatSkillsForDispatch } = await import('@/lib/skills');
        const skills = getMatchedSkills(task.product_id, task.title, task.description || '', agent.name);
        skillsSection = formatSkillsForDispatch(skills);
      } catch {
        // Skills injection is best-effort
      }
    }

    // Determine role-specific instructions based on workflow template
    const workflow = getTaskWorkflow(id);
    let currentStage: WorkflowStage | undefined;
    let nextStage: WorkflowStage | undefined;
    if (workflow) {
      let stageIndex = workflow.stages.findIndex(s => s.status === task.status);
      // 'assigned' isn't a workflow stage — resolve to the 'build' stage (in_progress)
      if (stageIndex < 0 && (task.status === 'assigned' || task.status === 'inbox')) {
        stageIndex = workflow.stages.findIndex(s => s.role === 'builder');
      }
      if (stageIndex >= 0) {
        currentStage = workflow.stages[stageIndex];
        nextStage = workflow.stages[stageIndex + 1];
      }
    }

    const isBuilder = !currentStage || currentStage.role === 'builder' || task.status === 'assigned';
    const isTester = currentStage?.role === 'tester';
    const isVerifier = currentStage?.role === 'verifier' || currentStage?.role === 'reviewer';
    const nextStatus = nextStage?.status || 'review';
    const failEndpoint = `POST ${missionControlUrl}/api/tasks/${task.id}/fail`;

    let completionInstructions: string;
    if (isBuilder) {
      completionInstructions = `**IMPORTANTE:** Después de completar el trabajo, DEBES llamar a estas APIs:
1. Log activity: POST ${missionControlUrl}/api/tasks/${task.id}/activities
   Body: {"activity_type": "completed", "message": "Description of what was done"}
2. Register deliverable: POST ${missionControlUrl}/api/tasks/${task.id}/deliverables
   Body: {"deliverable_type": "file", "title": "File name", "path": "${taskProjectDir}/filename.html"}
3. Update status: PATCH ${missionControlUrl}/api/tasks/${task.id}
   Cuerpo: {"status": "${nextStatus}"}

Al terminar, responde con:
\`TASK_COMPLETE: [resumen breve de lo que hiciste]\``;
    } else if (isTester) {
      completionInstructions = `**TU ROL: TESTER** — Prueba los entregables de esta tarea.

Revisa el directorio de salida para entregables y ejecuta las pruebas aplicables.

**Si las pruebas PASAN:**
1. Log activity: POST ${missionControlUrl}/api/tasks/${task.id}/activities
   Body: {"activity_type": "completed", "message": "Tests passed: [summary]"}
2. Update status: PATCH ${missionControlUrl}/api/tasks/${task.id}
   Body: {"status": "${nextStatus}"}

**Si las pruebas FALLAN:**
1. ${failEndpoint}
   Cuerpo: {"reason": "Descripción detallada de lo que falló y qué necesita corrección"}

Responde con: \`TEST_PASS: [resumen]\` o \`TEST_FAIL: [qué falló]\``;
    } else if (isVerifier) {
      completionInstructions = `**TU ROL: VERIFICADOR** — Verifica que todo el trabajo cumpla con los estándares de calidad.

Revisa los entregables, resultados de pruebas y requisitos de la tarea.

**Si la verificación PASA:**
1. Log activity: POST ${missionControlUrl}/api/tasks/${task.id}/activities
   Body: {"activity_type": "completed", "message": "Verification passed: [summary]"}
2. Update status: PATCH ${missionControlUrl}/api/tasks/${task.id}
   Body: {"status": "${nextStatus}"}

**Si la verificación FALLA:**
1. ${failEndpoint}
   Cuerpo: {"reason": "Descripción detallada de lo que falló y qué necesita corrección"}

Responde con: \`VERIFY_PASS: [resumen]\` o \`VERIFY_FAIL: [qué falló]\``;
    } else {
      // Fallback for unknown roles
      completionInstructions = `**IMPORTANTE:** After completing work:
1. Update status: PATCH ${missionControlUrl}/api/tasks/${task.id}
   Body: {"status": "${nextStatus}"}`;
    }

    // Build image references section
    let imagesSection = '';
    if (task.images) {
      try {
        const images: TaskImage[] = JSON.parse(task.images);
        if (images.length > 0) {
          const imageList = images
            .map(img => `- ${img.original_name}: ${missionControlUrl}/api/task-images/${task.id}/${img.filename}`)
            .join('\n');
          imagesSection = `\n**Imágenes de Referencia:**\n${imageList}\n`;
        }
      } catch {
        // Ignore malformed images JSON
      }
    }

    // Build repo/PR section for builder agents when task has a repo
    let repoSection = '';
    if ((task as Task & { repo_url?: string }).repo_url && isBuilder) {
      const repoUrl = (task as Task & { repo_url?: string }).repo_url!;
      const repoBranch = (task as Task & { repo_branch?: string }).repo_branch || 'main';
      const branchName = `autopilot/${task.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 50)}`;

      repoSection = `
---
**\u{1F517} REPOSITORIO:**
- **Repo:** ${repoUrl}
- **Rama base:** ${repoBranch}
- **Rama de feature:** ${branchName}

**FLUJO DE TRABAJO GIT:**
1. Primero, verifica que tengas acceso a git: ejecuta \`git ls-remote ${repoUrl}\`
   - If this fails, report the error immediately via:
     PATCH ${missionControlUrl}/api/tasks/${task.id}
     Body: {"status_reason": "Git auth not configured: [error message]"}
     Luego DETENTE — no procedas sin acceso al repositorio.
2. Clone the repo (or use existing local copy)
3. Crea la rama \`${branchName}\` desde \`${repoBranch}\`
4. Implementa la funcionalidad
5. Commit with clear messages (reference task: ${task.id})
6. Haz push de la rama y crea un Pull Request (PR)

**REQUISITOS DEL PR:**
- Título: "\u{1F916} Autopilot: ${task.title}"
- Body must include:
  - What was built and why
  - Research backing (from the idea)
  - Technical approach taken
  - Any risks or trade-offs
  - Task ID: ${task.id}
- Target branch: ${repoBranch}
- After creating PR, report the PR URL:
  PATCH ${missionControlUrl}/api/tasks/${task.id}
  Cuerpo: {"pr_url": "<url del PR en github>", "pr_status": "open"}
`;
    }

    const roleLabel = currentStage?.label || 'Task';
    const taskMessage = `${priorityEmoji} **${isBuilder ? 'NUEVA TAREA ASIGNADA' : `${roleLabel.toUpperCase()} — ${task.title}`}**

**Título:** ${task.title}
${task.description ? `**Descripción:** ${task.description}\n` : ''}
**Prioridad:** ${task.priority.toUpperCase()}
${task.due_date ? `**Vencimiento:** ${task.due_date}\n` : ''}
**ID de Tarea:** ${task.id}
${planningSpecSection}${agentInstructionsSection}${skillsSection}${knowledgeSection}${imagesSection}${buildCheckpointContext(task.id) || ''}${formatMailForDispatch(agent.id) || ''}${repoSection}
${isBuilder ? (workspaceIsolated
  ? `**\u{1F512} ESPACIO DE TRABAJO AISLADO:** ${taskProjectDir}\n- **Puerto:** ${workspacePort || 'predeterminado'} (usa este para el servidor de desarrollo, NO el predeterminado)\n${workspaceBranchName ? `- **Rama:** ${workspaceBranchName}\n` : ''}- **IMPORTANTE:** NO modifiques archivos fuera de este directorio de espacio de trabajo. Otros agentes podrían estar trabajando en el mismo proyecto en paralelo. Todo tu trabajo debe permanecer dentro de: ${taskProjectDir}\nCrea este directorio si es necesario y guarda todos los entregables allí.\n`
  : `**DIRECTORIO DE SALIDA:** ${taskProjectDir}\nCrea este directorio y guarda todos los entregables allí.\n`)
: `**DIRECTORIO DE SALIDA:** ${taskProjectDir}\n`}
${completionInstructions}

Si necesitas ayuda o aclaraciones, pregúntale al orquestador.`;

    // Inject any pending operator notes (queued via /btw chat)
    const { formatted: pendingNotes } = getPendingNotesForDispatch(id);
    const finalMessage = pendingNotes ? taskMessage + pendingNotes : taskMessage;
    const gatewayMessage = process.env.OPENCLAW_MISSION_CONTROL_AUTO_EXECUTE === '0'
      ? finalMessage
      : `/execute ${task.id}\n${finalMessage}`;

    // Send message to agent's session using chat.send
    try {
      // Use sessionKey for routing to the agent's session
      // Format: {prefix}{openclaw_session_id} where prefix defaults to 'agent:main:'
      const prefix = agent.session_key_prefix || 'agent:main:';
      const sessionKey = `${prefix}${session.openclaw_session_id}`;
      const gatewayPayload = await client.call('chat.send', {
        sessionKey,
        message: gatewayMessage,
        channel: 'mission-control',
        executionProfile: 'mission_control_agent',
        idempotencyKey: `dispatch-${task.id}-${Date.now()}`
      }, Number(process.env.OPENCLAW_CHAT_SEND_TIMEOUT_MS || 180_000));
      const dispatchResult = normalizeOpenClawDispatchResponse(gatewayPayload);

      if (dispatchResult.status === 'approval_required') {
        const error = 'Dispatch requires approval under Mission Control policy';
        recordDispatchError(id, error);
        recordDispatchActivity(task.id, agent.id, error, dispatchResult);
        return NextResponse.json({ success: false, error, openclaw_response: dispatchResult }, { status: 409 });
      }

      if (dispatchResponseHasModelFailure(dispatchResult)) {
        const detail = dispatchResult.backend_errors[0]?.error || dispatchResult.status;
        const error = `Model unavailable for Mission Control dispatch: ${detail}`;
        recordDispatchError(id, error);
        run('UPDATE agents SET status = ?, updated_at = ? WHERE id = ?', ['standby', now, agent.id]);
        recordDispatchActivity(task.id, agent.id, 'Model unavailable; task was not marked as working', dispatchResult);
        return NextResponse.json({ success: false, error, openclaw_response: dispatchResult }, { status: 503 });
      }

      let assistantNoteId: string | undefined;
      if (dispatchResult.assistant_text) {
        const note = createNote(task.id, dispatchResult.assistant_text, 'direct', 'assistant');
        assistantNoteId = note.id;
        broadcast({ type: 'note_delivered', payload: note });
        recordDispatchActivity(task.id, agent.id, 'Assistant reply captured from Mission Control dispatch', dispatchResult);
        if (completionClaimed(dispatchResult.assistant_text)) {
          const evidence = stageEvidenceCounts(task.id);
          if (evidence.deliverables === 0 || evidence.completedActivities === 0) {
            const reason = 'Completion claim received, but required activity/deliverable API evidence is missing.';
            recordDispatchActivity(task.id, agent.id, reason, { ...evidence, dispatchResult });
            run(
              `UPDATE tasks SET status_reason = ?, planning_dispatch_error = NULL, updated_at = ? WHERE id = ?`,
              [reason, new Date().toISOString(), task.id]
            );
            const refreshedTask = queryOne<Task>('SELECT * FROM tasks WHERE id = ?', [task.id]);
            if (refreshedTask) {
              broadcast({ type: 'task_updated', payload: refreshedTask });
            }
          }
        }
      }

      console.info('[Dispatch] Task message delivered to agent session', JSON.stringify({
        taskId: task.id,
        agentId: agent.id,
        sessionId: session.openclaw_session_id,
        previousTaskStatus: task.status,
        expectedTaskStatus: task.status === 'assigned' ? 'in_progress' : task.status,
      }));

      // Only move to in_progress for builder dispatch (task is in 'assigned' status)
      // For tester/reviewer/verifier, the task status is already correct
      if (task.status === 'assigned') {
        run(
          'UPDATE tasks SET status = ?, planning_dispatch_error = NULL, status_reason = NULL, updated_at = ? WHERE id = ?',
          ['in_progress', now, id]
        );
      } else {
        run(
          'UPDATE tasks SET planning_dispatch_error = NULL, status_reason = NULL, updated_at = ? WHERE id = ?',
          [now, id]
        );
      }

      // Broadcast task update
      const updatedTask = queryOne<Task>('SELECT * FROM tasks WHERE id = ?', [id]);
      if (updatedTask) {
        console.info('[Dispatch] Task state after dispatch delivery', JSON.stringify({
          taskId: task.id,
          agentId: agent.id,
          sessionId: session.openclaw_session_id,
          taskStatus: updatedTask.status,
          planningDispatchError: updatedTask.planning_dispatch_error || null,
          statusReason: updatedTask.status_reason || null,
        }));
        broadcast({
          type: 'task_updated',
          payload: updatedTask,
        });
      }

      // Update agent status to working
      run(
        'UPDATE agents SET status = ?, updated_at = ? WHERE id = ?',
        ['working', now, agent.id]
      );

      // Log dispatch event to events table
      const eventId = uuidv4();
      run(
        `INSERT INTO events (id, type, agent_id, task_id, message, created_at)
         VALUES (?, ?, ?, ?, ?, ?)`,
        [eventId, 'task_dispatched', agent.id, task.id, `Task "${task.title}" dispatched to ${agent.name}`, now]
      );

      // Log dispatch activity to task_activities table (for Activity tab)
      const activityId = crypto.randomUUID();
      run(
        `INSERT INTO task_activities (id, task_id, agent_id, activity_type, message, metadata, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
        [
          activityId,
          task.id,
          agent.id,
          'status_changed',
          dispatchResult.assistant_text
            ? `Task dispatched to ${agent.name} - Assistant reply captured`
            : `Task dispatched to ${agent.name} - Agent is now working on this task`,
          JSON.stringify(dispatchResult),
          now,
        ]
      );

      return NextResponse.json({
        success: true,
        task_id: task.id,
        agent_id: agent.id,
        session_id: session.openclaw_session_id,
        assistant_note_id: assistantNoteId,
        openclaw_response: dispatchResult,
        message: 'Task dispatched to agent',
        ...(costCapWarning ? { cost_cap_warning: costCapWarning } : {}),
      });
    } catch (err) {
      console.error('Failed to send message to agent:', err);
      // Force-reconnect so the next dispatch attempt gets a fresh WebSocket
      const client2 = getOpenClawClient();
      client2.forceReconnect();
      // Reset task to 'assigned' so dispatch can be retried
      run(
        `UPDATE tasks SET status = 'assigned', planning_dispatch_error = ?, status_reason = ?, updated_at = datetime('now') WHERE id = ? AND status != 'done'`,
        [
          `Dispatch delivery failed: ${(err as Error).message}`,
          `Dispatch failed: ${(err as Error).message}`,
          id,
        ]
      );
      const failedTask = queryOne<Task>('SELECT * FROM tasks WHERE id = ?', [id]);
      if (failedTask) {
        broadcast({ type: 'task_updated', payload: failedTask });
      }
      return NextResponse.json(
        { error: `Failed to deliver task to agent: ${(err as Error).message}` },
        { status: 503 }
      );
    }
  } catch (error) {
    console.error('Failed to dispatch task:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
