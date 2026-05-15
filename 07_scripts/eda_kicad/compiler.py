from __future__ import annotations

import json
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from collections import Counter, defaultdict

from kiutils.schematic import Schematic

from .geometry import Point, mm, snap_point
from .spec import CircuitSpec
from .symbols import SymbolDef, symbol_library


@dataclass(frozen=True)
class Placement:
    symbol_key: str
    at: Point

    def pin_point(self, pin: Point) -> Point:
        # KiCad symbol-local Y grows upward; sheet coordinates grow downward.
        return snap_point(Point(self.at.x + pin.x, self.at.y - pin.y))


def compile_schematic(spec: CircuitSpec, output: Path) -> None:
    symbols = symbol_library()
    placements = _placements()
    project_uuid = str(uuid.uuid4())
    text = _schematic_text(spec, symbols, placements, project_uuid)
    # Roundtrip parse before writing the final artifact.
    with tempfile.NamedTemporaryFile("w", suffix=".kicad_sch", delete=False, encoding="utf-8") as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    Schematic.from_file(str(tmp_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def _schematic_text(
    spec: CircuitSpec,
    symbols: dict[str, SymbolDef],
    placements: dict[str, Placement],
    project_uuid: str,
) -> str:
    used_symbol_keys = sorted({placement.symbol_key for placement in placements.values()} | {"PWR_FLAG"})
    lib_symbols = "\n".join(_indent(symbols[key].body, "    ") for key in used_symbol_keys)
    symbol_blocks = []
    wire_blocks = []
    label_blocks = []
    no_connects = []
    label_points_by_net: dict[str, list[Point]] = defaultdict(list)

    refs = spec.by_ref()
    by_ref_pin = {(conn.component, conn.pin): conn.net for conn in spec.connections}

    for ref, placement in placements.items():
        component = refs.get(ref)
        value = component.value if component else ref
        symbol = symbols[placement.symbol_key]
        symbol_blocks.append(_symbol_instance(symbol.name, ref, value, placement.at, project_uuid, symbol))
        for pin_name, pin in symbol.pins.items():
            net = by_ref_pin.get((ref, pin_name))
            if net is None:
                if ref == "U2" and pin_name in {"8", "9"}:
                    no_connects.append(_no_connect(placement.pin_point(pin.point)))
                continue
            pin_point = placement.pin_point(pin.point)
            label_point = _stub_label_point(pin_point, pin.point)
            wire_blocks.append(_wire(pin_point, label_point))
            label_blocks.append(_label(net, label_point))
            label_points_by_net[net].append(label_point)

    # Power flags drive the power nets for ERC.
    for ref, net, point in [
        ("PF1", "+5V", Point(20.32, 15.24)),
        ("PF2", "GND", Point(20.32, 130.81)),
    ]:
        symbol = symbols["PWR_FLAG"]
        symbol_blocks.append(_symbol_instance(symbol.name, ref, "PWR_FLAG", point, project_uuid, symbol))
        label_point = point.shifted(0, 2.54)
        wire_blocks.append(_wire(point, label_point))
        label_blocks.append(_label(net, label_point))
        label_points_by_net[net].append(label_point)

    routed_wires, junctions = _route_visible_nets(label_points_by_net)
    wire_blocks.extend(routed_wires)

    notes = [
        _text("D = /Q", Point(121.92, 17.78)),
        _text("SW1 acelera el reloj", Point(25.4, 121.92)),
        _text("Buzzer activo 5V", Point(210.82, 121.92)),
        _text("BUZZER_CTRL = Q", Point(177.8, 121.92)),
    ]
    return f'''(kicad_sch
  (version 20250114)
  (generator "eda_kicad")
  (generator_version "1.0")
  (uuid "{project_uuid}")
  (paper "A4")
  (title_block
    (title "{spec.name}")
    (date "2026-05-13")
    (comment 1 "{spec.purpose}")
  )
  (lib_symbols
{lib_symbols}
  )
{''.join(notes)}
{''.join(label_blocks)}
{''.join(no_connects)}
{''.join(wire_blocks)}
{''.join(junctions)}
{''.join(symbol_blocks)}
  (sheet_instances
    (path "/" (page "1"))
  )
  (embedded_fonts no)
)
'''


def _placements() -> dict[str, Placement]:
    return {
        "U1": Placement("NE555", Point(55.88, 68.58)),
        "U2": Placement("74HC74", Point(127.0, 68.58)),
        "R1": Placement("R", Point(30.48, 30.48)),
        "R2": Placement("R", Point(30.48, 50.8)),
        "SW1": Placement("SW", Point(30.48, 83.82)),
        "R3": Placement("R", Point(55.88, 83.82)),
        "C1": Placement("C", Point(30.48, 104.14)),
        "C2": Placement("C", Point(30.48, 119.38)),
        "C3": Placement("C", Point(30.48, 15.24)),
        "C4": Placement("C", Point(111.76, 15.24)),
        "C5": Placement("C", Point(76.2, 15.24)),
        "R4": Placement("R", Point(175.26, 43.18)),
        "D1": Placement("LED", Point(200.66, 43.18)),
        "R5": Placement("R", Point(175.26, 63.5)),
        "D2": Placement("LED", Point(200.66, 63.5)),
        "R6": Placement("R", Point(175.26, 91.44)),
        "R7": Placement("R", Point(160.02, 111.76)),
        "Q1": Placement("NPN", Point(200.66, 96.52)),
        "BZ1": Placement("BUZZER", Point(236.22, 91.44)),
    }


def _symbol_instance(lib_id: str, ref: str, value: str, at: Point, project_uuid: str, symbol: SymbolDef) -> str:
    pin_lines = "\n".join(
        f'    (pin "{pin.number}" (uuid "{uuid.uuid4()}"))'
        for pin in symbol.pins.values()
    )
    return f'''  (symbol (lib_id "{lib_id}") (at {mm(at.x)} {mm(at.y)} 0) (unit 1)
    (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced)
    (uuid "{uuid.uuid4()}")
    (property "Reference" "{ref}" (at {mm(at.x)} {mm(at.y - 3.81)} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "{value}" (at {mm(at.x)} {mm(at.y + 3.81)} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" "" (at {mm(at.x)} {mm(at.y)} 0)
      (effects (font (size 1.27 1.27)) (hide yes))
    )
    (property "Datasheet" "~" (at {mm(at.x)} {mm(at.y)} 0)
      (effects (font (size 1.27 1.27)) (hide yes))
    )
{pin_lines}
    (instances
      (project "sirena_555_flipflop"
        (path "/{project_uuid}" (reference "{ref}") (unit 1))
      )
    )
  )
'''


def _stub_label_point(pin_point: Point, local_pin: Point) -> Point:
    if local_pin.x < 0:
        return pin_point.shifted(-5.08, 0)
    if local_pin.x > 0:
        return pin_point.shifted(5.08, 0)
    if local_pin.y < 0:
        return pin_point.shifted(0, -5.08)
    return pin_point.shifted(0, 5.08)


def _route_visible_nets(label_points_by_net: dict[str, list[Point]]) -> tuple[list[str], list[str]]:
    wires: list[str] = []
    endpoints: list[Point] = []

    manual_segments = []
    manual_segments.extend(_route_dis_node())
    manual_segments.extend(_route_timing_node())
    manual_segments.extend(_route_ctrl_node())
    manual_segments.extend(_route_chain(label_points_by_net.get("CLK", []), [Point(71.12, 68.58), Point(104.14, 68.58)]))
    manual_segments.extend(
        [
            (Point(104.14, 63.5), Point(99.06, 63.5)),
            (Point(99.06, 63.5), Point(99.06, 48.26)),
            (Point(99.06, 48.26), Point(152.4, 48.26)),
            (Point(152.4, 48.26), Point(152.4, 68.58)),
            (Point(152.4, 68.58), Point(149.86, 68.58)),
            (Point(152.4, 48.26), Point(165.1, 48.26)),
            (Point(165.1, 48.26), Point(165.1, 43.18)),
        ]
    )
    manual_segments.extend(
        [
            (Point(149.86, 63.5), Point(165.1, 63.5)),
            (Point(165.1, 63.5), Point(165.1, 91.44)),
        ]
    )
    manual_segments.extend(_route_to_horizontal_trunk(label_points_by_net.get("BASE_Q1", []), 101.6))
    manual_segments.extend(_route_buzzer_neg())
    manual_segments.extend(_route_chain(label_points_by_net.get("FAST_NODE", []), [Point(40.64, 83.82), Point(45.72, 83.82)]))
    manual_segments.extend(_route_chain(label_points_by_net.get("LED_RED_NODE", []), [Point(185.42, 43.18), Point(190.5, 43.18)]))
    manual_segments.extend(_route_chain(label_points_by_net.get("LED_BLUE_NODE", []), [Point(185.42, 63.5), Point(190.5, 63.5)]))

    for a, b in manual_segments:
        if a == b:
            continue
        wires.append(_wire(a, b))
        endpoints.extend([a, b])
    junctions = [
        _junction(point)
        for point, count in Counter(endpoints).items()
        if count >= 3
    ]
    return wires, junctions


def _route_dis_node() -> list[tuple[Point, Point]]:
    # Avoid R1.1 +5V at (25.40, 30.48): R1.2 routes around the part body.
    return [
        (Point(40.64, 30.48), Point(45.72, 30.48)),
        (Point(45.72, 30.48), Point(45.72, 45.72)),
        (Point(45.72, 45.72), Point(15.24, 45.72)),
        (Point(15.24, 45.72), Point(15.24, 50.8)),
        (Point(15.24, 50.8), Point(15.24, 68.58)),
        (Point(15.24, 68.58), Point(15.24, 83.82)),
        (Point(20.32, 50.8), Point(15.24, 50.8)),
        (Point(40.64, 68.58), Point(15.24, 68.58)),
        (Point(20.32, 83.82), Point(15.24, 83.82)),
    ]


def _route_timing_node() -> list[tuple[Point, Point]]:
    # C1.2/GND and R3.1/FAST_NODE sit between the left pins and the right trunk.
    # The C1 timing branch is routed below the capacitor to avoid those nodes.
    return [
        (Point(40.64, 63.5), Point(73.66, 63.5)),
        (Point(40.64, 66.04), Point(73.66, 66.04)),
        (Point(40.64, 50.8), Point(73.66, 50.8)),
        (Point(66.04, 83.82), Point(73.66, 83.82)),
        (Point(20.32, 104.14), Point(20.32, 109.22)),
        (Point(20.32, 109.22), Point(73.66, 109.22)),
        (Point(73.66, 50.8), Point(73.66, 63.5)),
        (Point(73.66, 63.5), Point(73.66, 66.04)),
        (Point(73.66, 66.04), Point(73.66, 83.82)),
        (Point(73.66, 83.82), Point(73.66, 109.22)),
    ]


def _route_ctrl_node() -> list[tuple[Point, Point]]:
    # C2.2/GND is at (40.64, 119.38); route above it, not through it.
    return [
        (Point(55.88, 73.66), Point(63.5, 73.66)),
        (Point(63.5, 73.66), Point(63.5, 124.46)),
        (Point(63.5, 124.46), Point(20.32, 124.46)),
        (Point(20.32, 124.46), Point(20.32, 119.38)),
    ]


def _route_buzzer_neg() -> list[tuple[Point, Point]]:
    # BZ1+ is below BZ1-; route BUZZER_NEG above the positive terminal.
    return [
        (Point(210.82, 91.44), Point(226.06, 91.44)),
        (Point(226.06, 91.44), Point(226.06, 88.9)),
    ]


def _route_to_vertical_trunk(points: list[Point], trunk_x: float) -> list[tuple[Point, Point]]:
    unique = _unique_points(points)
    if len(unique) < 2:
        return []
    segments: list[tuple[Point, Point]] = []
    trunk_points = [Point(trunk_x, point.y) for point in unique]
    for point, trunk_point in zip(unique, trunk_points):
        segments.append((point, trunk_point))
    sorted_trunk = sorted(trunk_points, key=lambda point: point.y)
    for start, end in zip(sorted_trunk, sorted_trunk[1:]):
        segments.append((start, end))
    return segments


def _route_to_horizontal_trunk(points: list[Point], trunk_y: float) -> list[tuple[Point, Point]]:
    unique = _unique_points(points)
    if len(unique) < 2:
        return []
    segments: list[tuple[Point, Point]] = []
    trunk_points = [Point(point.x, trunk_y) for point in unique]
    for point, trunk_point in zip(unique, trunk_points):
        segments.append((point, trunk_point))
    sorted_trunk = sorted(trunk_points, key=lambda point: point.x)
    for start, end in zip(sorted_trunk, sorted_trunk[1:]):
        segments.append((start, end))
    return segments


def _route_chain(points: list[Point], chain: list[Point]) -> list[tuple[Point, Point]]:
    if len(_unique_points(points)) < 2:
        return []
    return list(zip(chain, chain[1:]))


def _unique_points(points: list[Point]) -> list[Point]:
    seen: set[tuple[float, float]] = set()
    unique: list[Point] = []
    for point in points:
        key = (point.x, point.y)
        if key not in seen:
            seen.add(key)
            unique.append(point)
    return unique


def _wire(a: Point, b: Point) -> str:
    return f'''  (wire (pts (xy {mm(a.x)} {mm(a.y)}) (xy {mm(b.x)} {mm(b.y)}))
    (stroke (width 0) (type solid))
    (uuid "{uuid.uuid4()}")
  )
'''


def _label(text: str, at: Point) -> str:
    return f'''  (label {json.dumps(text)} (at {mm(at.x)} {mm(at.y)} 0)
    (effects (font (size 1.27 1.27)) (justify left bottom))
    (uuid "{uuid.uuid4()}")
  )
'''


def _text(text: str, at: Point) -> str:
    return f'''  (text {json.dumps(text)} (at {mm(at.x)} {mm(at.y)} 0)
    (effects (font (size 1.27 1.27)) (justify left bottom))
    (uuid "{uuid.uuid4()}")
  )
'''


def _no_connect(at: Point) -> str:
    return f'  (no_connect (at {mm(at.x)} {mm(at.y)}) (uuid "{uuid.uuid4()}"))\n'


def _junction(at: Point) -> str:
    return f'  (junction (at {mm(at.x)} {mm(at.y)}) (diameter 0) (color 0 0 0 0) (uuid "{uuid.uuid4()}"))\n'


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())
