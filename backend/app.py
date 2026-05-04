from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = BASE_DIR.parent / "frontend" / "dist"

app = Flask(__name__, static_folder=str(FRONTEND_DIST_DIR), static_url_path="")
CORS(app)

# ----------------------------
# Mock "auto-discovered" devices
# ----------------------------
devices = [
    {"id": 1, "name": "iPhone", "type": "mobile"},
    {"id": 2, "name": "Gaming Console", "type": "console"},
    {"id": 3, "name": "Smart TV", "type": "iot"},
    {"id": 4, "name": "Work Laptop", "type": "computer"},
]

# Active policies
policies = []


# ----------------------------
# Intent → Policy Logic (CORE)
# ----------------------------
def generate_policy(intent):
    action = intent.get("action")
    device_id = intent.get("device_id")
    time = intent.get("time")

    # Find device name for nicer output
    device_name = next((d["name"] for d in devices if d["id"] == device_id), "Unknown Device")

    if action == "block":
        return {
            "type": "firewall",
            "rule": f"DENY all traffic from {device_name}"
        }

    elif action == "isolate":
        return {
            "type": "network",
            "rule": f"ISOLATE {device_name} from other devices"
        }

    elif action == "guest_network":
        return {
            "type": "network",
            "rule": "CREATE a guest Wi-Fi network (isolated SSID)"
        }

    elif action == "schedule_block":
        return {
            "type": "time_rule",
            "rule": f"BLOCK {device_name} from network AFTER {time}"
        }

    return {
        "type": "unknown",
        "rule": "INVALID INTENT"
    }


# ----------------------------
# Routes
# ----------------------------

# Get all devices
@app.route("/devices", methods=["GET"])
@app.route("/api/devices", methods=["GET"])
def get_devices():
    return jsonify(devices)


# (Optional) Add a device
@app.route("/devices", methods=["POST"])
@app.route("/api/devices", methods=["POST"])
def add_device():
    new_device = request.json
    new_device["id"] = len(devices) + 1
    devices.append(new_device)
    return jsonify(new_device)


# Create intent → generates policy
@app.route("/intent", methods=["POST"])
@app.route("/api/intent", methods=["POST"])
def create_intent():
    intent = request.json
    policy = generate_policy(intent)

    policy["id"] = len(policies) + 1
    policies.append(policy)

    return jsonify(policy)


# Get all policies
@app.route("/policies", methods=["GET"])
@app.route("/api/policies", methods=["GET"])
def get_policies():
    return jsonify(policies)


# Delete a policy
@app.route("/policies/<int:policy_id>", methods=["DELETE"])
@app.route("/api/policies/<int:policy_id>", methods=["DELETE"])
def delete_policy(policy_id):
    global policies
    policies = [p for p in policies if p["id"] != policy_id]
    return jsonify({"status": "deleted"})


@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_frontend(path):
    asset_path = FRONTEND_DIST_DIR / path

    if asset_path.exists() and asset_path.is_file():
        return send_from_directory(app.static_folder, path)

    return send_from_directory(app.static_folder, "index.html")


# ----------------------------
# Run app
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
