from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from common import ROOT


ZIP_VERSION_PATTERN = re.compile(r"_v(\d+)\.zip$", re.IGNORECASE)
ARTIFACT_VERSION_PATTERN = re.compile(r"__v(\d+)\.[^.]+$", re.IGNORECASE)

SOURCE_ZIP_DEFAULT = Path(r"O:\Descargas\sistema_operativo_tesis_iot__descargable_unico_verificado__v10.zip")
BASE_DIR = ROOT / "00_sistema_tesis"
STAGING_ROOT = BASE_DIR / "evidencia_privada" / "staging_ingestion"
AREAS = {
    "01_contexto_canonico": BASE_DIR / "01_contexto_canonico",
    "02_evidencia": BASE_DIR / "02_evidencia",
    "03_metadatos": BASE_DIR / "03_metadatos",
    "04_politicas_y_gobernanza": BASE_DIR / "04_politicas_y_gobernanza",
    "05_registros_de_ingestion": BASE_DIR / "05_registros_de_ingestion",
    "06_historico_de_paquetes": BASE_DIR / "06_historico_de_paquetes",
}
INDEX_PATH = AREAS["05_registros_de_ingestion"] / "indice_maestro_ingestion_contexto_iot.csv"


@dataclass(frozen=True)
class ArtifactSpec:
    file_name: str
    area: str
    role: str
    priority: str
    source_type: str
    dependencies: str
    expected_version: str


