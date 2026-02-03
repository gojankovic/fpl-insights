import json
from pathlib import Path
from typing import Any, Dict, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PLAYERS_DIR = RAW_DIR / "players"

BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"
PLAYER_SUMMARY_URL = "https://fantasy.premierleague.com/api/element-summary/{player_id}/"

DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3


def _requests_session(retries: int = DEFAULT_RETRIES) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def create_session(retries: int = DEFAULT_RETRIES) -> requests.Session:
    return _requests_session(retries=retries)


def ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PLAYERS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_bootstrap_static(write: bool = True) -> Dict[str, Any]:
    ensure_dirs()
    session = _requests_session()
    resp = session.get(BOOTSTRAP_URL, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if write:
        (RAW_DIR / "bootstrap_static.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
    return data


def fetch_fixtures() -> List[Dict[str, Any]]:
    ensure_dirs()
    session = _requests_session()
    resp = session.get(FIXTURES_URL, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    (RAW_DIR / "fixtures.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def fetch_player_summary(player_id: int, session: requests.Session | None = None) -> Dict[str, Any]:
    ensure_dirs()
    url = PLAYER_SUMMARY_URL.format(player_id=player_id)
    sess = session or _requests_session()
    resp = sess.get(url, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    (PLAYERS_DIR / f"{player_id}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data
