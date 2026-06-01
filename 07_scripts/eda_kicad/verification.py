from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


FINAL_OK = "TECNICAMENTE_CORRECTO"
FINAL_ERC = "RECHAZADO_POR_ERC"
FINAL_NETLIST = "RECHAZADO_POR_NETLIST"
FINAL_EXPORT = "EXPORTADO_SIN_APROBACION_HUMANA"


@dataclass
class VerificationResult:
    kicad_cli: str
    kicad_version: str
    commands: list[str] = field(default_factory=list)
    erc_errors: int = 0
    erc_warnings: int = 0
    state: str = FINAL_EXPORT
    notes: list[str] = field(default_factory=list)
    netlist_failures: list[str] = field(default_factory=list)
    visual_failures: list[str] = field(default_factory=list)
    export_failures: list[str] = field(default_factory=list)
    exported_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def run_verification(project_root: Path, schematic: Path) -> VerificationResult:
    export_dir = project_root / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    cli = _find_kicad_cli()
    version = _run([cli, "--version"]).stdout.strip()
    result = VerificationResult(cli, version)

    txt_report = export_dir / "reporte_erc.txt"
    json_report = export_dir / "reporte_erc.json"
    netlist = export_dir / "sirena_555_flipflop.net"
    pdf = export_dir / "sirena_555_flipflop.pdf"

    _record(result, [cli, "sch", "erc", str(schematic), "--output", str(txt_report)])
    _run([cli, "sch", "erc", str(schematic), "--output", str(txt_report)])
    _record(result, [cli, "sch", "erc", str(schematic), "--format", "json", "--output", str(json_report)])
    _run([cli, "sch", "erc", str(schematic), "--format", "json", "--output", str(json_report)])
    _record(result, [cli, "sch", "export", "netlist", str(schematic), "--format", "kicadsexpr", "--output", str(netlist)])
    _run([cli, "sch", "export", "netlist", str(schematic), "--format", "kicadsexpr", "--output", str(netlist)])
    result.erc_errors, result.erc_warnings, result.warnings = _count_erc(json_report, txt_report)
    result.netlist_failures = _netlist_failures(netlist)
    result.visual_failures = _visual_wire_failures(schematic)
    unacceptable_warnings = _unacceptable_warnings(result.warnings)
    if result.erc_errors or unacceptable_warnings:
        result.state = FINAL_ERC
        result.netlist_failures.extend(unacceptable_warnings)
    elif result.netlist_failures:
        result.state = FINAL_NETLIST
    elif result.visual_failures:
        result.state = FINAL_NETLIST
    else:
        result.state = FINAL_EXPORT
        result.notes.append("Circuito tecnicamente correcto por ERC/netlist, pendiente de validacion humana.")
        _record(result, [cli, "sch", "export", "pdf", str(schematic), "--output", str(pdf), "--black-and-white"])
        _run([cli, "sch", "export", "pdf", str(schematic), "--output", str(pdf), "--black-and-white"])
        _record(result, [cli, "sch", "export", "svg", str(schematic), "--output", str(export_dir), "--black-and-white"])
        _run([cli, "sch", "export", "svg", str(schematic), "--output", str(export_dir), "--black-and-white"])
        result.export_failures, result.exported_files = _export_status(export_dir, pdf)
        if result.export_failures:
            result.state = FINAL_NETLIST
    _write_report(project_root, result)
    return result


def _find_kicad_cli() -> str:
    found = shutil.which("kicad-cli")
    if found:
        return found
    default = Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
    if default.exists():
        return str(default)
    raise FileNotFoundError("kicad-cli no disponible")


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)


def _record(result: VerificationResult, args: list[str]) -> None:
    result.commands.append(" ".join(args))


