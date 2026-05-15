from pathlib import Path
import os
import sys
from typing import Any

# Asegurar que podemos importar los módulos locales
sys.path.append(str(Path(__file__).parent.parent.parent))

from runtime.openclaw.openclaw_local.orchestrator import Orchestrator, CommunicationChannel
from runtime.openclaw.openclaw_local.storage import OpenClawStore

class MockChannel(CommunicationChannel):
    def __init__(self):
        self.sent_messages = []
        self.actions = []

    def send_message(self, text: str, **kwargs) -> Any:
        print(f"[MOCK] Sending message: {text}")
        self.sent_messages.append(text)
        return {"status": "sent", "message_id": len(self.sent_messages)}

    def send_action(self, action: str) -> None:
        print(f"[MOCK] Sending action: {action}")
        self.actions.append(action)

    def update_message(self, message_id: Any, text: str) -> None:
        print(f"[MOCK] Updating message {message_id}: {text}")

    def send_photo(self, image_path: Path, caption: str = "") -> Any:
        print(f"[MOCK] Sending photo: {image_path} with caption: {caption}")
        return {"status": "sent"}

def smoke_test():
    import tempfile
    import shutil
    
    temp_data = Path(tempfile.mkdtemp())
    print(f"[DEBUG] Using temp data dir: {temp_data}")
    
    repo_root = Path(os.getenv("OPENCLAW_REPO_ROOT", "v:/Sistema_Operativo_Tesis_Posgrado"))
    store = OpenClawStore(temp_data)
    
    orchestrator = Orchestrator(repo_root, store)
    channel = MockChannel()
    
    # Test 1: Comando determinista /hora
    print("\nTest 1: /hora")
    res1 = orchestrator.dispatch_command("/hora", "", channel, chat_id="smoke_test")
    print(f"Result 1: {res1}")
    
    # Test 2: Chat básico (simulado)
    # Nota: Esto podría fallar si no hay modelos levantados, pero verificamos el flujo.
    print("\nTest 2: Chat 'Hola'")
    try:
        # Forzamos un profile local para no depender de inferencia pesada si es posible
        res2 = orchestrator.dispatch_command("chat", "Hola", channel, chat_id="smoke_test")
        print(f"Result 2: {res2}")
    except Exception as e:
        print(f"Test 2 failed (expected if backends are down): {e}")

    # Test 3: Perfilado semántico (simulado)
    print("\nTest 3: Intent Profiling")
    from runtime.openclaw.openclaw_local.orchestrator import _chat_request_profile_fallback
    profile = _chat_request_profile_fallback("Investiga la historia de OpenClaw")
    print(f"Profile: {profile}")

    print("\n--- Smoke Test Finished ---")

if __name__ == "__main__":
    smoke_test()
