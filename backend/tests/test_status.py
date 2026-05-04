def test_status_disconnected_by_default(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["openwrt"] == "disconnected"
    assert body["app_version"]
    assert body["classifier"] in {"random_forest", "stub"}


def test_status_when_router_connected(client, fake_openwrt):
    fake_openwrt["connected"] = True
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["openwrt"] == "connected"
    assert body["version"] == "23.05.5"
    assert body["hostname"] == "openwrt"