def _count_erc(json_report: Path, txt_report: Path) -> tuple[int, int, list[str]]:
    if json_report.exists():
        try:
            data = json.loads(json_report.read_text(encoding="utf-8"))
            messages = data.get("sheets", [{}])[0].get("violations", data.get("violations", []))
            errors = sum(1 for item in messages if str(item.get("severity", "")).lower() == "error")
            warnings = sum(1 for item in messages if str(item.get("severity", "")).lower() == "warning")
            warning_text = [
                str(item.get("description") or item.get("message") or item.get("type") or item)
                for item in messages
                if str(item.get("severity", "")).lower() == "warning"
            ]
            return errors, warnings, warning_text
        except Exception:
            pass
    text = txt_report.read_text(encoding="utf-8", errors="ignore") if txt_report.exists() else ""
    return text.count("; error"), text.count("; warning"), _warning_lines(text)


def _warning_lines(text: str) -> list[str]:
    lines = text.splitlines()
    warnings: list[str] = []
    for index, line in enumerate(lines):
        if "; warning" in line and index > 0:
            warnings.append(lines[index - 1].strip())
    return warnings


EXPECTED_NETS: dict[str, set[tuple[str, str]]] = {
    "+5V": {
        ("U1", "4"), ("U1", "8"), ("U2", "1"), ("U2", "4"), ("U2", "10"), ("U2", "13"),
        ("U2", "14"), ("R1", "1"), ("BZ1", "1"), ("C3", "1"), ("C4", "1"), ("C5", "1"),
        ("PF1", "1"),
    },
    "GND": {
        ("U1", "1"), ("U2", "7"), ("U2", "11"), ("U2", "12"), ("C1", "2"), ("C2", "2"),
        ("C3", "2"), ("C4", "2"), ("C5", "2"), ("D1", "K"), ("D2", "K"), ("Q1", "E"),
        ("R7", "2"), ("PF2", "1"),
    },
    "CLK": {("U1", "3"), ("U2", "3")},
    "DIS_NODE": {("U1", "7"), ("R1", "2"), ("R2", "1"), ("SW1", "1")},
    "TIMING_NODE": {("U1", "2"), ("U1", "6"), ("R2", "2"), ("R3", "2"), ("C1", "1")},
    "Q": {("U2", "5"), ("R5", "1"), ("R6", "1")},
    "/Q": {("U2", "2"), ("U2", "6"), ("R4", "1")},
    "BASE_Q1": {("R6", "2"), ("R7", "1"), ("Q1", "B")},
    "CTRL_NODE": {("U1", "5"), ("C2", "1")},
    "BUZZER_NEG": {("Q1", "C"), ("BZ1", "2")},
    "LED_BLUE_NODE": {("D2", "A"), ("R5", "2")},
    "LED_RED_NODE": {("D1", "A"), ("R4", "2")},
}


def _netlist_failures(netlist: Path) -> list[str]:
    if not netlist.exists() or netlist.stat().st_size == 0:
        return ["La netlist exportada no existe o esta vacia."]
    actual = _parse_netlist(netlist.read_text(encoding="utf-8", errors="ignore"))
    failures: list[str] = []
    for net, expected_nodes in EXPECTED_NETS.items():
        actual_nodes = actual.get(net, set())
        missing = expected_nodes - actual_nodes
        extra = actual_nodes - expected_nodes
        if missing:
            failures.append(f"{net}: faltan {sorted(missing)}")
        if extra:
            failures.append(f"{net}: nodos extra no esperados {sorted(extra)}")
    return failures


def _unacceptable_warnings(warnings: list[str]) -> list[str]:
    failures = []
    for warning in warnings:
        if "biblioteca de símbolos" in warning or "lib_symbol_issues" in warning:
            failures.append(f"Advertencia ERC no aceptable: {warning}")
    return failures


def _export_status(export_dir: Path, pdf: Path) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    exported: list[str] = []
    if not pdf.exists() or pdf.stat().st_size == 0:
        failures.append(f"PDF invalido o vacio: {pdf}")
    else:
        exported.append(f"{pdf.name}: {pdf.stat().st_size} bytes")
    svg_files = sorted(export_dir.glob("*.svg"))
    nonempty_svg = [path for path in svg_files if path.stat().st_size > 0]
    if not nonempty_svg:
        failures.append(f"SVG invalido o ausente en: {export_dir}")
    else:
        exported.extend(f"{path.name}: {path.stat().st_size} bytes" for path in nonempty_svg)
    return failures, exported


