import json
import os
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "devices.json"

_DEFAULTS = [
    {"id": 1, "name": "iPhone",         "type": "mobile",   "mac": ""},
    {"id": 2, "name": "Gaming Console", "type": "console",  "mac": ""},
    {"id": 3, "name": "Smart TV",       "type": "iot",      "mac": ""},
    {"id": 4, "name": "Work Laptop",    "type": "computer", "mac": ""},
]


def load_devices() -> list[dict]:
    if not DATA_PATH.exists():
        save_devices(_DEFAULTS)
        return list(_DEFAULTS)
    with open(DATA_PATH) as f:
        return json.load(f)


def save_devices(devices: list[dict]) -> None:
    tmp = DATA_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(devices, f, indent=2)
    os.replace(tmp, DATA_PATH)


def get_all() -> list[dict]:
    return load_devices()


def get_by_id(device_id: int) -> dict | None:
    return next((d for d in load_devices() if d["id"] == device_id), None)


def add(name: str, device_type: str, mac: str = "") -> dict:
    devices = load_devices()
    next_id = max((d["id"] for d in devices), default=0) + 1
    device = {"id": next_id, "name": name, "type": device_type, "mac": mac}
    devices.append(device)
    save_devices(devices)
    return device


def delete(device_id: int) -> bool:
    devices = load_devices()
    filtered = [d for d in devices if d["id"] != device_id]
    if len(filtered) == len(devices):
        return False
    save_devices(filtered)
    return True


def merge_live(live: list[dict]) -> list[dict]:
    """
    Merge live devices discovered from OpenWRT with the persisted device list.

    - Live devices with a MAC that matches an existing entry inherit that
      entry's id, name, and type (user annotations are preserved).
    - New MACs not in devices.json are appended with auto-assigned IDs.
    - Persisted entries with no MAC or no matching live device are retained
      so manual entries don't disappear when the router has no record of them.
    - The merged list is saved back to devices.json.
    """
    stored = load_devices()
    by_mac = {d["mac"].upper(): d for d in stored if d.get("mac")}

    merged = list(stored)
    next_id = max((d["id"] for d in stored), default=0) + 1

    for live_dev in live:
        mac = live_dev.get("mac", "").upper()
        ip  = live_dev.get("ip", "")

        if mac in by_mac:
            # Update IP on the existing record (non-destructive)
            for entry in merged:
                if entry.get("mac", "").upper() == mac:
                    entry["ip"] = ip
                    break
        else:
            # New device seen on the network — add it
            new = {
                "id":   next_id,
                "name": live_dev.get("name", mac),
                "type": live_dev.get("type", "unknown"),
                "mac":  mac,
                "ip":   ip,
            }
            merged.append(new)
            by_mac[mac] = new
            next_id += 1

    save_devices(merged)
    return merged
