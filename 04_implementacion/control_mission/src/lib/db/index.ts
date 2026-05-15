import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import { schema } from './schema';
import { runMigrations } from './migrations';
import { ensureCatalogSyncScheduled } from '@/lib/agent-catalog-sync';

const DB_PATH = process.env.DATABASE_PATH || path.join(process.cwd(), 'mission-control.db');

let db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (!db) {
    const isNewDb = !fs.existsSync(DB_PATH);
    
    db = new Database(DB_PATH);
    
    // Optimización de persistencia (DEC-0035)
    db.pragma('journal_mode = WAL');
    db.pragma('synchronous = NORMAL');
    db.pragma('wal_autocheckpoint = 1000');
    db.pragma('busy_timeout = 10000'); // Evitar errores SQLITE_BUSY en concurrencia
    db.pragma('foreign_keys = ON');
    db.pragma('encoding = "UTF-8"');

    try {
      // Initialize base schema (creates tables if they don't exist)
      db.exec(schema);
    } catch (error: any) {
      if (error.code === 'SQLITE_CORRUPT') {
        console.error('[DB] DATABASE CORRUPTION DETECTED DURING INITIALIZATION!');
        // En producción, el contenedor init-db debería haberlo arreglado antes.
        // Aquí solo fallamos rápido para evitar daños mayores.
        throw error;
      }
      throw error;
    }

    // Run migrations for schema updates
    // This handles both new and existing databases
    runMigrations(db);

    // Recover orphaned autopilot cycles from prior crash/restart
    import('@/lib/autopilot/recovery').then(({ recoverOrphanedCycles }) =>
      recoverOrphanedCycles().catch(err => console.warn('[Recovery] Failed:', err))
    );

    // Keep Mission Control's agent catalog synced with OpenClaw-installed agents
    ensureCatalogSyncScheduled();
    // Task watchdog: monitor active tasks and auto-recover when stale
    import('@/lib/task-watchdog').then(({ ensureTaskWatchdogScheduled }) => ensureTaskWatchdogScheduled());
    
    if (isNewDb) {
      console.log('[DB] New database created at:', DB_PATH);
    }
  }
  return db;
}

export function closeDb(): void {
  if (db) {
    db.close();
    db = null;
  }
}

// Type-safe query helpers
export function queryAll<T>(sql: string, params: unknown[] = []): T[] {
  const stmt = getDb().prepare(sql);
  return stmt.all(...params) as T[];
}

export function queryOne<T>(sql: string, params: unknown[] = []): T | undefined {
  const stmt = getDb().prepare(sql);
  return stmt.get(...params) as T | undefined;
}

export function run(sql: string, params: unknown[] = []): Database.RunResult {
  const stmt = getDb().prepare(sql);
  return stmt.run(...params);
}

export function transaction<T>(fn: () => T): T {
  const db = getDb();
  return db.transaction(fn)();
}

// Export migration utilities for CLI use
export { runMigrations, getMigrationStatus } from './migrations';
