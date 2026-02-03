import sqlite3
from typing import List

import pytest

from config import DB_PATH


def _parse_ids(raw: str | None) -> List[int]:
    if not raw:
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def pytest_addoption(parser):
    parser.addoption("--team", action="store", default="")
    parser.addoption("--bench", action="store", default="")
    parser.addoption("--gw", action="store", default="16")
    parser.addoption("--captain", action="store", default="430")
    parser.addoption("--vice", action="store", default="16")
    parser.addoption("--player-id", action="store", default="414")


@pytest.fixture(scope="session")
def gw(pytestconfig) -> int:
    return int(pytestconfig.getoption("--gw"))


@pytest.fixture(scope="session")
def team_ids(pytestconfig) -> List[int]:
    ids = _parse_ids(pytestconfig.getoption("--team"))
    if ids:
        return ids
    return [366, 8, 261, 407, 16, 119, 237, 414, 283, 249, 430]


@pytest.fixture(scope="session")
def bench_ids(pytestconfig) -> List[int]:
    ids = _parse_ids(pytestconfig.getoption("--bench"))
    if ids:
        return ids
    return [470, 242, 72, 347]


@pytest.fixture(scope="session")
def captain_id(pytestconfig) -> int:
    return int(pytestconfig.getoption("--captain"))


@pytest.fixture(scope="session")
def vice_id(pytestconfig) -> int:
    return int(pytestconfig.getoption("--vice"))


@pytest.fixture(scope="session")
def player_id(pytestconfig) -> int:
    return int(pytestconfig.getoption("--player-id"))


@pytest.fixture(scope="session")
def db_available():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
    except sqlite3.Error:
        pytest.skip(f"SQLite DB not available at {DB_PATH}")
