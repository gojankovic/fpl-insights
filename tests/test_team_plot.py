import sqlite3
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import DB_PATH

def get_player_data(pid):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM players WHERE id = ?", (pid,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise ValueError(f"Player {pid} not found.")

    return dict(row)


def get_fixture_difficulty(pid, gw):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Player's team id
    cur.execute("SELECT team_id FROM players WHERE id = ?", (pid,))
    team_id = cur.fetchone()["team_id"]

    # Fixture for GW
    cur.execute("""
        SELECT team_h, team_a, difficulty_home, difficulty_away
        FROM fixtures
        WHERE event = ? AND (team_h = ? OR team_a = ?)
    """, (gw, team_id, team_id))

    fx = cur.fetchone()
    conn.close()

    if not fx:
        return 3  # neutral fallback

    return fx["difficulty_home"] if fx["team_h"] == team_id else fx["difficulty_away"]


def get_history(pid, last_n=5):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT total_points
        FROM player_history
        WHERE player_id = ?
        ORDER BY gameweek DESC
        LIMIT ?
    """, (pid, last_n))

    rows = cur.fetchall()
    conn.close()

    return [r["total_points"] for r in rows if r["total_points"] is not None]


def predict_player_points(pid, gw):
    p = get_player_data(pid)

    # Expected minutes
    if p["status"] in ("i", "o"):   # injured/out
        exp_minutes = 0
    else:
        exp_minutes = 80 if (p.get("starts", 0) or 0) >= 3 else 60

    # Base signals
    ppg = p["points_per_game"] or 0
    form = p["form"] or ppg
    xgi = (p.get("expected_goals", 0) or 0) + (p.get("expected_assists", 0) or 0)

    base_ep = 0.5 * ppg + 0.3 * form + 0.2 * xgi

    # Fixture adjustment
    difficulty = get_fixture_difficulty(pid, gw)
    adj = 1 + (3 - difficulty) * 0.1
    ep = base_ep * adj

    # STD
    hist = get_history(pid)
    if len(hist) >= 3:
        std = float(np.std(hist))
    else:
        std = ep * 0.35  # fallback variance

    return ep, std


def simulate_team(player_ids, gw, n_sims=10000):
    team_samples = np.zeros(n_sims)

    for pid in player_ids:
        mean, std = predict_player_points(pid, gw)
        samples = np.random.normal(mean, std, n_sims)
        samples = np.clip(samples, 0, None)
        team_samples += samples

    return team_samples


if __name__ == "__main__":
    #my team
    team = [366, 8, 261, 407, 16, 119, 237, 414, 283, 249, 430]
    gw = 18

    samples = simulate_team(team, gw)

    plt.figure(figsize=(10, 6))
    plt.hist(samples, bins=60, edgecolor="black")
    plt.title("Team Points Distribution (Basic MC)")
    plt.xlabel("Points")
    plt.ylabel("Frequency")
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save output PNG
    OUTPUT_PATH = "team_distribution.png"
    plt.savefig(OUTPUT_PATH)

    print(f"Histogram saved to: {OUTPUT_PATH}")
