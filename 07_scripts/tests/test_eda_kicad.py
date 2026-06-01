from __future__ import annotations

from pathlib import Path

from eda_kicad.compiler import Placement
from eda_kicad.geometry import Point
from eda_kicad.spec import load_circuit_spec
from eda_kicad.symbols import symbol_library
from eda_kicad.verification import _netlist_failures, _normalize_net_name


ROOT = Path(__file__).resolve().parents[2]


def test_load_sirena_spec_normalizes_buzzer_negative() -> None:
    spec = load_circuit_spec(ROOT / "sirena_555_flipflop" / "circuito.yaml")
    by_pin = {(conn.component, conn.pin): conn.net for conn in spec.connections}

    assert by_pin[("Q1", "C")] == "BUZZER_NEG"
    assert by_pin[("BZ1", "-")] == "BUZZER_NEG"
    assert by_pin[("U2", "2")] == "/Q"


def test_symbol_registry_contains_required_pins() -> None:
    symbols = symbol_library()

    assert set(symbols["NE555"].pins) == {"1", "2", "3", "4", "5", "6", "7", "8"}
    assert symbols["74HC74"].pins["14"].kind == "power_in"
    assert symbols["PWR_FLAG"].pins["1"].kind == "power_out"


def test_kicad_symbol_y_axis_is_inverted() -> None:
    placement = Placement("NE555", Point(55.88, 68.58))

    assert placement.pin_point(Point(-10.16, 7.62)) == Point(45.72, 60.96)
    assert placement.pin_point(Point(0, -10.16)) == Point(55.88, 78.74)


def test_netlist_export_matches_expected_contract() -> None:
    netlist = ROOT / "sirena_555_flipflop" / "export" / "sirena_555_flipflop.net"

    assert _netlist_failures(netlist) == []


def test_normalize_kicad_local_net_names() -> None:
    assert _normalize_net_name("/Q") == "Q"
    assert _normalize_net_name("/{slash}Q") == "/Q"
