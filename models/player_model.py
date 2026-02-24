import sqlite3
import json
from pathlib import Path
from typing import Tuple, List, Dict, Optional

import numpy as np

from config import DB_PATH

PARAMS_PATH = Path(__file__).resolve().parent / "player_model_params.json"

DEFAULT_MODEL_PARAMS: Dict[str, float] = {
    "history_recent_n": 6,
    "history_long_n": 60,
    "recent_decay": 0.83,
    "w_season": 0.55,
    "w_recent": 0.30,
    "w_anchor": 0.15,
    "shrink_k": 10.0,
    "xgi_weight_gk": 0.00,
    "xgi_weight_def": 0.02,
    "xgi_weight_mid": 0.05,
    "xgi_weight_fwd": 0.08,
    "fixture_w_gk": 0.12,
    "fixture_w_def": 0.16,
    "fixture_w_mid": 0.20,
    "fixture_w_fwd": 0.24,
    "fixture_role_floor_mid": 0.55,
    "fixture_role_floor_fwd": 0.70,
    "fixture_role_ref_mid": 0.70,
    "fixture_role_ref_fwd": 0.85,
    "fixture_role_cap": 1.15,
    "elite_uplift_mid_max": 0.14,
    "elite_uplift_fwd_max": 0.14,
    "elite_xgi_ref_mid": 0.70,
    "elite_xgi_ref_fwd": 0.90,
    "elite_xgi_floor_mid": 0.18,
    "elite_xgi_floor_fwd": 0.30,
    "elite_ppg_ref_mid": 6.0,
    "elite_ppg_ref_fwd": 7.0,
    "elite_starts_ref": 12.0,
    "elite_n_games_ref": 10.0,
    "set_piece_uplift_mid_max": 0.08,
    "set_piece_xa90_ref": 0.25,
    "set_piece_crea90_ref": 35.0,
    "set_piece_xa90_floor": 0.12,
    "set_piece_crea90_floor": 16.0,
    "set_piece_min_starts": 8.0,
    "dgw_minutes_factor": 0.82,
    "std_floor": 0.50,
    "std_fallback_mult": 0.35,
}

_PARAMS_CACHE: Optional[Dict[str, float]] = None


def _get_model_params() -> Dict[str, float]:
    global _PARAMS_CACHE
    if _PARAMS_CACHE is not None:
        return _PARAMS_CACHE

    params = dict(DEFAULT_MODEL_PARAMS)
    if PARAMS_PATH.exists():
        try:
            raw = json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
            for k, v in raw.items():
                if k in params:
                    params[k] = float(v)
        except Exception:
            pass

    _PARAMS_CACHE = params
    return params

