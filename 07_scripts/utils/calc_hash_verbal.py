import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



import hashlib
text = "implementalo, investiga las fuentes oficiales y descarga todo lo que sea necesario"
hash_val = hashlib.sha256(text.encode('utf-8')).hexdigest()
print(f"sha256:{hash_val}")
