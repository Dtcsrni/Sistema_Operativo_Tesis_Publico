#!/usr/bin/env python3
from urllib import request, error
import json
import os
import sys
import subprocess
from pathlib import Path

BASES = {
    "edge": os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip('/'),
    "desktop": os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:21434").rstrip('/'),
}
MODELS = {
    "edge": os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b"),
    "desktop": os.getenv("OPENCLAW_DESKTOP_COMPUTE_MODEL", "deepseek-r1:7b"),
}

results = {"bases": {}, "docker": {}, "processes": {}}

def http_get(url, timeout=5):
    try:
        with request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            return True, body
    except error.HTTPError as e:
        try:
            detail = e.read().decode('utf-8', errors='replace')
        except Exception:
            detail = str(e)
        return False, f"HTTPError:{e.code}:{detail}"
    except Exception as e:
        return False, f"Error:{type(e).__name__}:{e}"


def http_post(url, payload_bytes, timeout=20):
    req = request.Request(url, data=payload_bytes, method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            return True, body
    except error.HTTPError as e:
        try:
            detail = e.read().decode('utf-8', errors='replace')
        except Exception:
            detail = str(e)
        return False, f"HTTPError:{e.code}:{detail}"
    except Exception as e:
        return False, f"Error:{type(e).__name__}:{e}"

for name, base in BASES.items():
    r = {"base": base, "tags": None, "ps": None, "generate": None}
    tags_url = f"{base}/api/tags"
    ok, out = http_get(tags_url, timeout=5)
    r['tags'] = {"ok": ok, "out": out}
    ps_url = f"{base}/api/ps"
    ok, out = http_get(ps_url, timeout=5)
    r['ps'] = {"ok": ok, "out": out}
    # prueba /api/generate con payload pequeño
    gen_url = f"{base}/api/generate"
    payload = json.dumps({
        "model": MODELS.get(name, ""),
        "prompt": "diagnostic ping",
        "stream": False,
        "keep_alive": "1m",
        "options": {"num_predict": 1, "num_ctx": 512, "temperature": 0}
    }, ensure_ascii=False).encode('utf-8')
    ok, out = http_post(gen_url, payload, timeout=20)
    r['generate'] = {"ok": ok, "out": out}
    results['bases'][name] = r

# Docker checks
try:
    cp = subprocess.run(["docker", "ps", "--format", "{{.ID}} {{.Image}} {{.Names}}"], capture_output=True, text=True, timeout=10)
    results['docker']['ps'] = {"rc": cp.returncode, "out": cp.stdout.strip(), "err": cp.stderr.strip()}
    # look for ollama-like containers
    names = []
    for line in cp.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            if 'ollama' in parts[1].lower() or 'ollama' in parts[2].lower():
                names.append(parts[2])
    results['docker']['candidates'] = names
    logs = {}
    for n in names[:3]:
        try:
            cp2 = subprocess.run(["docker","logs", n, "--tail", "200"], capture_output=True, text=True, timeout=10)
            logs[n] = {"rc": cp2.returncode, "out": cp2.stdout.strip(), "err": cp2.stderr.strip()}
        except Exception as e:
            logs[n] = {"error": str(e)}
    results['docker']['logs'] = logs
except Exception as e:
    results['docker'] = {"error": str(e)}

# Process checks (tasklist)
try:
    cp = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ollama.exe"], capture_output=True, text=True, timeout=5)
    results['processes']['ollama'] = {"rc": cp.returncode, "out": cp.stdout.strip(), "err": cp.stderr.strip()}
except Exception as e:
    results['processes']['ollama'] = {"error": str(e)}

print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    sys.exit(0)