def get_player_data(player_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM players WHERE id = ?", (player_id,))
    p = c.fetchone()

    if not p:
        conn.close()
        raise ValueError(f"Player {player_id} not found")

    data = dict(p)
    conn.close()
    return data


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
    conn.close()
    return rows


def get_player_history(
    player_id: int,
    last_n: int = 5,
    up_to_gw: Optional[int] = None,
) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if up_to_gw is None:
        c.execute("""
        SELECT gameweek, total_points, minutes, goals_scored, assists, clean_sheets, bonus_points
        FROM player_history
        WHERE player_id = ?
        ORDER BY gameweek DESC
        LIMIT ?
    """, (player_id, last_n))
    else:
        c.execute("""
        SELECT gameweek, total_points, minutes, goals_scored, assists, clean_sheets, bonus_points
        FROM player_history
        WHERE player_id = ? AND gameweek < ?
        ORDER BY gameweek DESC
        LIMIT ?
    """, (player_id, up_to_gw, last_n))

    rows = c.fetchall()
    conn.close()
    return [
        {
            "gw": r["gameweek"],
            "points": r["total_points"],
            "minutes": r["minutes"],
            "goals": r["goals_scored"],
            "assists": r["assists"],
            "clean_sheets": r["clean_sheets"],
            "bonus": r["bonus_points"],
        }
        for r in rows
    ]


def get_player_fixtures_in_gw(player_id: int, gw: int) -> List[int]:
    """
    Returns a list of fixture difficulties (1–5) for the given player's GW.
    Supports blank GW (empty list) and DGW (two values).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # get player team
    c.execute("SELECT team_id FROM players WHERE id = ?", (player_id,))
    team_row = c.fetchone()
    if not team_row:
        conn.close()
        return []
    team_id = team_row["team_id"]

    # find fixture
    c.execute("""
        SELECT team_h, team_a, difficulty_home, difficulty_away
        FROM fixtures
        WHERE event = ? AND (team_h = ? OR team_a = ?)
    """, (gw, team_id, team_id))

    rows = c.fetchall()
    conn.close()
    if not rows:
        return []

    difficulties = []
    for fx in rows:
        if fx["team_h"] == team_id:
            difficulties.append(fx["difficulty_home"])
        else:
            difficulties.append(fx["difficulty_away"])
    return difficulties


def get_fixture_difficulty(player_id: int, gw: int) -> int:
    """
    Returns difficulty 1–5 for the given player's fixture in GW.
    For DGW, returns the average difficulty.
    """
    diffs = get_player_fixtures_in_gw(player_id, gw)
    if not diffs:
        return 3
    return int(round(float(sum(diffs)) / len(diffs)))


def _estimate_expected_minutes(player: dict, history: List[Dict]) -> float:
    status = player.get("status")
    if status in ("i", "o", "s"):
        return 0.0

    recent_minutes = [h["minutes"] for h in history if h.get("minutes") is not None]
    if recent_minutes:
        # Robust center: median is less sensitive to cameo outliers.
        base_minutes = float(np.median(recent_minutes))
    else:
        base_minutes = 80.0 if (player.get("starts") or 0) >= 3 else 60.0

    chance = player.get("chance_of_playing_next_round")
    if chance is not None:
        base_minutes *= max(0.0, min(float(chance), 100.0)) / 100.0

    # Keep a reasonable floor for consistently starting players.
    starts = int(player.get("starts") or 0)
    chance_pct = 100.0 if chance is None else max(0.0, min(float(chance), 100.0))
    if starts >= 10 and chance_pct >= 75:
        high_minutes_games = [m for m in recent_minutes if m >= 70]
        if len(high_minutes_games) >= 3:
            base_minutes = max(base_minutes, 75.0)

    return min(base_minutes, 90.0)


def _weighted_mean(values: List[float], decay: float = 0.85) -> float:
    if not values:
        return 0.0
    weights = [decay ** i for i in range(len(values))]
    den = float(sum(weights))
    if den <= 0:
        return float(sum(values)) / len(values)
    return float(sum(v * w for v, w in zip(values, weights))) / den


def _xgi_per90(player: dict) -> float:
    if player.get("expected_goal_involvements_per_90") is not None:
        return float(player["expected_goal_involvements_per_90"])

    xg = player.get("expected_goals") or 0.0
    xa = player.get("expected_assists") or 0.0
    minutes = player.get("minutes") or 0
    if minutes <= 0:
        return 0.0
    return float((xg + xa) / minutes * 90.0)


def _position(player: dict) -> str:
    pos_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    return pos_map.get(player.get("element_type"), "MID")


def _safe_float(value: Optional[float], default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def get_player_position(player_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT element_type FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    conn.close()
    pos_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    if not row:
        return "MID"
    return pos_map.get(row["element_type"], "MID")


def predict_player_points(
    player_id: int,
    gw: int,
    params: Optional[Dict[str, float]] = None,
) -> Tuple[float, float]:
    """
    Returns (mean, std) points expectation for player in a given GW.
    """
    cfg = params or _get_model_params()
    p = get_player_data(player_id)
    # Time-sliced history: for GW X, use only data up to GW X-1.
    history_all = get_player_history(
        player_id,
        last_n=int(cfg.get("history_long_n", 60)),
        up_to_gw=gw,
    )
    history_recent = history_all[:int(cfg.get("history_recent_n", 6))]

    # Expected minutes for upcoming GW
    exp_minutes = _estimate_expected_minutes(p, history_recent)

    # Base EP components (per full match)
    season_points = [float(h["points"]) for h in history_all if h.get("points") is not None]
    recent_points = [float(h["points"]) for h in history_recent if h.get("points") is not None]

    season_ppg_asof = (
        float(sum(season_points)) / len(season_points)
        if season_points else float(p.get("points_per_game") or 0.0)
    )
    recent_ppg = _weighted_mean(
        recent_points,
        decay=float(cfg.get("recent_decay", 0.83)),
    ) if recent_points else season_ppg_asof
    anchor_ppg = float(p.get("points_per_game") or season_ppg_asof)

    # Blend season signal + recent trend with a light anchor to bootstrap.
    raw_ep = (
        float(cfg.get("w_season", 0.55)) * season_ppg_asof
        + float(cfg.get("w_recent", 0.30)) * recent_ppg
        + float(cfg.get("w_anchor", 0.15)) * anchor_ppg
    )

    # Bayesian-style shrinkage toward position prior for stability.
    pos = _position(p)
    pos_prior = {"GK": 3.4, "DEF": 3.8, "MID": 4.9, "FWD": 5.2}
    n_games = len(season_points)
    shrink_k = max(1e-6, float(cfg.get("shrink_k", 10.0)))
    shrink = n_games / (n_games + shrink_k)
    base_ep = shrink * raw_ep + (1.0 - shrink) * pos_prior.get(pos, 4.5)

    # xGI bonus scaled by position
    xgi90 = _xgi_per90(p)
    xgi_weight = {
        "GK": float(cfg.get("xgi_weight_gk", 0.00)),
        "DEF": float(cfg.get("xgi_weight_def", 0.02)),
        "MID": float(cfg.get("xgi_weight_mid", 0.05)),
        "FWD": float(cfg.get("xgi_weight_fwd", 0.08)),
    }
    xgi_trust = min(1.0, n_games / 8.0)
    base_ep += xgi90 * xgi_weight.get(pos, 0.05) * xgi_trust

    # Expand premium attacker ceiling without inflating low-sample outliers.
    starts = _safe_float(p.get("starts"), 0.0)
    sample_trust = min(1.0, n_games / max(1e-6, float(cfg.get("elite_n_games_ref", 10.0))))
    start_trust = min(1.0, starts / max(1e-6, float(cfg.get("elite_starts_ref", 12.0))))
    elite_trust = sample_trust * start_trust
    if pos in ("MID", "FWD") and elite_trust > 0:
        xgi_ref = float(cfg.get("elite_xgi_ref_mid" if pos == "MID" else "elite_xgi_ref_fwd", 0.70 if pos == "MID" else 0.90))
        ppg_ref = float(cfg.get("elite_ppg_ref_mid" if pos == "MID" else "elite_ppg_ref_fwd", 6.0 if pos == "MID" else 7.0))
        elite_max = float(cfg.get("elite_uplift_mid_max" if pos == "MID" else "elite_uplift_fwd_max", 0.20 if pos == "MID" else 0.18))
        xgi_floor = float(cfg.get("elite_xgi_floor_mid" if pos == "MID" else "elite_xgi_floor_fwd", 0.18 if pos == "MID" else 0.30))
        xgi_score = 0.0
        if xgi90 > xgi_floor:
            xgi_score = min(1.0, (xgi90 - xgi_floor) / max(1e-6, (xgi_ref - xgi_floor)))
        ppg_score = min(1.0, anchor_ppg / max(1e-6, ppg_ref))
        elite_score = 0.70 * xgi_score + 0.30 * ppg_score
        base_ep *= 1.0 + elite_max * elite_score * elite_trust

    # Creator/set-piece proxy for attacking mids.
    if pos == "MID" and starts >= float(cfg.get("set_piece_min_starts", 8.0)):
        minutes_total = max(1.0, _safe_float(p.get("minutes"), 0.0))
        xa90 = _safe_float(p.get("expected_assists_per_90"), 0.0)
        creativity_total = _safe_float(p.get("creativity"), 0.0)
        creativity90 = creativity_total / minutes_total * 90.0
        xa_floor = float(cfg.get("set_piece_xa90_floor", 0.12))
        crea_floor = float(cfg.get("set_piece_crea90_floor", 16.0))
        xa_score = 0.0
        if xa90 > xa_floor:
            xa_score = min(1.0, (xa90 - xa_floor) / max(1e-6, float(cfg.get("set_piece_xa90_ref", 0.25)) - xa_floor))
        crea_score = 0.0
        if creativity90 > crea_floor:
            crea_score = min(1.0, (creativity90 - crea_floor) / max(1e-6, float(cfg.get("set_piece_crea90_ref", 35.0)) - crea_floor))
        creator_score = 0.65 * xa_score + 0.35 * crea_score
        base_ep *= 1.0 + float(cfg.get("set_piece_uplift_mid_max", 0.12)) * creator_score * elite_trust

    # Fixture adjustment (supports DGW)
    difficulties = get_player_fixtures_in_gw(player_id, gw)
    if not difficulties:
        return 0.0, 0.0

    minutes_per_fixture = exp_minutes
    if len(difficulties) > 1:
        minutes_per_fixture = exp_minutes * float(cfg.get("dgw_minutes_factor", 0.82))
    minutes_factor = min(minutes_per_fixture, 90.0) / 90.0

    ep_total = 0.0
    # Stronger fixture impact so opponent quality matters more.
    fixture_weight_by_pos = {
        "GK": float(cfg.get("fixture_w_gk", 0.12)),
        "DEF": float(cfg.get("fixture_w_def", 0.16)),
        "MID": float(cfg.get("fixture_w_mid", 0.20)),
        "FWD": float(cfg.get("fixture_w_fwd", 0.24)),
    }
    fixture_weight = fixture_weight_by_pos.get(pos, 0.18)

    # MID/FWD fixture sensitivity should depend on attacking profile.
    # This avoids overrating low-xGI midfielders just because they have an easy fixture.
    if pos in ("MID", "FWD"):
        role_floor = float(
            cfg.get(
                "fixture_role_floor_mid" if pos == "MID" else "fixture_role_floor_fwd",
                0.55 if pos == "MID" else 0.70,
            )
        )
        role_ref = max(
            1e-6,
            float(
                cfg.get(
                    "fixture_role_ref_mid" if pos == "MID" else "fixture_role_ref_fwd",
                    0.70 if pos == "MID" else 0.85,
                )
            ),
        )
        role_cap = max(1.0, float(cfg.get("fixture_role_cap", 1.15)))
        role_mult = role_floor + (1.0 - role_floor) * min(1.0, max(0.0, xgi90) / role_ref)
        fixture_weight *= min(role_mult, role_cap)

    for difficulty in difficulties:
        adj = 1 + (3 - difficulty) * fixture_weight
        ep_total += base_ep * minutes_factor * adj

    # STD from history
    points_history = [h["points"] for h in history_recent if h.get("points") is not None]
    if len(points_history) >= 3:
        std = float(np.std(points_history))
    else:
        std = ep_total * float(cfg.get("std_fallback_mult", 0.35))  # fallback variance

    # Position-based variance adjustment
    pos_std_mult = {"GK": 0.75, "DEF": 0.85, "MID": 1.0, "FWD": 1.1}
    std *= pos_std_mult.get(pos, 1.0)

    return max(ep_total, 0.0), max(std, float(cfg.get("std_floor", 0.5)))
