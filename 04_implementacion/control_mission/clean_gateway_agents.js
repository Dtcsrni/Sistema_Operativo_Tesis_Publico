const Database = require('better-sqlite3');
const fs = require('fs');

const dbPath = './mission-control.db';
const backupPath = './mission-control.db.bak';

// Crear backup
fs.copyFileSync(dbPath, backupPath);
console.log('Backup creado:', backupPath);

const db = new Database(dbPath);

// Obtener IDs de agentes gateway
const gatewayAgents = db.prepare("SELECT id, name FROM agents WHERE source = 'gateway'").all();
console.log('Agentes gateway encontrados:', gatewayAgents.length);
gatewayAgents.forEach(a => console.log(' -', a.name, '(' + a.id + ')'));

if (gatewayAgents.length === 0) {
  console.log('No hay agentes gateway. Nada que hacer.');
  db.close();
  process.exit(0);
}

const ids = gatewayAgents.map(a => a.id);
const placeholders = ids.map(() => '?').join(',');

// Eliminar dependencias en orden correcto
db.transaction(() => {
  // 1. task_roles que referencian agentes gateway
  const tr = db.prepare('DELETE FROM task_roles WHERE agent_id IN (' + placeholders + ')').run(...ids);
  console.log('task_roles eliminados:', tr.changes);

  // 2. agent_health que referencian agentes gateway
  const ah = db.prepare('DELETE FROM agent_health WHERE agent_id IN (' + placeholders + ')').run(...ids);
  console.log('agent_health eliminados:', ah.changes);

  // 3. work_checkpoints que referencian agentes gateway
  const wc = db.prepare('DELETE FROM work_checkpoints WHERE agent_id IN (' + placeholders + ')').run(...ids);
  console.log('work_checkpoints eliminados:', wc.changes);

  // 4. agent_mailbox que referencian agentes gateway
  const am = db.prepare('DELETE FROM agent_mailbox WHERE from_agent_id IN (' + placeholders + ') OR to_agent_id IN (' + placeholders + ')').run(...ids, ...ids);
  console.log('agent_mailbox eliminados:', am.changes);

  // 5. knowledge_entries creadas por agentes gateway
  const ke = db.prepare('DELETE FROM knowledge_entries WHERE created_by_agent_id IN (' + placeholders + ')').run(...ids);
  console.log('knowledge_entries eliminados:', ke.changes);

  // 6. openclaw_sessions que referencian agentes gateway
  const os = db.prepare('DELETE FROM openclaw_sessions WHERE agent_id IN (' + placeholders + ')').run(...ids);
  console.log('openclaw_sessions eliminados:', os.changes);

  // 7. events que referencian agentes gateway
  const ev = db.prepare('DELETE FROM events WHERE agent_id IN (' + placeholders + ')').run(...ids);
  console.log('events eliminados:', ev.changes);

  // 8. messages enviadas por agentes gateway
  const ms = db.prepare('DELETE FROM messages WHERE sender_agent_id IN (' + placeholders + ')').run(...ids);
  console.log('messages eliminados:', ms.changes);

  // 9. conversation_participants de agentes gateway
  const cp = db.prepare('DELETE FROM conversation_participants WHERE agent_id IN (' + placeholders + ')').run(...ids);
  console.log('conversation_participants eliminados:', cp.changes);

  // 10. tasks asignadas a o creadas por agentes gateway (set null)
  const ta = db.prepare('UPDATE tasks SET assigned_agent_id = NULL WHERE assigned_agent_id IN (' + placeholders + ')').run(...ids);
  console.log('tasks asignadas desvinculadas:', ta.changes);
  const tc = db.prepare('UPDATE tasks SET created_by_agent_id = NULL WHERE created_by_agent_id IN (' + placeholders + ')').run(...ids);
  console.log('tasks creadas desvinculadas:', tc.changes);

  // 11. task_activities de agentes gateway
  const tact = db.prepare('UPDATE task_activities SET agent_id = NULL WHERE agent_id IN (' + placeholders + ')').run(...ids);
  console.log('task_activities desvinculadas:', tact.changes);

  // 12. cost_events de agentes gateway
  const ce = db.prepare('UPDATE cost_events SET agent_id = NULL WHERE agent_id IN (' + placeholders + ')').run(...ids);
  console.log('cost_events desvinculados:', ce.changes);

  // 13. product_skills de agentes gateway
  const ps = db.prepare('UPDATE product_skills SET created_by_agent_id = NULL WHERE created_by_agent_id IN (' + placeholders + ')').run(...ids);
  console.log('product_skills desvinculados:', ps.changes);

  // 14. operations_log de agentes gateway
  const ol = db.prepare('UPDATE operations_log SET agent_id = NULL WHERE agent_id IN (' + placeholders + ')').run(...ids);
  console.log('operations_log desvinculados:', ol.changes);

  // 15. research_cycles de agentes gateway
  const rc = db.prepare('UPDATE research_cycles SET agent_id = NULL WHERE agent_id IN (' + placeholders + ')').run(...ids);
  console.log('research_cycles desvinculados:', rc.changes);

  // 16. Finalmente eliminar los agentes gateway
  const del = db.prepare('DELETE FROM agents WHERE source = \'gateway\'').run();
  console.log('\nAgentes gateway ELIMINADOS:', del.changes);

  // 17. Registrar evento de limpieza
  const now = new Date().toISOString();
  db.prepare('INSERT INTO events (id, type, message, metadata, created_at) VALUES (lower(hex(randomblob(16))), \'system\', ?, ?, ?)').run(
    'Agentes gateway eliminados manualmente (limpieza de catalogo)',
    JSON.stringify({ deleted: del.changes, reason: 'manual_cleanup', timestamp: now }),
    now
  );
})();

// Verificar agentes restantes
const agents = db.prepare('SELECT name, role, status, source FROM agents ORDER BY source, name').all();
console.log('\nAgentes restantes en DB:');
agents.forEach(a => console.log('  [' + a.source + '] ' + a.name + ' (' + a.role + ') - ' + a.status));

db.close();
console.log('\nLimpieza completada exitosamente');
