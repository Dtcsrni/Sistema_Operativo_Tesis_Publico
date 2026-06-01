from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .geometry import Point


LOCAL_LIBRARY = "Sirena"


@dataclass(frozen=True)
class PinDef:
    name: str
    number: str
    point: Point
    kind: str = "passive"


@dataclass(frozen=True)
class SymbolDef:
    name: str
    pins: dict[str, PinDef]
    body: str

    @property
    def digest(self) -> str:
        return sha256(self.body.encode("utf-8")).hexdigest()


def symbol_library() -> dict[str, SymbolDef]:
    return {
        "NE555": _ne555(),
        "74HC74": _hc74(),
        "R": _two_pin(_local("SIR_R"), "R", "passive"),
        "C": _two_pin(_local("SIR_C"), "C", "passive"),
        "LED": _led(),
        "SW": _two_pin(_local("SIR_SW_Push"), "SW", "passive"),
        "NPN": _npn(),
        "BUZZER": _buzzer(),
        "PWR_FLAG": _pwr_flag(),
    }


def kicad_symbol_library_text() -> str:
    bodies = []
    for symbol in symbol_library().values():
        bodies.append(_library_symbol_body(symbol.body))
    return (
        "(kicad_symbol_lib\n"
        "  (version 20250114)\n"
        '  (generator "eda_kicad")\n'
        '  (generator_version "1.0")\n'
        + "\n".join(bodies)
        + "\n)\n"
    )


def _local(name: str) -> str:
    return f"{LOCAL_LIBRARY}:{name}"


def _library_symbol_body(body: str) -> str:
    return body.replace(f'(symbol "{LOCAL_LIBRARY}:', '(symbol "')


def _pin(number: str, name: str, x: float, y: float, angle: int, kind: str = "passive") -> str:
    return (
        f'(pin {kind} line (at {x} {y} {angle}) (length 2.54) '
        f'(name "{name}" (effects (font (size 1.27 1.27)))) '
        f'(number "{number}" (effects (font (size 1.27 1.27)))))'
    )


def _symbol(name: str, ref: str, value: str, pins: list[str], graphics: str) -> str:
    child_name = name.split(":")[-1]
    return f'''(symbol "{name}" (in_bom yes) (on_board yes)
  (property "Reference" "{ref}" (at 0 -10.16 0) (effects (font (size 1.27 1.27))))
  (property "Value" "{value}" (at 0 10.16 0) (effects (font (size 1.27 1.27))))
  (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
  (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
  (symbol "{child_name}_0_1" {graphics})
  (symbol "{child_name}_1_1" {' '.join(pins)})
)'''


def _two_pin(name: str, ref: str, kind: str) -> SymbolDef:
    pins = {
        "1": PinDef("1", "1", Point(-5.08, 0), kind),
        "2": PinDef("2", "2", Point(5.08, 0), kind),
    }
    body = _symbol(
        name,
        ref,
        ref,
        [_pin("1", "1", -5.08, 0, 0, kind), _pin("2", "2", 5.08, 0, 180, kind)],
        '(rectangle (start -2.54 1.27) (end 2.54 -1.27) (stroke (width 0.254) (type default)) (fill (type none)))',
    )
    return SymbolDef(name, pins, body)


def _ne555() -> SymbolDef:
    coords = {
        "1": ("GND", -10.16, 7.62, 0, "power_in"),
        "2": ("TRIG", -10.16, 5.08, 0, "input"),
        "6": ("THR", -10.16, 2.54, 0, "input"),
        "7": ("DIS", -10.16, 0, 0, "input"),
        "4": ("RESET", -10.16, -2.54, 0, "input"),
        "5": ("CTRL", 0, -10.16, 90, "passive"),
        "3": ("OUT", 10.16, 0, 180, "output"),
        "8": ("VCC", 10.16, 7.62, 180, "power_in"),
    }
    pins = {num: PinDef(name, num, Point(x, y), kind) for num, (name, x, y, _angle, kind) in coords.items()}
    body = _symbol(
        _local("SIR_NE555P"),
        "U",
        "NE555",
        [_pin(num, name, x, y, angle, kind) for num, (name, x, y, angle, kind) in coords.items()],
        '(rectangle (start -7.62 8.89) (end 7.62 -8.89) (stroke (width 0.254) (type default)) (fill (type background)))',
    )
    return SymbolDef(_local("SIR_NE555P"), pins, body)


