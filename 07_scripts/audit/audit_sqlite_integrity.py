from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))  # subdirectory siblings

from common import ROOT


EXCLUDE_DIRS = {".git", ".venv", "node_modules", "scratch"}


def iter_sqlite_files(root: Path):
    for current_dir, dirs, files in root.walk(on_error=print):
        # Skip excluded dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f.endswith(".db") or f.endswith(".sqlite"):
                yield current_dir / f


def check_database_integrity(db_path: Path) -> list[str]:
    errors = []
    try:
        # uri=True allows read-only connection
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
        with conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            results = cursor.fetchall()
            
            # The result is typically a single row with 'ok' if no errors
            # Or multiple rows with error messages
            for row in results:
                if str(row[0]).lower() != "ok":
                    errors.append(str(row[0]))
    except sqlite3.DatabaseError as e:
        errors.append(f"Database error: {e}")
    except Exception as e:
        errors.append(f"Unexpected error: {e}")
    finally:
        try:
            conn.close()
        except:
            pass

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita la integridad estructural de bases de datos SQLite.")
    parser.parse_args()

    print("[PROCESS] Analizando integridad estructural de bases de datos SQLite...")
    
    total_scanned = 0
    all_errors = {}

    for db_path in iter_sqlite_files(ROOT):
        total_scanned += 1
        rel_path = db_path.relative_to(ROOT).as_posix()
        errors = check_database_integrity(db_path)
        if errors:
            all_errors[rel_path] = errors

    if all_errors:
        print("[CRITICAL ERROR] Se detectó corrupción en bases de datos SQLite:", file=sys.stderr)
        for rel_path, errs in all_errors.items():
            print(f"  - {rel_path}:", file=sys.stderr)
            for e in errs:
                print(f"      * {e}", file=sys.stderr)
        print("\nPara reparar run: `sqlite3 <db> \".recover\" | sqlite3 <new_db>` o restaura desde backup.", file=sys.stderr)
        return 1

    print(f"[OK] {total_scanned} bases de datos SQLite verificadas y saludables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
