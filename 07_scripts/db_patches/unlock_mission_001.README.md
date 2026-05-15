Instrucciones para desbloquear la Misión #001 en mission-control.db

IMPORTANTE: Esta operación es manual y potencialmente destructiva. Sigue los pasos y confirma antes de ejecutar.

1) Crear un backup seguro (vacuum into) antes de aplicar cambios:
   - Abrir node REPL o usar sqlite3/better-sqlite3: ejecutar el siguiente comando antes de modificar:

     python - <<'PY'
     import sqlite3, sys
     db = sqlite3.connect('04_implementacion/control_mission/mission-control.db')
     db.execute("VACUUM INTO '04_implementacion/control_mission/db-backups/mission-control.db.backup.manual'")
     db.close()
     print('Backup creado en 04_implementacion/control_mission/db-backups/')
     PY

   O usar la utilería del proyecto que crea backups en `db-backups/`.

2) Revisar el registro actual de la misión (sólo lectura):

   sqlite3 04_implementacion/control_mission/mission-control.db "SELECT id,title,status,status_reason,dispatch_lock FROM tasks WHERE id IN ('001','mission-001') OR title LIKE '%Misión%001%';"

3) Si confirmas que el registro correcto es `id='001'` (ajusta el WHERE si tu id difiere), ejecutar el parche SQL seguro:

   sqlite3 04_implementacion/control_mission/mission-control.db < unlock_mission_001.sql

4) Verifica el resultado:

   sqlite3 04_implementacion/control_mission/mission-control.db "SELECT id,title,status,status_reason,dispatch_lock FROM tasks WHERE id='001';"

5) Registrar la operación en el Ledger (requerido por gobernanza): actualiza `00_sistema_tesis/bitacora/` con el Step ID y el hash del SQL aplicado.

---

El archivo `unlock_mission_001.sql` contiene una plantilla segura con SELECT previo y UPDATE entre transacciones.

_Última actualización: `2026-05-15`._
