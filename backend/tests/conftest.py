"""Test fixtures: isolated tmpdir-backed JSON stores + a stubbed openwrt module."""

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def tmp_data(tmp_path, monkeypatch):
    """Redirect devices.json and policies.json to a per-test tmp dir."""
    import devices as devices_mod
    import policies as policies_mod

    devices_path = tmp_path / "devices.json"
    policies_path = tmp_path / "policies.json"

    monkeypatch.setattr(devices_mod, "DATA_PATH", devices_path)
    monkeypatch.setattr(policies_mod, "DATA_PATH", policies_path)

    # Seed devices with a known fixture set so tests are deterministic
    devices_path.write_text(json.dumps([
        {"id": 1, "name": "iPhone",         "type": "mobile",   "mac": "AA:BB:CC:DD:EE:01"},
        {"id": 2, "name": "Gaming Console", "type": "console",  "mac": "AA:BB:CC:DD:EE:02"},
        {"id": 3, "name": "Smart TV",       "type": "iot",      "mac": ""},
    ]))
    policies_path.write_text("[]")

    yield {"devices": devices_path, "policies": policies_path}


@pytest.fixture
def fake_openwrt(monkeypatch):
    """Replace the openwrt module with a controllable stub."""
    import openwrt as real

    state: dict[str, Any] = {
        "connected": False,
        "applied_calls": [],
        "live_devices": [],
        "next_apply_result": True,
    }

    def get_status():
        return (
            {"openwrt": "connected", "version": "23.05.5", "hostname": "openwrt", "model": "x86"}
            if state["connected"]
            else {"openwrt": "disconnected", "version": None}
        )

    def discover_devices():
        return list(state["live_devices"])

    def apply_firewall_rule(mac, action):
        state["applied_calls"].append(("firewall", mac, action))
        return state["next_apply_result"]

    def apply_isolation(mac, isolated):
        state["applied_calls"].append(("isolation", mac, isolated))
        return state["next_apply_result"]

    def create_guest_network(ssid="NetSys-Guest"):
        state["applied_calls"].append(("guest", ssid))
        return state["next_apply_result"]

    def apply_schedule(mac, t):
        state["applied_calls"].append(("schedule", mac, t))
        return state["next_apply_result"]

    monkeypatch.setattr(real, "get_status", get_status)
    monkeypatch.setattr(real, "discover_devices", discover_devices)
    monkeypatch.setattr(real, "apply_firewall_rule", apply_firewall_rule)
    monkeypatch.setattr(real, "apply_isolation", apply_isolation)
    monkeypatch.setattr(real, "create_guest_network", create_guest_network)
    monkeypatch.setattr(real, "apply_schedule", apply_schedule)

    return state


@pytest.fixture
def client(tmp_data, fake_openwrt):
    """FastAPI TestClient with isolated state and stubbed router."""
    from fastapi.testclient import TestClient
    import app as app_mod

    return TestClient(app_mod.app)
