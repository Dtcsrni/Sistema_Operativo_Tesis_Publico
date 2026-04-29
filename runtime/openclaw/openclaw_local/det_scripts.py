"""det_scripts.py — Cálculos determinísticos sin inferencia LLM.

Política R6 (token-efficiency-policy.md):
  Los datos y cálculos determinísticos se ejecutan aquí (sin LLM),
  ahorrando 100% de los tokens que consumiría una inferencia completa.

Handlers incluidos:
  - Aritmética básica (eval seguro)
  - Estadísticas descriptivas (media, mediana, moda, desv. estándar)
  - Conversiones de unidades (peso, temperatura, longitud, volumen, velocidad)
  - Fecha/hora local y UTC
  - Delegación a scripts Python del SO (07_scripts/)

Cada handler retorna dict[str, Any] | None.
None = no reconoció el patrón → pasar a inferencia LLM.
"""
from __future__ import annotations

import ast
import math
import operator
import os
import re
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Aritmética segura ─────────────────────────────────────────────────────────
_SAFE_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_MATH_FUNCS: dict[str, Any] = {
    "sqrt": math.sqrt,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node: ast.expr) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in _MATH_FUNCS:
        val = _MATH_FUNCS[node.id]
        if isinstance(val, float):
            return val
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _MATH_FUNCS:
            func = _MATH_FUNCS[node.func.id]
            if callable(func):
                args = [_safe_eval(a) for a in node.args]
                return float(func(*args))
    raise ValueError(f"Operación no permitida: {ast.dump(node)}")


_MATH_PATTERN = re.compile(
    r"^[\d\s\+\-\*\/\%\^\(\)\.\,sqrt\slog\ssin\scos\stan\sabs\sround\sceil\sfloor\sfactorial\spi\se]+$",
    re.IGNORECASE,
)

_CALC_TRIGGERS = re.compile(
    r"\b(cu[aá]nto\s+es|calcula|calcula\s+me|resultado\s+de|cu[aá]nto\s+da|"
    r"cu[aá]nto\s+son|resuelve|eval[uú]a|computa)\b",
    re.IGNORECASE,
)

_EXPR_EXTRACT = re.compile(
    r"([\d][\d\s\+\-\*\/\%\^\(\)\.]*(?:sqrt|log|sin|cos|tan|abs|round|ceil|floor|factorial|pi|e)?[\d\s\(\)\.]*)",
    re.IGNORECASE,
)


def arithmetic_response(text: str) -> dict[str, Any] | None:
    """Evalúa expresiones matemáticas sin LLM."""
    lowered = text.strip().lower()
    # Detectar trigger de cálculo
    has_trigger = bool(_CALC_TRIGGERS.search(lowered))
    # Detectar expresión directa (ej: "3 * 7 + 2")
    cleaned = re.sub(r"[\s]", " ", lowered)
    # Intentar extraer expresión
    expr_raw = ""
    if has_trigger:
        m = re.search(r"[\d\(\-][\d\s\+\-\*\/\%\^\(\)\.sqrtloginscoabcoundreilfacop]+", cleaned)
        if m:
            expr_raw = m.group(0).strip()
    elif re.fullmatch(r"[\d\s\+\-\*\/\%\^\(\)\.]+", cleaned.replace("x", "*").replace("×", "*").replace("÷", "/")):
        expr_raw = cleaned.replace("x", "*").replace("×", "*").replace("÷", "/")
    if not expr_raw:
        return None
    expr_raw = expr_raw.replace(",", ".").replace("^", "**").strip()
    if not expr_raw:
        return None
    try:
        tree = ast.parse(expr_raw, mode="eval")
        result = _safe_eval(tree.body)
    except Exception:
        return None
    # Formatear resultado
    if isinstance(result, float) and result.is_integer() and abs(result) < 1e15:
        formatted = str(int(result))
    else:
        formatted = f"{result:,.6g}"
    return {
        "status": "ok",
        "text": f"🔢 Resultado: <b>{formatted}</b>\n<i>Expresión: {expr_raw}</i>",
        "model": "deterministic:arithmetic",
    }


