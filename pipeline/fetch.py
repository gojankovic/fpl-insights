import json
from pathlib import Path
from typing import Any, Dict, List

import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PLAYERS_DIR = RAW_DIR / "players"

BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"
PLAYER_SUMMARY_URL = "https://fantasy.premierleague.com/api/element-summary/{player_id}/"


def ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PLAYERS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_bootstrap_static() -> Dict[str, Any]:
    ensure_dirs()
    resp = requests.get(BOOTSTRAP_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    (RAW_DIR / "bootstrap_static.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def fetch_fixtures() -> List[Dict[str, Any]]:
    ensure_dirs()
    resp = requests.get(FIXTURES_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    (RAW_DIR / "fixtures.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def fetch_player_summary(player_id: int) -> Dict[str, Any]:
    ensure_dirs()
    url = PLAYER_SUMMARY_URL.format(player_id=player_id)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    (PLAYERS_DIR / f"{player_id}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data
