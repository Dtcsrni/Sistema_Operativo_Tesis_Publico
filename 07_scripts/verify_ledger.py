import hashlib
import re
import sys
from pathlib import Path
try:
    from guardrails import is_protected, backup_file
except ImportError:
    def is_protected(p): return False
    def backup_file(p): pass

def calculate_block_hash(text_block):
    return hashlib.sha256(text_block.encode('utf-8')).hexdigest()

def verify_ledger(file_path):
    content = file_path.read_text(encoding='utf-8')
    blocks = re.split(r'\n---+\n', content)
    
    errors = []
    headers = []
    chain_links = {} # ID -> (Prev, Next)
    
    for block in blocks:
        block = block.strip()
        if not block or block.startswith("# "):
            continue
            
        match_id = re.search(r'## \[(.*?)\]', block)
        if not match_id: continue
        
        block_id = match_id.group(1)
        headers.append(block_id)
        
        # Extraer Cadena
        match_chain = re.search(r'-\s+\*\*Cadena:\*\*\s+\[Anterior:\s+(.*?)\]\s+\|\s+\[Siguiente:\s+(.*?)\]', block)
        if match_chain:
            chain_links[block_id] = (match_chain.group(1), match_chain.group(2))
        
        # Hash Check
        match_hash = re.search(r'-\s+\*\*Hash:\*\*\s+`sha256:([a-f0-9]+)`', block)
        if match_hash:
            declared_hash = match_hash.group(1)
            match_content = re.search(r'<<<[\n\r]*(.*?)[\n\r]*>>>', block, re.DOTALL)
            if match_content:
                actual_hash = calculate_block_hash(match_content.group(1))
                if actual_hash != declared_hash:
                    errors.append(f"[{block_id}] HASH INVÁLIDO.")
        else:
            errors.append(f"[{block_id}] Sin hash.")
            
    # Verificar continuidad de la cadena
    for i, b_id in enumerate(headers):
        if b_id in chain_links:
            prev_link, next_link = chain_links[b_id]
            if i > 0:
                expected_prev = headers[i-1]
                if prev_link != expected_prev:
                    errors.append(f"[{b_id}] Quiebre de cadena: Anterior esperado {expected_prev}, real {prev_link}")
            if i < len(headers) - 1:
                expected_next = headers[i+1]
                if next_link != expected_next:
                    errors.append(f"[{b_id}] Quiebre de cadena: Siguiente esperado {expected_next}, real {next_link}")

    return errors, headers

def main():
    root = Path(__file__).resolve().parents[1]
    ledger_path = root / "00_sistema_tesis" / "bitacora" / "log_sesiones_trabajo_registradas.md"
    errors, headers = verify_ledger(ledger_path)
    
    if errors:
        print("AUDITORÍA LEDGER: FALLÓ")
        for err in errors: print(f"- {err}")
        sys.exit(1)
    else:
        print(f"AUDITORÍA LEDGER: OK ({len(headers)} bloques enlazados)")

if __name__ == "__main__": main()

