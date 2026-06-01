import json
import hashlib
from pathlib import Path
from datetime import datetime

class CapsuleGenerator:
    """
    Generador de Cápsulas de Conocimiento (.capsule).
    Congela el estado de una sesión para persistencia distribuida.
    """
    
    def __init__(self, root_path: Path):
        self.root = root_path
        self.capsules_dir = self.root / "00_sistema_tesis" / "capsulas"
        self.capsules_dir.mkdir(parents=True, exist_ok=True)

    def generate_capsule(self, session_id: str, context: dict, nexuses: list[str], bitacora_path: str) -> Path:
        """Crea un archivo .capsule con la información de la sesión."""
        
        capsule_data = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "session_info": {
                "id": session_id,
                "archetype": context.get("archetype", "General"),
                "bitacora_ref": str(bitacora_path)
            },
            "knowledge": {
                "nexuses": nexuses,
                "context_summary": context
            },
            "system_state": {
                "active_pets": context.get("active_pets", []),
                "parent_session": context.get("parent_session_id", "N/A")
            }
        }
        
        # Calcular hash de integridad de la cápsula
        raw_json = json.dumps(capsule_data, sort_keys=True, ensure_ascii=False)
        capsule_hash = hashlib.sha256(raw_json.encode()).hexdigest()
        capsule_data["integrity"] = {
            "hash": capsule_hash,
            "method": "sha256"
        }
        
        # Nombre de archivo determinístico
        filename = f"{session_id[:12]}_{datetime.now().strftime('%Y%m%d')}.capsule"
        capsule_path = self.capsules_dir / filename
        
        with open(capsule_path, "w", encoding="utf-8") as f:
            json.dump(capsule_data, f, indent=2, ensure_ascii=False)
            
        return capsule_path

if __name__ == "__main__":
    # Test
    gen = CapsuleGenerator(Path("."))
    dummy_ctx = {"archetype": "Investigación", "active_pets": ["PET-001"]}
    path = gen.generate_capsule("test-uuid-1234", dummy_ctx, ["Nexo 1", "Nexo 2"], "bitacora/test.md")
    print(f"[OK] Cápsula generada en: {path}")
