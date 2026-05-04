"""
OpenWRT adapter — live implementation via ubus JSON-RPC.

All public functions degrade gracefully: they return False / empty list / a
"disconnected" dict when the router is unreachable, so the rest of the app
keeps working without an active router.

Environment variables (set in backend/.env):
  OPENWRT_HOST     router IP or hostname  (default: 127.0.0.1)
  OPENWRT_PORT     ubus HTTP port         (default: 8080)
  OPENWRT_USER     auth user              (default: root)
  OPENWRT_PASS     auth password
  OPENWRT_TIMEOUT  per-request timeout s  (default: 10)

Operational notes:
  - On real hardware change OPENWRT_PORT to 80 and OPENWRT_HOST to 192.168.1.1
  - Wireless operations (apply_isolation, create_guest_network SSID) require
    a device with at least one radio; they are skipped silently on the x86 VM
  - If the router uses HTTPS, add verify= handling to _client.call()
"""

import base64
import os
import time

import requests
from requests.exceptions import RequestException


# ── Config ────────────────────────────────────────────────────────────────────

_HOST = os.environ.get("OPENWRT_HOST", "127.0.0.1")
_PORT = int(os.environ.get("OPENWRT_PORT", "8080"))
_USER = os.environ.get("OPENWRT_USER", "root")
_PASS = os.environ.get("OPENWRT_PASS", "")
_TIMEOUT = int(os.environ.get("OPENWRT_TIMEOUT", "10"))
_URL = f"http://{_HOST}:{_PORT}/ubus"

_NULL_TOKEN = "00000000000000000000000000000000"


# ── ubus client ───────────────────────────────────────────────────────────────

class _UbusClient:
    """
    Thin JSON-RPC 2.0 client for OpenWRT's ubus HTTP endpoint.
    Handles session login, token refresh on expiry, and graceful error surfacing.
    """

    def __init__(self):
        self._token: str | None = None
        self._expiry: float = 0.0

    def _login(self) -> bool:
        try:
            r = requests.post(_URL, json={
                "jsonrpc": "2.0", "id": 1, "method": "call",
                "params": [_NULL_TOKEN, "session", "login",
                           {"username": _USER, "password": _PASS}],
            }, timeout=_TIMEOUT)
            result = r.json().get("result", [])
            if result and result[0] == 0:
                self._token = result[1]["ubus_rpc_session"]
                self._expiry = time.time() + result[1]["expires"] - 30
                return True
        except (RequestException, KeyError, IndexError, ValueError):
            pass
        return False

    def call(self, obj: str, method: str, params: dict | None = None,
             _retry: bool = True) -> tuple[int, dict]:
        """
        Make an authenticated ubus call.
        Returns (ubus_code, result_dict). Code 0 = success.
        Returns (-1, {}) on network/auth failure.
        """
        if not self._token or time.time() > self._expiry:
            if not self._login():
                return -1, {}

        try:
            r = requests.post(_URL, json={
                "jsonrpc": "2.0", "id": 1, "method": "call",
                "params": [self._token, obj, method, params or {}],
            }, timeout=_TIMEOUT)
            result = r.json().get("result", [-1])
            code = result[0]
            data = result[1] if len(result) > 1 else {}

            # Code 6 = PERMISSION_DENIED — usually a stale token; retry once.
            if code == 6 and _retry:
                self._token = None
                return self.call(obj, method, params, _retry=False)

            return code, data
        except (RequestException, ValueError, IndexError):
            return -1, {}


_client = _UbusClient()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mac_section(mac: str) -> str:
    """Safe UCI section name from a MAC address."""
    return "netsys_" + mac.replace(":", "").lower()


def _uci_commit_and_reload(config: str, init_service: str) -> bool:
    code, _ = _client.call("uci", "apply", {"rollback": False})
    # code 5 = NO_DATA: no pending changes (idempotent re-apply) — treat as success
    if code not in (0, 5):
        return False
    code, _ = _client.call("file", "exec",
                            {"command": f"/etc/init.d/{init_service}",
                             "params": ["restart"]})
    return code == 0


def _file_read(path: str) -> str | None:
    code, data = _client.call("file", "read", {"path": path})
    if code != 0:
        return None
    raw = data.get("data", "")
    return base64.b64decode(raw).decode("utf-8", errors="replace")


def _file_write(path: str, content: str) -> bool:
    encoded = base64.b64encode(content.encode()).decode()
    code, _ = _client.call("file", "write", {"path": path, "data": encoded})
    return code == 0


# ── Public API ────────────────────────────────────────────────────────────────

