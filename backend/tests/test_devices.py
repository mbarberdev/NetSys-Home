def test_devices_returns_seeded_when_router_offline(client):
    r = client.get("/api/devices")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 3
    assert {d["name"] for d in body} == {"iPhone", "Gaming Console", "Smart TV"}


def test_devices_returns_live_when_router_connected(client, fake_openwrt):
    fake_openwrt["connected"] = True
    fake_openwrt["live_devices"] = [
        {"mac": "AA:BB:CC:DD:EE:01", "name": "iPhone-live", "ip": "192.168.1.10", "type": "unknown"},
        {"mac": "AA:BB:CC:DD:EE:99", "name": "newhost",     "ip": "192.168.1.50", "type": "unknown"},
    ]
    r = client.get("/api/devices")
    assert r.status_code == 200
    body = r.json()
    # Existing entry preserves its user-assigned name
    by_mac = {d["mac"]: d for d in body}
    assert by_mac["AA:BB:CC:DD:EE:01"]["name"] == "iPhone"
    assert by_mac["AA:BB:CC:DD:EE:01"]["ip"] == "192.168.1.10"
    # New MAC is appended
    assert "AA:BB:CC:DD:EE:99" in by_mac
    assert by_mac["AA:BB:CC:DD:EE:99"]["name"] == "newhost"


def test_add_device_minimal(client):
    r = client.post("/api/devices", json={"name": "Laptop", "type": "computer"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Laptop"
    assert body["type"] == "computer"
    assert body["id"] == 4

    r2 = client.get("/api/devices")
    assert any(d["name"] == "Laptop" for d in r2.json())


def test_add_device_uppercases_mac(client):
    r = client.post("/api/devices", json={"name": "X", "type": "mobile", "mac": "aa:bb:cc:dd:ee:ff"})
    assert r.status_code == 201
    assert r.json()["mac"] == "AA:BB:CC:DD:EE:FF"


def test_add_device_missing_fields(client):
    r = client.post("/api/devices", json={"name": "x"})
    assert r.status_code == 422

    r = client.post("/api/devices", json={"type": "x"})
    assert r.status_code == 422


def test_add_device_blank_name_rejected(client):
    r = client.post("/api/devices", json={"name": "", "type": "mobile"})
    assert r.status_code == 422
