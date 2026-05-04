import json
import os
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "policies.json"


def load_policies() -> list[dict]:
    if not DATA_PATH.exists():
        save_policies([])
        return []
    with open(DATA_PATH) as f:
        return json.load(f)


def save_policies(policies: list[dict]) -> None:
    tmp = DATA_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(policies, f, indent=2)
    os.replace(tmp, DATA_PATH)


def get_all() -> list[dict]:
    return load_policies()


def get_by_id(policy_id: int) -> dict | None:
    return next((p for p in load_policies() if p["id"] == policy_id), None)


def add(policy: dict) -> dict:
    policies = load_policies()
    next_id = max((p["id"] for p in policies), default=0) + 1
    policy = {"id": next_id, **policy}
    policies.append(policy)
    save_policies(policies)
    return policy


def delete(policy_id: int) -> bool:
    policies = load_policies()
    filtered = [p for p in policies if p["id"] != policy_id]
    if len(filtered) == len(policies):
        return False
    save_policies(filtered)
    return True