def _hc74() -> SymbolDef:
    coords = {
        "1": ("~CLR1", -17.78, 10.16, 0, "input"), "2": ("D1", -17.78, 5.08, 0, "input"),
        "3": ("CLK1", -17.78, 0, 0, "input"), "4": ("~PRE1", -17.78, -5.08, 0, "input"),
        "5": ("Q1", 17.78, 5.08, 180, "output"), "6": ("~Q1", 17.78, 0, 180, "output"),
        "7": ("GND", 0, -17.78, 90, "power_in"), "8": ("~Q2", 17.78, -5.08, 180, "output"),
        "9": ("Q2", 17.78, -10.16, 180, "output"), "10": ("~PRE2", -17.78, -10.16, 0, "input"),
        "11": ("CLK2", -17.78, -15.24, 0, "input"), "12": ("D2", -17.78, -20.32, 0, "input"),
        "13": ("~CLR2", -17.78, -25.4, 0, "input"), "14": ("VCC", 0, 15.24, 270, "power_in"),
    }
    pins = {num: PinDef(name, num, Point(x, y), kind) for num, (name, x, y, _angle, kind) in coords.items()}
    body = _symbol(
        _local("SIR_74HC74"),
        "U",
        "74HC74",
        [_pin(num, name, x, y, angle, kind) for num, (name, x, y, angle, kind) in coords.items()],
        '(rectangle (start -15.24 13.97) (end 15.24 -27.94) (stroke (width 0.254) (type default)) (fill (type background)))',
    )
    return SymbolDef(_local("SIR_74HC74"), pins, body)


def _led() -> SymbolDef:
    pins = {"A": PinDef("A", "A", Point(-5.08, 0)), "K": PinDef("K", "K", Point(5.08, 0))}
    body = _symbol(
        _local("SIR_LED"),
        "D",
        "LED",
        [_pin("A", "A", -5.08, 0, 0), _pin("K", "K", 5.08, 0, 180)],
        '(polyline (pts (xy -1.27 2.54) (xy -1.27 -2.54) (xy 2.54 0) (xy -1.27 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))',
    )
    return SymbolDef(_local("SIR_LED"), pins, body)


def _npn() -> SymbolDef:
    pins = {
        "B": PinDef("B", "B", Point(-7.62, 0), "input"),
        "C": PinDef("C", "C", Point(5.08, 5.08)),
        "E": PinDef("E", "E", Point(5.08, -5.08)),
    }
    body = _symbol(
        _local("SIR_BC547"),
        "Q",
        "NPN",
        [_pin("B", "B", -7.62, 0, 0, "input"), _pin("C", "C", 5.08, 5.08, 270), _pin("E", "E", 5.08, -5.08, 90)],
        '(circle (center 0 0) (radius 3.81) (stroke (width 0.254) (type default)) (fill (type none)))',
    )
    return SymbolDef(_local("SIR_BC547"), pins, body)


def _buzzer() -> SymbolDef:
    pins = {"+": PinDef("+", "1", Point(-5.08, -2.54)), "-": PinDef("-", "2", Point(-5.08, 2.54))}
    body = _symbol(
        _local("SIR_Buzzer"),
        "BZ",
        "Buzzer",
        [_pin("1", "+", -5.08, -2.54, 0), _pin("2", "-", -5.08, 2.54, 0)],
        '(circle (center 1.27 0) (radius 3.81) (stroke (width 0.254) (type default)) (fill (type none)))',
    )
    return SymbolDef(_local("SIR_Buzzer"), pins, body)


def _pwr_flag() -> SymbolDef:
    pins = {"1": PinDef("PWR", "1", Point(0, 0), "power_out")}
    body = _symbol(
        _local("SIR_PWR_FLAG"),
        "#FLG",
        "PWR_FLAG",
        [_pin("1", "PWR", 0, 0, 0, "power_out")],
        '(polyline (pts (xy 0 0) (xy 0 -2.54) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))',
    )
    return SymbolDef(_local("SIR_PWR_FLAG"), pins, body)
