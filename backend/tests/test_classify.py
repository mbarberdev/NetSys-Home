import pytest


@pytest.mark.parametrize("text,expected_in", [
    ("block my gaming console",       {"block", "schedule_block"}),
    ("isolate that smart bulb",       {"isolate"}),
    ("create a guest network",        {"guest_network"}),
    ("turn off the kid's iPad at 9pm", {"schedule_block", "block"}),
])
def test_classify_predicts_a_known_action(client, text, expected_in):
    r = client.post("/api/classify", json={"text": text})
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == text
    assert body["predicted_action"] in {"block", "isolate", "guest_network", "schedule_block"}
    assert body["model"] in {"random_forest", "stub"}


def test_classify_empty_text(client):
    r = client.post("/api/classify", json={"text": ""})
    assert r.status_code == 422


def test_classify_missing_text(client):
    r = client.post("/api/classify", json={})
    assert r.status_code == 422