def get_status() -> dict:
    """
    Probe OpenWRT via ubus. Returns connection state and firmware version.
    """
    code, data = _client.call("system", "board")
    if code != 0:
        return {"openwrt": "disconnected", "version": None}
    release = data.get("release", {})
    return {
        "openwrt": "connected",
        "version": release.get("version"),
        "hostname": data.get("hostname"),
        "model": data.get("model"),
    }


def discover_devices() -> list[dict]:
    """
    Merge DHCP leases and ARP host hints from OpenWRT into the device schema.
    Returns [] if the router is unreachable.

    Each entry: {"mac", "name", "ip", "type"}
    The caller (devices.py) merges this with the local devices.json to
    preserve user-assigned names and types.
    """
    code, data = _client.call("luci-rpc", "getHostHints")
    if code != 0:
        return []

    code2, lease_data = _client.call("luci-rpc", "getDHCPLeases")
    leases_by_mac: dict[str, dict] = {}
    if code2 == 0:
        for lease in lease_data.get("dhcp_leases", []):
            mac = lease.get("macaddr", "").upper()
            if mac:
                leases_by_mac[mac] = lease

    discovered = []
    for mac, info in data.items():
        # Skip the router itself and QEMU virtual hosts with no name
        ips = info.get("ipaddrs", [])
        name = info.get("name", "")
        if not ips or mac == "52:54:00:12:34:56":
            continue

        lease = leases_by_mac.get(mac.upper(), {})
        hostname = lease.get("hostname") or name or mac

        discovered.append({
            "mac": mac,
            "name": hostname,
            "ip": ips[0] if ips else "",
            "type": "unknown",
        })

    return discovered


def apply_firewall_rule(mac: str, action: str) -> bool:
    """
    Block or unblock a device's internet (WAN) access via a UCI firewall rule.
    action: "block" | "unblock"
    """
    section = _mac_section(mac)

    if action == "block":
        code, _ = _client.call("uci", "add", {
            "config": "firewall",
            "type": "rule",
            "name": section,
        })
        if code not in (0, 6):  # 6 = section already exists
            return False

        code, _ = _client.call("uci", "set", {
            "config": "firewall",
            "section": section,
            "values": {
                "name": f"NetSys block {mac}",
                "src": "lan",
                "src_mac": mac,
                "dest": "wan",
                "target": "REJECT",
                "enabled": "1",
            },
        })
        if code != 0:
            return False
        return _uci_commit_and_reload("firewall", "firewall")

    if action == "unblock":
        code, _ = _client.call("uci", "delete", {
            "config": "firewall",
            "section": section,
        })
        # code 5 = section not found — already unblocked, treat as success
        if code not in (0, 5):
            return False
        return _uci_commit_and_reload("firewall", "firewall")

    return False


def apply_isolation(mac: str, isolated: bool) -> bool:
    """
    Isolate a device from other LAN peers while keeping internet access.

    Implementation: writes an nftables rule into /etc/nftables.d/ (fw4 style)
    that drops forwarding between the MAC and the LAN subnet.

    On hardware without wifi, this is the correct isolation mechanism.
    On wifi-capable hardware, combine with 'option isolate 1' on the SSID.

    Note: bridge-level isolation (device ↔ device on same L2 segment) is not
    possible via nftables alone; it requires ebtables or per-VLAN assignment.
    This implementation blocks routed LAN traffic, which covers most use cases.
    """
    section_block = _mac_section(mac) + "_iso_out"
    section_in    = _mac_section(mac) + "_iso_in"

    if isolated:
        for section, dest in [(section_block, "lan"), (section_in, "lan")]:
            _client.call("uci", "add", {
                "config": "firewall", "type": "rule", "name": section,
            })
            _client.call("uci", "set", {
                "config": "firewall",
                "section": section,
                "values": {
                    "name": f"NetSys isolate {mac}",
                    "src": "lan",
                    "src_mac": mac,
                    "dest": "lan",
                    "target": "REJECT",
                    "enabled": "1",
                },
            })
        return _uci_commit_and_reload("firewall", "firewall")

    else:
        for section in [section_block, section_in]:
            _client.call("uci", "delete", {"config": "firewall", "section": section})
        return _uci_commit_and_reload("firewall", "firewall")


