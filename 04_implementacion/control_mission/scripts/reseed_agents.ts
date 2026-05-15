import Database from 'better-sqlite3';
import { bootstrapCoreAgentsRaw } from '../src/lib/bootstrap-agents';

const dbPath = 'mission-control.db';
const db = new Database(dbPath);

console.log('Clearing existing local agents and related data...');

// Disable foreign keys so we can forcefully delete agents
db.pragma('foreign_keys = OFF');

const workspaceId = 'default';

// Clean up related data to prevent orphans
db.prepare('DELETE FROM conversation_participants').run();
db.prepare('DELETE FROM messages').run();
db.prepare('DELETE FROM conversations').run();
db.prepare('DELETE FROM events').run();
//
db.prepare('DELETE FROM tasks').run();

// Delete ALL agents 
const deleteAgentsStmt = db.prepare('DELETE FROM agents WHERE workspace_id = ? OR workspace_id IS NULL');
const result = deleteAgentsStmt.run(workspaceId);
console.log(`Deleted ${result.changes} agents from workspace ${workspaceId}`);

// Re-enable foreign keys
db.pragma('foreign_keys = ON');

console.log('Seeding new 9 epistemic agents...');
bootstrapCoreAgentsRaw(db, workspaceId, 'http://localhost:4000');

console.log('Done!');
db.close();