# ── Estadísticas descriptivas ─────────────────────────────────────────────────
_STATS_TRIGGER = re.compile(
    r"\b(media|promedio|mediana|moda|desviaci[oó]n\s+est[aá]ndar|varianza|m[aá]ximo|m[ií]nimo|rango)\b",
    re.IGNORECASE,
)
_NUMBER_LIST = re.compile(r"-?\d+(?:[.,]\d+)?(?:\s*[,;\s]\s*-?\d+(?:[.,]\d+)?)+")


def statistics_response(text: str) -> dict[str, Any] | None:
    """Calcula estadísticas descriptivas de una lista de números."""
    if not _STATS_TRIGGER.search(text):
        return None
    m = _NUMBER_LIST.search(text)
    if not m:
        return None
    raw_nums = re.findall(r"-?\d+(?:[.,]\d+)?", m.group(0))
    try:
        nums = [float(n.replace(",", ".")) for n in raw_nums]
    except ValueError:
        return None
    if len(nums) < 2:
        return None
    lines = [f"📊 Estadísticas de: <code>{', '.join(str(n) for n in nums)}</code>"]
    lines.append(f"• Media: <b>{statistics.mean(nums):.4g}</b>")
    lines.append(f"• Mediana: <b>{statistics.median(nums):.4g}</b>")
    if len(nums) >= 2:
        lines.append(f"• Desv. estándar: <b>{statistics.stdev(nums):.4g}</b>")
        lines.append(f"• Varianza: <b>{statistics.variance(nums):.4g}</b>")
    lines.append(f"• Máximo: <b>{max(nums):.4g}</b>  Mínimo: <b>{min(nums):.4g}</b>")
    lines.append(f"• Rango: <b>{max(nums) - min(nums):.4g}</b>  N: <b>{len(nums)}</b>")
    try:
        moda = statistics.mode(nums)
        lines.append(f"• Moda: <b>{moda:.4g}</b>")
    except statistics.StatisticsError:
        pass
    return {"status": "ok", "text": "\n".join(lines), "model": "deterministic:statistics"}


# ── Conversiones de unidades ──────────────────────────────────────────────────
_UNIT_CONVERSIONS: dict[str, tuple[set[str], set[str], float, str, str]] = {
    # (from_aliases, to_aliases, factor, from_label, to_label)
    "lb_kg":   ({"lb", "lbs", "libra", "libras", "pound", "pounds"}, {"kg", "kilo", "kilos", "kilogramo", "kilogramos"}, 0.45359237, "lb", "kg"),
    "kg_lb":   ({"kg", "kilo", "kilos", "kilogramo", "kilogramos"}, {"lb", "lbs", "libra", "libras", "pound", "pounds"}, 2.20462262, "kg", "lb"),
    "km_mi":   ({"km", "kilómetro", "kilómetros", "kilometro", "kilometros"}, {"mi", "milla", "millas", "mile", "miles"}, 0.62137119, "km", "mi"),
    "mi_km":   ({"mi", "milla", "millas", "mile", "miles"}, {"km", "kilómetro", "kilómetros"}, 1.60934400, "mi", "km"),
    "m_ft":    ({"m", "metro", "metros", "meter", "meters"}, {"ft", "pie", "pies", "foot", "feet"}, 3.28084, "m", "ft"),
    "ft_m":    ({"ft", "pie", "pies", "foot", "feet"}, {"m", "metro", "metros"}, 0.3048, "ft", "m"),
    "cm_in":   ({"cm", "centímetro", "centimetro", "centímetros", "centimetros"}, {"in", "pulgada", "pulgadas", "inch", "inches"}, 0.393701, "cm", "in"),
    "in_cm":   ({"in", "pulgada", "pulgadas", "inch", "inches"}, {"cm", "centímetro", "centimetros"}, 2.54, "in", "cm"),
    "l_gal":   ({"l", "litro", "litros", "liter", "liters"}, {"gal", "galón", "galones", "gallon", "gallons"}, 0.264172, "L", "gal"),
    "gal_l":   ({"gal", "galón", "galones", "gallon", "gallons"}, {"l", "litro", "litros"}, 3.785411784, "gal", "L"),
    "kmh_mph": ({"km/h", "kmh", "km\\h"}, {"mph", "mi/h", "millas/h"}, 0.621371, "km/h", "mph"),
    "mph_kmh": ({"mph", "mi/h", "millas/h"}, {"km/h", "kmh"}, 1.60934, "mph", "km/h"),
    "oz_g":    ({"oz", "onza", "onzas", "ounce", "ounces"}, {"g", "gramo", "gramos", "gram", "grams"}, 28.3495, "oz", "g"),
    "g_oz":    ({"g", "gramo", "gramos", "gram", "grams"}, {"oz", "onza", "onzas"}, 0.035274, "g", "oz"),
}

