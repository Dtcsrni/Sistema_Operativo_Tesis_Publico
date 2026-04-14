import hashlib
import re
from pathlib import Path

def get_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

root = Path(".")
ledger_path = root / "00_sistema_tesis" / "bitacora" / "log_sesiones_trabajo_registradas.md"
content = ledger_path.read_text(encoding='utf-8')

matches = re.findall(r'## \[(.*?)\].*?<<<[\n\r]*(.*?)[\n\r]*>>>', content, re.DOTALL)

results = []
for block_id, text in matches:
    results.append(f"{block_id}: {get_hash(text)}")

Path("real_hashes.txt").write_text("\n".join(results))
print("Hashes written to real_hashes.txt")