EXPECTED_ARTIFACTS = [
    ArtifactSpec(
        file_name="sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_humana__v09.md",
        area="01_contexto_canonico",
        role="Vista legible primaria del contexto canónico",
        priority="P0",
        source_type="fuente_de_verdad",
        dependencies="sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_maquina__v09.jsonl; sistema_operativo_tesis_iot__registro_estructurado_del_contexto__v09.sqlite",
        expected_version="v09",
    ),
    ArtifactSpec(
        file_name="sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_maquina__v09.jsonl",
        area="01_contexto_canonico",
        role="Vista máquina del contexto canónico",
        priority="P0",
        source_type="fuente_de_verdad",
        dependencies="sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_humana__v09.md; sistema_operativo_tesis_iot__registro_estructurado_del_contexto__v09.sqlite",
        expected_version="v09",
    ),
    ArtifactSpec(
        file_name="sistema_operativo_tesis_iot__registro_estructurado_del_contexto__v09.sqlite",
        area="01_contexto_canonico",
        role="Base estructurada principal del contexto",
        priority="P0",
        source_type="fuente_de_verdad",
        dependencies="sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_humana__v09.md; sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_maquina__v09.jsonl",
        expected_version="v09",
    ),
    ArtifactSpec(
        file_name="sistema_operativo_tesis_iot__catalogo_general_de_artefactos__v09.json",
        area="03_metadatos",
        role="Catálogo general de inventario",
        priority="P1",
        source_type="soporte",
        dependencies="sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_humana__v09.md",
        expected_version="v09",
    ),
    ArtifactSpec(
        file_name="sistema_operativo_tesis_iot__columna_vertebral_de_evidencia__v09.tsv",
        area="02_evidencia",
        role="Columna vertebral de evidencia para defensa",
        priority="P1",
        source_type="evidencia",
        dependencies="sistema_operativo_tesis_iot__justificacion_de_inclusion_por_archivo__v09.tsv",
        expected_version="v09",
    ),
    ArtifactSpec(
        file_name="sistema_operativo_tesis_iot__convencion_de_nombres__v09.json",
        area="03_metadatos",
        role="Convención de nombres y normalización",
        priority="P1",
        source_type="soporte",
        dependencies="sistema_operativo_tesis_iot__catalogo_general_de_artefactos__v09.json",
        expected_version="v09",
    ),
    ArtifactSpec(
        file_name="sistema_operativo_tesis_iot__guia_de_ingestion__v09.md",
        area="04_politicas_y_gobernanza",
        role="Guía operativa de ingestión",
        priority="P1",
        source_type="politica",
        dependencies="sistema_operativo_tesis_iot__convencion_de_nombres__v09.json",
        expected_version="v09",
    ),
    ArtifactSpec(
        file_name="sistema_operativo_tesis_iot__justificacion_de_inclusion_por_archivo__v09.tsv",
        area="02_evidencia",
        role="Justificación de inclusión por archivo",
        priority="P1",
        source_type="evidencia",
        dependencies="sistema_operativo_tesis_iot__catalogo_general_de_artefactos__v09.json",
        expected_version="v09",
    ),
    ArtifactSpec(
        file_name="sistema_operativo_tesis_iot__politica_de_valor_documental__v09.md",
        area="04_politicas_y_gobernanza",
        role="Política de valor documental",
        priority="P1",
        source_type="politica",
        dependencies="sistema_operativo_tesis_iot__guia_de_ingestion__v09.md",
        expected_version="v09",
    ),
    ArtifactSpec(
        file_name="sistema_operativo_tesis_iot__politica_de_estatus_del_overleaf_actual__v09.md",
        area="04_politicas_y_gobernanza",
        role="Política de estatus de Overleaf actual (borrador no canónico)",
        priority="P1",
        source_type="politica",
        dependencies="sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_humana__v09.md",
        expected_version="v09",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingestión canónica del paquete de contexto IoT.")
    parser.add_argument("--source", default=str(SOURCE_ZIP_DEFAULT), help="Ruta absoluta al ZIP fuente.")
    parser.add_argument("--mode", choices=["check", "apply"], default="check", help="Modo de ejecución.")
    return parser.parse_args()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_compact() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def rel_posix(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def parse_zip_version(file_name: str) -> str:
    match = ZIP_VERSION_PATTERN.search(file_name)
    return f"v{match.group(1)}" if match else "desconocida"


def parse_artifact_version(file_name: str) -> str:
    match = ARTIFACT_VERSION_PATTERN.search(file_name)
    return f"v{match.group(1)}" if match else "desconocida"


def ensure_area_structure() -> None:
    for path in AREAS.values():
        path.mkdir(parents=True, exist_ok=True)


def extract_zip_to_staging(source_zip: Path, stamp: str) -> tuple[Path, list[Path], list[str]]:
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    extraction_root = STAGING_ROOT / stamp
    extraction_root.mkdir(parents=True, exist_ok=True)
    extracted_files: list[Path] = []
    member_names: list[str] = []
    with zipfile.ZipFile(source_zip, "r") as zip_handle:
        members = [m for m in zip_handle.infolist() if not m.is_dir()]
        member_names = [m.filename for m in members]
        zip_handle.extractall(extraction_root)
    for path in extraction_root.rglob("*"):
        if path.is_file():
            extracted_files.append(path)
    return extraction_root, extracted_files, member_names


def locate_expected_artifacts(extracted_files: list[Path]) -> tuple[dict[str, Path], list[str], list[str]]:
    by_name: dict[str, list[Path]] = {}
    for file_path in extracted_files:
        by_name.setdefault(file_path.name, []).append(file_path)

    located: dict[str, Path] = {}
    errors: list[str] = []
    warnings: list[str] = []
    expected_names = {spec.file_name for spec in EXPECTED_ARTIFACTS}

    for spec in EXPECTED_ARTIFACTS:
        candidates = by_name.get(spec.file_name, [])
        if not candidates:
            errors.append(f"Falta artefacto esperado: {spec.file_name}")
            continue
        if len(candidates) > 1:
            errors.append(
                f"Artefacto duplicado en staging ({len(candidates)} copias): {spec.file_name}"
            )
            continue
        located[spec.file_name] = candidates[0]

    extras = sorted(name for name in by_name if name not in expected_names)
    if extras:
        warnings.append(
            "Se detectaron archivos adicionales no contemplados en el plan: "
            + ", ".join(extras)
        )
    return located, errors, warnings


def build_tree_lines() -> list[str]:
    lines = ["00_sistema_tesis/"]
    for area_name in (
        "01_contexto_canonico",
        "02_evidencia",
        "03_metadatos",
        "04_politicas_y_gobernanza",
        "05_registros_de_ingestion",
        "06_historico_de_paquetes",
    ):
        area_path = AREAS[area_name]
        lines.append(f"  {area_name}/")
        if area_path.exists():
            files = sorted(p.name for p in area_path.iterdir() if p.is_file())
            for file_name in files:
                lines.append(f"    {file_name}")
    return lines


def write_or_append_index(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "archivo",
        "ruta_origen",
        "ruta_destino",
        "rol",
        "prioridad",
        "hash_sha256",
        "estado_verificacion",
        "tipo_fuente",
        "dependencias",
        "paquete",
        "version_paquete",
        "version_artefacto",
        "fecha_ingestion",
    ]
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    exists = INDEX_PATH.exists()
    with INDEX_PATH.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, str]]) -> str:
    headers = [
        "archivo",
        "ruta_origen",
        "ruta_destino",
        "rol",
        "prioridad",
        "hash_sha256",
        "estado_verificacion",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row.get(header, "") for header in headers) + " |")
    return "\n".join(lines)