_CONV_PATTERN = re.compile(
    r"(?P<value>-?\d+(?:[.,]\d+)?)\s*(?P<from>[\w/\\áéíóúü]+)\s+(?:a|en|to)\s+(?P<to>[\w/\\áéíóúü]+)",
    re.IGNORECASE,
)


def unit_conversion_response(text: str) -> dict[str, Any] | None:
    """Conversiones de unidades: peso, distancia, volumen, velocidad, masa."""
    normalized = text.lower().strip()
    m = _CONV_PATTERN.search(normalized)
    if not m:
        return None
    raw_val = m.group("value").replace(",", ".")
    from_tok = m.group("from").strip()
    to_tok = m.group("to").strip()
    try:
        value = float(raw_val)
    except ValueError:
        return None
    for key, (from_aliases, to_aliases, factor, from_lbl, to_lbl) in _UNIT_CONVERSIONS.items():
        if from_tok in from_aliases and to_tok in to_aliases:
            result = value * factor
            return {
                "status": "ok",
                "text": (
                    f"📐 Conversión: <b>{value:g} {from_lbl} = {result:.4g} {to_lbl}</b>\n"
                    f"<i>Factor: × {factor}</i>"
                ),
                "model": "deterministic:unit_conversion",
            }
    # Temperatura (requiere offset, no factor puro)
    if from_tok in {"c", "celsius", "°c"} and to_tok in {"f", "fahrenheit", "°f"}:
        result = value * 9 / 5 + 32
        return {"status": "ok", "text": f"🌡️ <b>{value}°C = {result:.2f}°F</b>\n<i>Fórmula: (C × 9/5) + 32</i>", "model": "deterministic:temperature"}
    if from_tok in {"f", "fahrenheit", "°f"} and to_tok in {"c", "celsius", "°c"}:
        result = (value - 32) * 5 / 9
        return {"status": "ok", "text": f"🌡️ <b>{value}°F = {result:.2f}°C</b>\n<i>Fórmula: (F − 32) × 5/9</i>", "model": "deterministic:temperature"}
    if from_tok in {"k", "kelvin"} and to_tok in {"c", "celsius", "°c"}:
        result = value - 273.15
        return {"status": "ok", "text": f"🌡️ <b>{value} K = {result:.2f}°C</b>", "model": "deterministic:temperature"}
    if from_tok in {"c", "celsius", "°c"} and to_tok in {"k", "kelvin"}:
        result = value + 273.15
        return {"status": "ok", "text": f"🌡️ <b>{value}°C = {result:.2f} K</b>", "model": "deterministic:temperature"}
    return None


# ── Fecha y hora ──────────────────────────────────────────────────────────────
_TIME_PATTERN = re.compile(
    r"\b(qu[eé]\s+hora|hora\s+actual|hora\s+es|d[ií]a\s+es|fecha\s+actual|fecha\s+y\s+hora|utc|zona\s+horaria)\b",
    re.IGNORECASE,
)


