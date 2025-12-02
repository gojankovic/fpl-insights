import json
from pathlib import Path
from typing import Any, Dict


def extract_keys(obj: Any):
    if isinstance(obj, dict):
        return set(obj.keys())
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return set(obj[0].keys())
    return set()


def check_schema_change(raw_dir: Path, name: str, new_data: Dict[str, Any]):
    path = raw_dir / f"{name}.json"
    if not path.exists():
        return

    old_data = json.loads(path.read_text(encoding="utf-8"))

    if name == "bootstrap_static":
        old_keys = extract_keys(old_data)
        new_keys = extract_keys(new_data)

        added = new_keys - old_keys
        removed = old_keys - new_keys

        if added or removed:
            print(f"[SCHEMA] bootstrap_static top-level changed. Added={added}, Removed={removed}")

        # elements
        old_el = extract_keys(old_data.get("elements", []))
        new_el = extract_keys(new_data.get("elements", []))
        added_el = new_el - old_el
        removed_el = old_el - new_el
        if added_el or removed_el:
            print(f"[SCHEMA] elements struct changed. Added={added_el}, Removed={removed_el}")
