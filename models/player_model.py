import sqlite3
import numpy as np
from typing import Tuple
from config import DB_PATH

def get_player_data(player_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM players WHERE id = ?", (player_id,))
    p = c.fetchone()

    if not p:
        raise ValueError(f"Player {player_id} not found")

    return dict(p)


def get_player_history_points(player_id: int, last_n: int = 5) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT total_points
        FROM player_history
        WHERE player_id = ?
        ORDER BY gameweek DESC
        LIMIT ?
    """, (player_id, last_n))

    rows = [r["total_points"] for r in c.fetchall() if r["total_points"] is not None]
    return rows


def get_fixture_difficulty(player_id: int, gw: int) -> int:
    """
    Returns difficulty 1–5 for the given player's fixture in GW.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # get player team
    c.execute("SELECT team_id FROM players WHERE id = ?", (player_id,))
    team_id = c.fetchone()["team_id"]

    # find fixture
    c.execute("""
        SELECT team_h, team_a, difficulty_home, difficulty_away
        FROM fixtures
        WHERE event = ? AND (team_h = ? OR team_a = ?)
    """, (gw, team_id, team_id))

    fx = c.fetchone()
    if not fx:
        return 3  # neutral fallback

    if fx["team_h"] == team_id:
        return fx["difficulty_home"]
    else:
        return fx["difficulty_away"]


def predict_player_points(player_id: int, gw: int) -> Tuple[float, float]:
    """
    Returns (mean, std) points expectation for player in a given GW.
    """
    p = get_player_data(player_id)

    # Expected minutes
    if p["status"] in ("i", "o"):  # injured/out
        exp_minutes = 0
    else:
        exp_minutes = 80 if (p.get("starts") or 0) >= 3 else 60

    # Base EP components
    ppg = p["points_per_game"] or 0
    form = p["form"] or ppg
    xgi = (p.get("expected_goals", 0) + p.get("expected_assists", 0))

    base_ep = 0.5 * ppg + 0.3 * form + 0.2 * xgi

    # Fixture adjustment
    difficulty = get_fixture_difficulty(player_id, gw)
    adj = 1 + (3 - difficulty) * 0.1
    ep = base_ep * adj

    # STD from history
    history = get_player_history_points(player_id, last_n=5)
    if len(history) >= 3:
        std = float(np.std(history))
    else:
        std = ep * 0.35  # fallback variance

    return ep, std
