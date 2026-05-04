def test_intent_block_enforces_on_router(client, fake_openwrt):
    r = client.post("/api/intent", json={"device_id": 1, "action": "block"})
    assert r.status_code == 201
    body = r.json()
    assert body["action"] == "block"
    assert body["enforced"] is True
    assert ("firewall", "AA:BB:CC:DD:EE:01", "block") in fake_openwrt["applied_calls"]


def test_intent_isolate(client, fake_openwrt):
    r = client.post("/api/intent", json={"device_id": 1, "action": "isolate"})
    assert r.status_code == 201
    assert r.json()["enforced"] is True
    assert ("isolation", "AA:BB:CC:DD:EE:01", True) in fake_openwrt["applied_calls"]


def test_intent_guest_network(client, fake_openwrt):
    r = client.post("/api/intent", json={"device_id": 1, "action": "guest_network"})
    assert r.status_code == 201
    body = r.json()
    assert body["action"] == "guest_network"
    assert body["enforced"] is True
    assert any(c[0] == "guest" for c in fake_openwrt["applied_calls"])


def test_intent_schedule_block_requires_time(client):
    r = client.post("/api/intent", json={"device_id": 1, "action": "schedule_block"})
    assert r.status_code == 400
    assert "time" in r.json()["detail"].lower()


def test_intent_schedule_block_with_time(client, fake_openwrt):
    r = client.post(
        "/api/intent",
        json={"device_id": 1, "action": "schedule_block", "time": "22:00"},
    )
    assert r.status_code == 201
    assert ("schedule", "AA:BB:CC:DD:EE:01", "22:00") in fake_openwrt["applied_calls"]


def test_intent_with_text_uses_classifier(client, fake_openwrt):
    r = client.post("/api/intent", json={"device_id": 1, "text": "block my console"})
    assert r.status_code == 201
    body = r.json()
    assert body["action"] in {"block", "isolate", "guest_network", "schedule_block"}
    assert "classification" in body
    assert body["classification"]["predicted_action"] == body["action"]


def test_intent_missing_device_id(client):
    r = client.post("/api/intent", json={"action": "block"})
    assert r.status_code == 422


def test_intent_unknown_device(client):
    r = client.post("/api/intent", json={"device_id": 9999, "action": "block"})
    assert r.status_code == 404


def test_intent_invalid_action(client):
    r = client.post("/api/intent", json={"device_id": 1, "action": "delete_everything"})
    assert r.status_code == 422


def test_intent_neither_action_nor_text(client):
    r = client.post("/api/intent", json={"device_id": 1})
    assert r.status_code == 400


def test_intent_no_mac_block_records_not_enforced(client, fake_openwrt):
    """Smart TV (id=3) has no MAC. Block should save the policy but not enforce."""
    r = client.post("/api/intent", json={"device_id": 3, "action": "block"})
    assert r.status_code == 201
    body = r.json()
    assert body["enforced"] is False
    # And nothing was sent to the router
    assert all(c[0] != "firewall" for c in fake_openwrt["applied_calls"])


def test_intent_failed_enforcement_still_saves_policy(client, fake_openwrt):
    fake_openwrt["next_apply_result"] = False
    r = client.post("/api/intent", json={"device_id": 1, "action": "block"})
    assert r.status_code == 201
    body = r.json()
    assert body["enforced"] is False
    # The policy was still persisted
    assert client.get("/api/policies").json()