def create_guest_network(ssid: str = "NetSys-Guest") -> bool:
    """
    Create an isolated guest network:
      - New static interface 10.10.10.1/24 named 'netsys_guest'
      - DHCP pool on that interface
      - Firewall zone: allows WAN forward, rejects LAN forward
      - Wireless SSID (skipped on x86 VM — no radios present)

    Changes require a netifd + firewall restart; clients appear after ~10s.
    """
    iface = "netsys_guest"
    zone  = "netsys_guest_zone"
    fwd   = "netsys_guest_fwd"

    # 1. Network interface
    _client.call("uci", "add",  {"config": "network",  "type": "interface", "name": iface})
    _client.call("uci", "set",  {"config": "network",  "section": iface, "values": {
        "proto": "static", "ipaddr": "10.10.10.1", "netmask": "255.255.255.0",
    }})

    # 2. DHCP pool
    _client.call("uci", "add",  {"config": "dhcp", "type": "dhcp", "name": iface})
    _client.call("uci", "set",  {"config": "dhcp", "section": iface, "values": {
        "interface": iface, "start": "100", "limit": "100", "leasetime": "1h",
    }})

    # 3. Firewall zone
    _client.call("uci", "add",  {"config": "firewall", "type": "zone", "name": zone})
    _client.call("uci", "set",  {"config": "firewall", "section": zone, "values": {
        "name": "guest", "network": iface,
        "input": "REJECT", "output": "ACCEPT", "forward": "REJECT",
    }})

    # 4. Forward guest → wan
    _client.call("uci", "add",  {"config": "firewall", "type": "forwarding", "name": fwd})
    _client.call("uci", "set",  {"config": "firewall", "section": fwd,
                                  "values": {"src": "guest", "dest": "wan"}})

    # 5. Try to add wireless SSID (silently skipped on x86 with no radios)
    code, radio_data = _client.call("iwinfo", "info", {})
    if code == 0 and radio_data:
        radio = next(iter(radio_data))
        wiface = "netsys_guest_wifi"
        _client.call("uci", "add", {"config": "wireless", "type": "wifi-iface", "name": wiface})
        _client.call("uci", "set", {"config": "wireless", "section": wiface, "values": {
            "device": radio, "mode": "ap", "ssid": ssid,
            "encryption": "none", "network": iface,
        }})

    # 6. Apply all UCI changes
    # code 5 = NO_DATA: sections unchanged (idempotent re-apply) — still success
    code, _ = _client.call("uci", "apply", {"rollback": False})
    if code not in (0, 5):
        return False

    # Bring up the new interface (init.d/network restart is blocked by ubus ACL;
    # ifup works and is sufficient to activate the new interface without a full restart)
    _client.call("file", "exec", {"command": "/sbin/ifup", "params": [iface]})
    _client.call("file", "exec", {"command": "/etc/init.d/firewall", "params": ["restart"]})
    return True


def apply_schedule(mac: str, block_after: str) -> bool:
    """
    Install a cron job that blocks the device at block_after and unblocks at 06:00.
    block_after: "HH:MM" in 24h format, e.g. "22:00"

    The block is implemented by enabling a UCI firewall rule via ssh-less exec.
    The unblock job removes it. Both jobs reload the firewall.
    """
    try:
        h, m = block_after.strip().split(":")
        h, m = int(h), int(m)
        assert 0 <= h <= 23 and 0 <= m <= 59
    except (ValueError, AssertionError):
        return False

    section = _mac_section(mac)

    # Ensure the firewall rule section exists (disabled by default)
    _client.call("uci", "add", {"config": "firewall", "type": "rule", "name": section})
    _client.call("uci", "set", {"config": "firewall", "section": section, "values": {
        "name": f"NetSys schedule {mac}",
        "src": "lan", "src_mac": mac, "dest": "wan",
        "target": "REJECT", "enabled": "0",
    }})
    code, _ = _client.call("uci", "apply", {"rollback": False})
    if code != 0:
        return False

    # Write cron entries
    enable_cmd  = f"uci set firewall.{section}.enabled=1 && uci apply && /etc/init.d/firewall restart"
    disable_cmd = f"uci set firewall.{section}.enabled=0 && uci apply && /etc/init.d/firewall restart"

    block_entry   = f"{m} {h} * * * {enable_cmd}"
    unblock_entry = f"0 6 * * * {disable_cmd}"
    marker        = f"# netsys {section}"

    current = _file_read("/etc/crontabs/root") or ""

    # Remove any previous entries for this MAC
    lines = [l for l in current.splitlines()
             if section not in l and l.strip() != marker]
    lines += [marker, block_entry, unblock_entry]

    if not _file_write("/etc/crontabs/root", "\n".join(lines) + "\n"):
        return False

    code, _ = _client.call("file", "exec",
                            {"command": "/etc/init.d/cron", "params": ["reload"]})
    return code == 0