def datetime_response(text: str) -> dict[str, Any] | None:
    """Responde preguntas de hora/fecha sin LLM."""
    if not _TIME_PATTERN.search(text):
        return None
    now_local = datetime.now().astimezone()
    now_utc = datetime.now(timezone.utc)
    tz_name = now_local.strftime("%Z") or "local"
    lines = [
        f"🕐 <b>Hora local ({tz_name}):</b> {now_local.strftime('%H:%M:%S')}",
        f"📅 <b>Fecha:</b> {now_local.strftime('%A %d de %B de %Y')}",
        f"🌐 <b>UTC:</b> {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC",
    ]
    return {"status": "ok", "text": "\n".join(lines), "model": "deterministic:datetime"}


# ── Delegación a scripts del SO ───────────────────────────────────────────────
_SCRIPT_TRIGGER = re.compile(
    r"\b(ejecuta\s+script|corre\s+script|lanza\s+script|run\s+script|"
    r"check_serena|build_all|build_memory|validate_structure|token_usage|"
    r"openclaw_status|validate_memory)\b",
    re.IGNORECASE,
)

_ALLOWED_SCRIPTS: dict[str, str] = {
    "check_serena_access":    "07_scripts/check_serena_access.py",
    "check_serena":           "07_scripts/check_serena_access.py",
    "build_memory":           "07_scripts/build_memory.py",
    "build_openclaw_status":  "07_scripts/build_openclaw_status.py",
    "token_usage":            "07_scripts/build_token_usage_snapshot.py",
    "token_snapshot":         "07_scripts/build_token_usage_snapshot.py",
    "validate_memory":        "07_scripts/validate_memory.py",
    "validate_structure":     "07_scripts/validate_structure.py",
    "report_consistency":     "07_scripts/report_consistency.py",
}

_SCRIPT_NAME_EXTRACT = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _ALLOWED_SCRIPTS) + r")\b",
    re.IGNORECASE,
)


def edge_script_response(text: str, *, repo_root: Path) -> dict[str, Any] | None:
    """Delega ejecución de scripts de solo-lectura del SO al intérprete Python edge."""
    if not _SCRIPT_TRIGGER.search(text):
        return None
    m = _SCRIPT_NAME_EXTRACT.search(text.lower())
    if not m:
        return None
    script_key = m.group(1).lower()
    script_rel = _ALLOWED_SCRIPTS.get(script_key)
    if not script_rel:
        return None
    script_path = repo_root / script_rel
    if not script_path.exists():
        return {
            "status": "error",
            "text": f"⚠️ Script no encontrado: <code>{script_rel}</code>",
            "model": "deterministic:edge_script",
        }
    timeout = int(os.getenv("OPENCLAW_DET_SCRIPT_TIMEOUT", "30"))
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(repo_root),
        )
        output = (result.stdout or result.stderr or "sin salida").strip()[:800]
        status = "ok" if result.returncode == 0 else "degraded"
        icon = "✅" if result.returncode == 0 else "⚠️"
        return {
            "status": status,
            "text": f"{icon} <b>{script_key}</b> (rc={result.returncode}):\n<code>{output}</code>",
            "model": "deterministic:edge_script",
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "text": f"⏱️ Script <code>{script_key}</code> superó el timeout de {timeout}s.", "model": "deterministic:edge_script"}
    except Exception as exc:
        return {"status": "error", "text": f"❌ Error al ejecutar <code>{script_key}</code>: {exc}", "model": "deterministic:edge_script"}


# ── Dispatcher principal ──────────────────────────────────────────────────────
def dispatch(text: str, *, repo_root: Path) -> dict[str, Any] | None:
    """Intenta resolver el texto con handlers determinísticos en orden de prioridad.

    Retorna dict si algún handler reconoció el patrón, None si debe pasar a LLM.
    """
    for handler in (
        datetime_response,
        unit_conversion_response,
        statistics_response,
        arithmetic_response,
    ):
        result = handler(text)
        if result is not None:
            return result
    return edge_script_response(text, repo_root=repo_root)
