import numpy as np
from db.sqlite import get_connection
from utils.ai_data_builder import build_squad_for_gw
from models.monte_carlo import MonteCarlo


def _player_expected_points(player_id: int, last_n: int = 5) -> float:
    """
    Estimate expected points for a player based on last N GWs.
    Falls back gracefully if player has few matches.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT total_points
        FROM player_history
        WHERE player_id = ?
        ORDER BY gameweek DESC
        LIMIT ?
    """, (player_id, last_n))

    rows = [r["total_points"] for r in cur.fetchall()]
    conn.close()

    if not rows:
        return 2.0  # minimal safe fallback

    # Mean of last N matches
    return float(np.mean(rows))


def calc_expected_points(entry_id: int, gw: int) -> float:
    """
    Returns expected points for TEAM for the target GW.
    Uses simple baseline:
      - For each player: mean(points last 5 matches)
      - Sum XI (bench ignored for now)
      - Add captain multipler
      - Run Monte Carlo around that sum
    """

    # ============================
    # 1) Load last valid squad
    # ============================
    squad = build_squad_for_gw(entry_id, gw)

    total_mean = 0.0
    total_std = 0.0

    # ============================================
    # 2) Compute mean expectation per player
    # ============================================
    for p in squad:
        base = _player_expected_points(p["id"], last_n=5)

        # Basic minutes adjustment:
        minutes_factor = 1.0
        last_gws = p["gw_history"]
        if last_gws:
            if last_gws[-1]["minutes"] < 30:
                minutes_factor = 0.4
            elif last_gws[-1]["minutes"] < 60:
                minutes_factor = 0.7

        expected = base * minutes_factor

        # add captain multiplier
        expected *= p["multiplier"]

        total_mean += expected

        # simple std heuristic: 40% variance
        total_std += (expected * 0.4)

    # ============================================
    # 3) MC simulation on total team score
    # ============================================
    mc = MonteCarlo(n_sims=5000)
    dist = mc.simulate(mean=total_mean, std=total_std)

    return dist.expected
