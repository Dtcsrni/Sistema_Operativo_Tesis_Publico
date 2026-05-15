
import os
import sys
import json
import time
from pathlib import Path

# Add /app to sys.path
repo_root = Path("/app")
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from openclaw_local.telegram_bot import ollama_generate_streaming

def test():
    print("Testing OpenAI-compatible llama.cpp endpoint direct to PC (120s timeout)...")
    url = os.getenv("OPENCLAW_DESKTOP_RUNTIME_BASE_URL", "http://inferencia-llamacpp:8080/v1")
    model = "deepseek-r1:7b"
    prompt = "hola"
    
    def cb(tc, delta, st="agent"):
        print(f"TOKEN[{tc}]: {delta}")
        
    start = time.time()
    ok, res = ollama_generate_streaming(
        base_url=url,
        model=model,
        prompt=prompt,
        timeout_seconds=120,
        progress_callback=cb
    )
    duration = time.time() - start
    print(f"DONE in {duration:.2f}s")
    print(f"OK: {ok}")
    print(f"RES (len): {len(res)}")

if __name__ == "__main__":
    test()