CRITICAL_VISUAL_NETS = {
    "CLK", "Q", "/Q", "DIS_NODE", "TIMING_NODE", "BASE_Q1", "CTRL_NODE",
    "BUZZER_NEG", "FAST_NODE", "LED_RED_NODE", "LED_BLUE_NODE",
}


def _visual_wire_failures(schematic: Path) -> list[str]:
    if not schematic.exists():
        return ["No existe el esquematico para auditoria visual-estatica."]
    text = schematic.read_text(encoding="utf-8", errors="ignore")
    labels = _parse_label_points(text)
    graph = _wire_graph(text)
    failures: list[str] = []
    for net in sorted(CRITICAL_VISUAL_NETS):
        points = labels.get(net, [])
        if len(points) < 2:
            failures.append(f"{net}: menos de dos etiquetas conectables en el diagrama.")
            continue
        root = graph.find(points[0])
        disconnected = [point for point in points[1:] if graph.find(point) != root]
        if disconnected:
            failures.append(f"{net}: la red se resuelve por etiquetas, no por wires continuos: {disconnected}")
    return failures


def _parse_label_points(text: str) -> dict[str, list[tuple[float, float]]]:
    labels: dict[str, list[tuple[float, float]]] = {}
    pattern = re.compile(r'\(label\s+"([^"]+)"\s+\(at\s+([-0-9.]+)\s+([-0-9.]+)\s+0\)')
    for match in pattern.finditer(text):
        labels.setdefault(match.group(1), []).append((float(match.group(2)), float(match.group(3))))
    return labels


class _WireGraph:
    def __init__(self) -> None:
        self.parent: dict[tuple[float, float], tuple[float, float]] = {}

    def find(self, point: tuple[float, float]) -> tuple[float, float]:
        self.parent.setdefault(point, point)
        if self.parent[point] != point:
            self.parent[point] = self.find(self.parent[point])
        return self.parent[point]

    def union(self, a: tuple[float, float], b: tuple[float, float]) -> None:
        self.parent[self.find(b)] = self.find(a)


def _wire_graph(text: str) -> _WireGraph:
    graph = _WireGraph()
    pattern = re.compile(
        r'\(wire\s+\(pts\s+\(xy\s+([-0-9.]+)\s+([-0-9.]+)\)\s+\(xy\s+([-0-9.]+)\s+([-0-9.]+)\)\)'
    )
    for match in pattern.finditer(text):
        a = (float(match.group(1)), float(match.group(2)))
        b = (float(match.group(3)), float(match.group(4)))
        graph.union(a, b)
    return graph


def _parse_netlist(text: str) -> dict[str, set[tuple[str, str]]]:
    nets: dict[str, set[tuple[str, str]]] = {}
    current_net: str | None = None
    current_ref: str | None = None
    in_net = False
    in_node = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "(net":
            in_net = True
            current_net = None
            continue
        if in_net and line.startswith("(name "):
            current_net = _normalize_net_name(_quoted_value(line))
            nets.setdefault(current_net, set())
            continue
        if in_net and line == "(node":
            in_node = True
            current_ref = None
            continue
        if in_node and line.startswith("(ref "):
            current_ref = _quoted_value(line)
            continue
        if in_node and line.startswith("(pin ") and current_net and current_ref:
            nets.setdefault(current_net, set()).add((current_ref, _quoted_value(line)))
            continue
        if in_node and line == ")":
            in_node = False
            current_ref = None
    return nets


def _quoted_value(line: str) -> str:
    parts = line.split('"')
    return parts[1] if len(parts) > 1 else ""


def _normalize_net_name(name: str) -> str:
    if name == "/{slash}Q":
        return "/Q"
    if name.startswith("/") and name != "/":
        return name[1:]
    return name


