import sqlite3
db_path = '04_implementacion/control_mission/mission-control.db'
conn = sqlite3.connect(db_path)
cursor = conn.execute("SELECT name FROM sqlite_master")
for row in cursor:
    if 'Bibliotecario' in row[0]:
        print(f"FOUND TABLE/INDEX NAME: {row[0]}")
conn.close()
