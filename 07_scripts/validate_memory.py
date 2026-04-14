from __future__ import annotations

from build_memory import OUTPUT_PATH, render_memory


REQUIRED_MARKERS = (
    "Este `MEMORY.md` es un artefacto derivado",
    "Últimos cambios validados",
    "Próximos pendientes críticos",
    "Referencias base",
)


def validate() -> list[str]:
    errors: list[str] = []
    if not OUTPUT_PATH.exists():
        return [f"Falta el artefacto derivado: {OUTPUT_PATH.name}"]

    content = OUTPUT_PATH.read_text(encoding="utf-8")
    for marker in REQUIRED_MARKERS:
        if marker not in content:
            errors.append(f"MEMORY.md no contiene el marcador requerido: {marker}")

    expected = render_memory()
    if content != expected:
        errors.append("MEMORY.md tiene drift respecto a su fuente canónica; ejecuta build_memory.py")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("VALIDACION MEMORY: ERROR")
        for item in errors:
            print(f"- {item}")
        return 1
    print("VALIDACION MEMORY: OK")
    print("MEMORY.md está sincronizado con canon y trazabilidad")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