def backup_existing_file(target: Path, stamp: str) -> Path:
    backup_path = target.parent / f"{target.name}.{stamp}.bak"
    shutil.copy2(target, backup_path)
    return backup_path


def archive_source_zip(source_zip: Path, package_version: str, date_stamp: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    version_suffix = package_version if package_version != "desconocida" else "vNA"
    target_dir = AREAS["06_historico_de_paquetes"] / f"{date_stamp}_{version_suffix}"
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_path = target_dir / source_zip.name

    if archive_path.exists():
        existing_hash = sha256_path(archive_path)
        source_hash = sha256_path(source_zip)
        if existing_hash == source_hash:
            warnings.append(f"ZIP histórico ya existente con hash idéntico: {rel_posix(archive_path)}")
            return rel_posix(archive_path), warnings
        archive_path = target_dir / f"{source_zip.stem}_{now_compact()}{source_zip.suffix}"
        warnings.append(
            "Conflicto de nombre en histórico; se archivó con sufijo timestamp: "
            + rel_posix(archive_path)
        )

    shutil.copy2(source_zip, archive_path)
    return rel_posix(archive_path), warnings


def write_report(
    *,
    report_path: Path,
    package_name: str,
    package_version: str,
    ingest_date_iso: str,
    package_hash: str,
    package_size: int,
    package_file_count: int,
    rows: list[dict[str, str]],
    errors: list[str],
    warnings: list[str],
    decisions: list[str],
) -> None:
    tree_text = "\n".join(build_tree_lines())
    table_text = markdown_table(rows)
    error_lines = "\n".join(f"- {item}" for item in errors) if errors else "- Ninguno."
    warning_lines = "\n".join(f"- {item}" for item in warnings) if warnings else "- Ninguna."
    decision_lines = "\n".join(f"- {item}" for item in decisions)
    next_steps = "\n".join(
        [
            "1. Crear branch/commit firmado del lote de ingestión y revisar diff semántico de cero cambios en contenido canónico.",
            "2. Ejecutar validación cruzada entre `.md`, `.jsonl` y `.sqlite` para detectar divergencias internas de contexto.",
            "3. Vincular el contexto canónico recién ingerido al flujo de redacción nueva del manuscrito desde cero.",
            "4. Integrar referencias de evidencia experimental futuras contra `02_evidencia/` y el índice maestro.",
            "5. Definir pipeline de sincronización futura con Overleaf, manteniendo estatus de borrador no canónico hasta nueva decisión formal.",
        ]
    )

    lines = [
        "# Reporte de Ingestión Canónica IoT",
        "",
        "## 1. Resumen ejecutivo",
        f"- Paquete: `{package_name}`",
        f"- Versión de paquete detectada: `{package_version}`",
        f"- Fecha de ingestión: `{ingest_date_iso}`",
        f"- Hash SHA-256 del paquete: `sha256:{package_hash}`",
        f"- Tamaño total del paquete (bytes): `{package_size}`",
        f"- Cantidad de archivos en el ZIP: `{package_file_count}`",
        "- Estado de Overleaf actual: **borrador provisional no canónico**.",
        "",
        "## 2. Árbol de carpetas resultante",
        "```text",
        tree_text,
        "```",
        "",
        "## 3. Tabla de ingestión",
        table_text,
        "",
        "## 4. Hallazgos y riesgos",
        "### Errores encontrados",
        error_lines,
        "",
        "### Advertencias",
        warning_lines,
        "",
        "### Decisiones tomadas",
        decision_lines,
        "",
        "## 5. Siguientes pasos priorizados",
        next_steps,
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    source_zip = Path(args.source).expanduser()
    stamp = now_compact()
    ingest_iso = now_iso()

    if not source_zip.exists() or not source_zip.is_file():
        print(f"[ERROR] No existe el ZIP fuente: {source_zip}")
        return 1

    ensure_area_structure()

    package_hash = sha256_path(source_zip)
    package_name = source_zip.name
    package_size = source_zip.stat().st_size
    package_version = parse_zip_version(package_name)
    date_stamp = datetime.now().strftime("%Y-%m-%d")

    staging_dir, extracted_files, member_names = extract_zip_to_staging(source_zip, stamp)
    located, errors, warnings = locate_expected_artifacts(extracted_files)

    package_file_count = len(member_names)
    if package_version == "v10":
        warnings.append("Consistencia registrada: contenedor ZIP v10 con artefactos internos v09 (advertencia no fatal).")

    rows: list[dict[str, str]] = []
    decisions: list[str] = [
        "Se respetaron nombres originales de artefactos (sin renombrado).",
        "Se realizó extracción en staging aislado antes de cualquier copia operativa.",
        "Se clasificó Overleaf actual como borrador provisional no canónico.",
    ]

    backups_created: list[str] = []

    for spec in EXPECTED_ARTIFACTS:
        origin = located.get(spec.file_name)
        if origin is None:
            continue
        version_artifact = parse_artifact_version(spec.file_name)
        destination = AREAS[spec.area] / spec.file_name
        file_hash = sha256_path(origin)
        status = "verificado"

        if version_artifact != spec.expected_version:
            warnings.append(
                f"Versión inesperada en artefacto {spec.file_name}: detectada {version_artifact}, esperada {spec.expected_version}."
            )

        if args.mode == "apply":
            if destination.exists():
                backup = backup_existing_file(destination, stamp)
                backups_created.append(rel_posix(backup))
            shutil.copy2(origin, destination)

        rows.append(
            {
                "archivo": spec.file_name,
                "ruta_origen": str(origin.resolve()),
                "ruta_destino": rel_posix(destination),
                "rol": spec.role,
                "prioridad": spec.priority,
                "hash_sha256": f"sha256:{file_hash}",
                "estado_verificacion": status,
                "tipo_fuente": spec.source_type,
                "dependencias": spec.dependencies,
                "paquete": package_name,
                "version_paquete": package_version,
                "version_artefacto": version_artifact,
                "fecha_ingestion": ingest_iso,
            }
        )

    if args.mode == "apply" and not errors:
        archived_path, archive_warnings = archive_source_zip(source_zip, package_version, date_stamp)
        warnings.extend(archive_warnings)
        decisions.append(f"ZIP fuente archivado en histórico: {archived_path}")
        if backups_created:
            decisions.append("Se creó respaldo .bak antes de sobrescrituras: " + "; ".join(backups_created))
        write_or_append_index(rows)

    report_path = AREAS["05_registros_de_ingestion"] / f"reporte_ingestion_{stamp}.md"
    write_report(
        report_path=report_path,
        package_name=package_name,
        package_version=package_version,
        ingest_date_iso=ingest_iso,
        package_hash=package_hash,
        package_size=package_size,
        package_file_count=package_file_count,
        rows=rows,
        errors=errors,
        warnings=warnings,
        decisions=decisions,
    )

    summary = {
        "mode": args.mode,
        "source_zip": str(source_zip),
        "staging_dir": str(staging_dir),
        "package_name": package_name,
        "package_version": package_version,
        "package_sha256": f"sha256:{package_hash}",
        "package_size_bytes": package_size,
        "zip_file_count": package_file_count,
        "ingest_date": ingest_iso,
        "rows": len(rows),
        "errors": errors,
        "warnings": warnings,
        "report_path": rel_posix(report_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        print("[ERROR] Ingestión incompleta por inconsistencias.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
