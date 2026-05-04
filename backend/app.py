"""FastAPI entry point for NetSys-Home."""

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import devices
import policies
import openwrt
from classifier.intent_classifier import IntentClassifier
from schemas import (
    ClassifyRequest,
    ClassifyResponse,
    Device,
    DeviceCreate,
    IntentRequest,
    IntentResponse,
    Policy,
    StatusResponse,
)


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = BASE_DIR.parent / "frontend" / "dist"

APP_VERSION = "1.1.0"

app = FastAPI(
    title="NetSys-Home API",
    version=APP_VERSION,
    description="Intent-based home Wi-Fi management backed by OpenWRT.",
)

_cors_raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:5000")
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


classifier = IntentClassifier()
classifier.load()


def _policy_rule(action: str, device_name: str, time: str) -> tuple[str, str]:
    if action == "block":
        return "firewall", f"DENY all traffic from {device_name}"
    if action == "isolate":
        return "network", f"ISOLATE {device_name} from other devices"
    if action == "guest_network":
        return "network", "CREATE a guest Wi-Fi network (isolated SSID)"
    if action == "schedule_block":
        return "time_rule", f"BLOCK {device_name} from network AFTER {time}"
    return "unknown", "INVALID INTENT"


def _enforce_policy(action: str, device: dict, time: str) -> bool:
    """Call the appropriate OpenWRT function. Returns True on success."""
    mac = device.get("mac", "")
    if action == "block":
        return openwrt.apply_firewall_rule(mac, "block") if mac else False
    if action == "isolate":
        return openwrt.apply_isolation(mac, True) if mac else False
    if action == "guest_network":
        return openwrt.create_guest_network()
    if action == "schedule_block":
        return openwrt.apply_schedule(mac, time) if mac else False
    return False


def _reverse_policy(policy: dict) -> bool:
    """Undo the router-side effect of a policy. Best-effort; does not raise."""
    action = policy.get("action", "")
    device = devices.get_by_id(policy.get("device_id"))
    mac = (device or {}).get("mac", "")
    if action == "block":
        return openwrt.apply_firewall_rule(mac, "unblock") if mac else False
    if action == "isolate":
        return openwrt.apply_isolation(mac, False) if mac else False
    if action == "schedule_block":
        return openwrt.apply_firewall_rule(mac, "unblock") if mac else False
    return False  # guest_network: no automatic teardown


# ── Devices ──────────────────────────────────────────────────────────────────

@app.get("/api/devices", response_model=list[Device])
def get_devices():
    live = openwrt.discover_devices()
    if live:
        return devices.merge_live(live)
    return devices.get_all()


@app.post("/api/devices", response_model=Device, status_code=201)
def add_device(payload: DeviceCreate):
    return devices.add(payload.name, payload.type, payload.mac)


# ── Intents ──────────────────────────────────────────────────────────────────

@app.post("/api/intent", response_model=IntentResponse, status_code=201)
def handle_intent(payload: IntentRequest):
    action = payload.action
    text = (payload.text or "").strip()

    if not action and not text:
        raise HTTPException(400, "Provide either 'action' or 'text'")

    classification = None
    if not action and text:
        classification = classifier.predict(text)
        action = classification["predicted_action"]

    if action == "schedule_block" and not (payload.time or "").strip():
        raise HTTPException(400, "Missing required field: time for schedule_block")

    device = devices.get_by_id(payload.device_id)
    if device is None:
        raise HTTPException(404, "Device not found")

    policy_type, rule = _policy_rule(action, device["name"], payload.time or "")
    policy = policies.add({
        "type": policy_type,
        "rule": rule,
        "device_id": device["id"],
        "action": action,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    enforced = _enforce_policy(action, device, payload.time or "")

    response = {**policy, "enforced": enforced}
    if classification:
        response["classification"] = classification
    return response


# ── Policies ─────────────────────────────────────────────────────────────────

@app.get("/api/policies", response_model=list[Policy])
def get_policies():
    return policies.get_all()


@app.delete("/api/policies/{policy_id}")
def delete_policy(policy_id: int):
    policy = policies.get_by_id(policy_id)
    if policy is None:
        raise HTTPException(404, "Policy not found")
    _reverse_policy(policy)
    policies.delete(policy_id)
    return {"message": "Policy deleted"}


# ── Status ───────────────────────────────────────────────────────────────────

@app.get("/api/status", response_model=StatusResponse)
def get_status():
    return {
        **openwrt.get_status(),
        "app_version": APP_VERSION,
        "classifier": "random_forest" if classifier.is_trained else "stub",
    }


# ── Classify ─────────────────────────────────────────────────────────────────

@app.post("/api/classify", response_model=ClassifyResponse)
def classify_intent(payload: ClassifyRequest):
    result = classifier.predict(payload.text)
    return {"text": payload.text, **result}


# ── Frontend (production build) ──────────────────────────────────────────────

if FRONTEND_DIST_DIR.exists():
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str = ""):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        candidate = FRONTEND_DIST_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        index = FRONTEND_DIST_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
        return JSONResponse({"error": "Frontend not built. Run: npm run build"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    debug = os.environ.get("FASTAPI_DEBUG", os.environ.get("FLASK_DEBUG", "0")) == "1"
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=debug)
