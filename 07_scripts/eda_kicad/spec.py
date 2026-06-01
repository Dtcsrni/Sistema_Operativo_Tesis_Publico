from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ComponentSpec(BaseModel):
    reference: str
    value: str
    role: str = ""
    symbol: str = ""
    unit: int = 1
    footprint: str = ""
    description: str = ""


class PinConnection(BaseModel):
    component: str
    pin: str
    net: str
    description: str = ""


class CircuitSpec(BaseModel):
    name: str
    purpose: str
    components: list[ComponentSpec]
    nets: list[str]
    connections: list[PinConnection]
    equations: dict[str, str] = Field(default_factory=dict)
    acceptance: list[str] = Field(default_factory=list)

    def by_ref(self) -> dict[str, ComponentSpec]:
        return {component.reference: component for component in self.components}


def load_circuit_spec(path: Path) -> CircuitSpec:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    components = [
        ComponentSpec(
            reference=item["referencia"],
            value=str(item.get("valor", "")),
            role=str(item.get("funcion", "")),
        )
        for item in data.get("componentes", [])
    ]
    connections: list[PinConnection] = []
    for ref, pins in data.get("conexiones", {}).items():
        if not isinstance(pins, dict):
            continue
        for raw_pin, net in pins.items():
            if str(net).startswith("no conectado"):
                continue
            canonical_net = "BUZZER_NEG" if str(net) == "BZ1-" else str(net)
            connections.append(
                PinConnection(
                    component=str(ref),
                    pin=_normalize_pin(raw_pin),
                    net=canonical_net,
                    description=f"{ref}.{raw_pin}",
                )
            )

    # Conexiones explicitas no representadas en el YAML original.
    extra = [
        ("R1", "1", "+5V"), ("R1", "2", "DIS_NODE"),
        ("R2", "1", "DIS_NODE"), ("R2", "2", "TIMING_NODE"),
        ("SW1", "1", "DIS_NODE"), ("SW1", "2", "FAST_NODE"),
        ("R3", "1", "FAST_NODE"), ("R3", "2", "TIMING_NODE"),
        ("C1", "1", "TIMING_NODE"), ("C1", "2", "GND"),
        ("C2", "1", "CTRL_NODE"), ("C2", "2", "GND"),
        ("C3", "1", "+5V"), ("C3", "2", "GND"),
        ("C4", "1", "+5V"), ("C4", "2", "GND"),
        ("C5", "1", "+5V"), ("C5", "2", "GND"),
        ("R4", "1", "/Q"), ("R4", "2", "LED_RED_NODE"),
        ("D1", "A", "LED_RED_NODE"), ("D1", "K", "GND"),
        ("R5", "1", "Q"), ("R5", "2", "LED_BLUE_NODE"),
        ("D2", "A", "LED_BLUE_NODE"), ("D2", "K", "GND"),
        ("R6", "1", "Q"), ("R6", "2", "BASE_Q1"),
        ("R7", "1", "BASE_Q1"), ("R7", "2", "GND"),
        ("Q1", "B", "BASE_Q1"), ("Q1", "C", "BUZZER_NEG"), ("Q1", "E", "GND"),
        ("BZ1", "+", "+5V"), ("BZ1", "-", "BUZZER_NEG"),
    ]
    seen = {(c.component, c.pin) for c in connections}
    for component, pin, net in extra:
        if (component, pin) not in seen:
            connections.append(PinConnection(component=component, pin=pin, net=net))

    return CircuitSpec(
        name=str(data.get("metadatos", {}).get("nombre", "kicad_project")),
        purpose=str(data.get("metadatos", {}).get("proposito", "")),
        components=components,
        nets=[str(net) for net in data.get("redes", [])],
        connections=connections,
        equations={str(k): str(v) for k, v in data.get("ecuaciones", {}).items()},
        acceptance=[str(item) for item in data.get("criterios_de_aprobacion", [])],
    )


def _normalize_pin(pin: Any) -> str:
    text = str(pin)
    if text.startswith("pin"):
        return text[3:]
    aliases = {"base": "B", "emisor": "E", "colector": "C", "positivo": "+", "negativo": "-"}
    return aliases.get(text, text)
