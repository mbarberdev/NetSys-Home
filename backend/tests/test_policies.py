def test_policies_starts_empty(client):
    r = client.get("/api/policies")
    assert r.status_code == 200
    assert r.json() == []


def test_policy_created_then_listed(client):
    client.post("/api/intent", json={"device_id": 1, "action": "block"})
    r = client.get("/api/policies")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["action"] == "block"


def test_policy_delete(client):
    client.post("/api/intent", json={"device_id": 1, "action": "block"})
    pid = client.get("/api/policies").json()[0]["id"]

    r = client.delete(f"/api/policies/{pid}")
    assert r.status_code == 200
    assert client.get("/api/policies").json() == []


def test_policy_delete_unknown(client):
    r = client.delete("/api/policies/9999")
    assert r.status_code == 404


def test_policy_delete_reverses_block_on_router(client, fake_openwrt):
    """Deleting a block policy should call apply_firewall_rule(..., 'unblock')."""
    client.post("/api/intent", json={"device_id": 1, "action": "block"})
    pid = client.get("/api/policies").json()[0]["id"]
    fake_openwrt["applied_calls"].clear()

    r = client.delete(f"/api/policies/{pid}")
    assert r.status_code == 200
    assert ("firewall", "AA:BB:CC:DD:EE:01", "unblock") in fake_openwrt["applied_calls"]


def test_policy_delete_reverses_isolate_on_router(client, fake_openwrt):
    """Deleting an isolate policy should call apply_isolation(..., False)."""
    client.post("/api/intent", json={"device_id": 1, "action": "isolate"})
    pid = client.get("/api/policies").json()[0]["id"]
    fake_openwrt["applied_calls"].clear()

    r = client.delete(f"/api/policies/{pid}")
    assert r.status_code == 200
    assert ("isolation", "AA:BB:CC:DD:EE:01", False) in fake_openwrt["applied_calls"]


def test_policy_delete_with_no_mac_does_not_call_router(client, fake_openwrt):
    """Device 3 has no MAC — reversal should be skipped without raising."""
    # Skip enforcement on the way in (no MAC), but the policy still persists
    client.post("/api/intent", json={"device_id": 3, "action": "block"})
    pid = client.get("/api/policies").json()[0]["id"]
    fake_openwrt["applied_calls"].clear()

    r = client.delete(f"/api/policies/{pid}")
    assert r.status_code == 200
    assert fake_openwrt["applied_calls"] == []
