import sqlite3
db_path = '04_implementacion/control_mission/mission-control.db'
conn = sqlite3.connect(db_path)
cursor = conn.execute("SELECT type, name, sql FROM sqlite_master")
for row in cursor:
    t, n, s = row
    if s and 'Bibliotecario' in s:
        print(f"FOUND in {t} {n}:")
        print(s)
conn.close()
