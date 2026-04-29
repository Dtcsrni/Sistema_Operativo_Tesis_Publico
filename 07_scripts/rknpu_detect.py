from __future__ import annotations

import os
from pathlib import Path


LEGACY_DEVICE_PATHS = ("/dev/rknpu", "/dev/rknn")
DRM_RENDER_ROOT = Path("/sys/class/drm")


def _driver_name(render_node: Path) -> str:
    uevent = Path("/sys/class/drm") / render_node.name / "device" / "uevent"
    if not uevent.exists():
        return ""
    for line in uevent.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("DRIVER="):
            return line.partition("=")[2].strip()
    return ""


def discover_rknpu_devices() -> list[str]:
    devices: list[str] = []
    for raw_path in LEGACY_DEVICE_PATHS:
        path = Path(raw_path)
        if path.exists():
            devices.append(str(path))

    if DRM_RENDER_ROOT.exists():
        for render in sorted(DRM_RENDER_ROOT.glob("renderD*")):
            if _driver_name(render).lower() == "rknpu":
                device = Path("/dev/dri") / render.name
                if device.exists():
                    devices.append(str(device))

    return devices


def rknpu_ready() -> bool:
    if os.getenv("OPENCLAW_FORCE_NPU_READY") == "1":
        return True
    return bool(discover_rknpu_devices())


def rknpu_summary() -> dict[str, object]:
    devices = discover_rknpu_devices()
    return {
        "ready": bool(devices),
        "devices": devices,
        "detection": "legacy_or_drm_render_rknpu",
    }