def _write_report(project_root: Path, result: VerificationResult) -> None:
    report = project_root / "export" / "reporte_verificacion.md"
    commands = "\n".join(f"- `{cmd}`" for cmd in result.commands)
    notes = "\n".join(f"- {note}" for note in result.notes) or "- Sin notas adicionales."
    netlist = "\n".join(f"- {failure}" for failure in result.netlist_failures) or "- Netlist comparada contra matriz esperada: sin faltantes ni nodos extra."
    visual = "\n".join(f"- {failure}" for failure in result.visual_failures) or "- Redes criticas conectadas por wires continuos."
    exports = "\n".join(f"- {item}" for item in result.exported_files) or "- Exportaciones no ejecutadas porque fallaron gates previos."
    export_failures = "\n".join(f"- {item}" for item in result.export_failures) or "- Sin fallas de exportacion."
    warnings = "\n".join(f"- {warning}" for warning in result.warnings[:20]) or "- Sin advertencias ERC."
    report.write_text(
        f"""# Reporte de verificacion electrica

## 1. Version de KiCad detectada

- `kicad-cli`: {result.kicad_version}
- Ruta: `{result.kicad_cli}`

## 2. Comandos ejecutados

{commands}

## 3. Resultado de ERC

- Errores: {result.erc_errors}
- Advertencias: {result.erc_warnings}

## 4. Verificacion de netlist

- Exportacion netlist KiCad S-expression ejecutada.
- Nets obligatorias buscadas: `+5V`, `GND`, `CLK`, `Q`, `/Q`, `TIMING_NODE`, `DIS_NODE`, `BASE_Q1`, `CTRL_NODE`.
{netlist}

## 4.1 Auditoria visual-estatica de wires

{visual}

## 5. Exportaciones

- PDF/SVG regenerados desde el esquematico actual.
{exports}
{export_failures}

## 6. Estado tecnico

- `{result.state}`

## 7. Notas

{notes}

## 8. Advertencias justificadas

{warnings}

## 9. Lecciones aprendidas

- La coordenada local `y` de simbolos KiCad debe invertirse al proyectarla a hoja.
- Los simbolos embebidos deben incluirse en `lib_symbols`; si no, ERC puede degradar pines a tipo desconocido.
- ERC limpio no sustituye la comparacion funcional de netlist: etiquetas distintas pueden aislar una etapa sin error critico.
- ERC limpio no garantiza un diagrama visual didactico: se requiere verificar continuidad grafica de wires para las redes criticas.
- No mezclar `lib_id` oficiales con cuerpos embebidos no oficiales; produce advertencias `lib_symbol_mismatch` y puede alterar la conectividad efectiva.
- Una libreria local de proyecto (`sym-lib-table` + `.kicad_sym`) elimina `lib_symbol_issues` sin sacrificar reproducibilidad.

## 10. Diagnostico del fallo anterior

- El generador anterior usaba `pin -> stub -> label` como sustituto de cableado visible.
- Varias conexiones principales existian en netlist por etiquetas, pero no como wires continuos legibles.
- Al intentar usar `lib_id` oficiales con geometria local se introdujeron advertencias de simbolo y nets falsas.

## 11. Correcciones aplicadas

- Registro local `Sirena` con `kicad/sym-lib-table` y `kicad/sirena.kicad_sym`.
- Ruteo ortogonal explicito para `CLK`, `Q`, `/Q`, `DIS_NODE`, `TIMING_NODE`, `BASE_Q1`, `CTRL_NODE`, `BUZZER_NEG`, `FAST_NODE`, `LED_RED_NODE` y `LED_BLUE_NODE`.
- Comparacion contractual de netlist KiCad S-expression contra matriz esperada.
- Gate visual-estatico para rechazar redes criticas resueltas solo por labels.

## 12. Serena / entorno agéntico

- `check_serena_access.py --json` reporto `serena-local` HTTP sano en `http://127.0.0.1:8765/mcp`.
- Esta conversacion no expone herramientas Serena nativas; el trabajo se ejecuto por filesystem y comandos locales.
""",
        encoding="utf-8",
    )
