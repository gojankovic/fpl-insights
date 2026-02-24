import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from rich.console import Console
from rich.table import Table

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from db.sqlite import get_connection
from models.player_model import predict_player_points


def _position_label(element_type: int | None) -> str:
    return {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}.get(element_type, "?")


def _fixture_count_map(gw: int) -> Dict[int, int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT team_h AS team_id, COUNT(*) AS cnt
        FROM fixtures
        WHERE event = ?
        GROUP BY team_h
        """,
        (gw,),
    )
    team_h_rows = cur.fetchall()

    cur.execute(
        """
        SELECT team_a AS team_id, COUNT(*) AS cnt
        FROM fixtures
        WHERE event = ?
        GROUP BY team_a
        """,
        (gw,),
    )
    team_a_rows = cur.fetchall()
    conn.close()

    counts: Dict[int, int] = {}
    for r in team_h_rows:
        counts[r["team_id"]] = counts.get(r["team_id"], 0) + int(r["cnt"])
    for r in team_a_rows:
        counts[r["team_id"]] = counts.get(r["team_id"], 0) + int(r["cnt"])
    return counts


def _simulate_player_distribution(mean: float, std: float, n_sims: int) -> Dict[str, float]:
    if mean <= 0:
        return {"expected": 0.0, "p75": 0.0, "p90": 0.0}

    samples = np.random.normal(loc=mean, scale=max(std, 0.0), size=n_sims)
    samples = np.clip(samples, 0, None)
    return {
        "expected": float(np.mean(samples)),
        "p75": float(np.percentile(samples, 75)),
        "p90": float(np.percentile(samples, 90)),
    }


def top_players_by_prediction(
    gw: int,
    top_n: int = 10,
    n_sims: int = 5000,
    include_unavailable: bool = False,
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT p.id,
               p.first_name,
               p.second_name,
               p.team_id,
               p.element_type,
               p.status,
               t.short_name AS team
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
    """
    if not include_unavailable:
        query += " WHERE p.status NOT IN ('i', 's', 'u', 'o')"

    cur.execute(query)
    players = cur.fetchall()
    conn.close()
    fixture_counts = _fixture_count_map(gw)

    out: List[Dict[str, Any]] = []
    for row in players:
        pid = row["id"]
        mean, std = predict_player_points(pid, gw)
        fixtures = fixture_counts.get(row["team_id"], 0)
        dist = _simulate_player_distribution(mean, std, n_sims=n_sims)

        out.append(
            {
                "id": pid,
                "name": f"{row['first_name']} {row['second_name']}".strip(),
                "team": row["team"],
                "pos": _position_label(row["element_type"]),
                "status": row["status"],
                "fixtures": fixtures,
                "predicted_points": float(mean),
                "expected_points_mc": dist["expected"],
                "p75_mc": dist["p75"],
                "p90_mc": dist["p90"],
            }
        )

    ranked = sorted(out, key=lambda x: x["expected_points_mc"], reverse=True)
    return ranked[:top_n]


def render_dashboard(rows: List[Dict[str, Any]], gw: int) -> None:
    console = Console()
    table = Table(title=f"Top Predicted Players for GW{gw}")
    table.add_column("#", justify="right")
    table.add_column("Player")
    table.add_column("Team")
    table.add_column("Pos", justify="center")
    table.add_column("Fx", justify="right")
    table.add_column("Mean", justify="right")
    table.add_column("MC Exp", justify="right")
    table.add_column("P75", justify="right")
    table.add_column("P90", justify="right")

    for i, p in enumerate(rows, start=1):
        table.add_row(
            str(i),
            p["name"],
            p["team"] or "-",
            p["pos"],
            str(p["fixtures"]),
            f"{p['predicted_points']:.2f}",
            f"{p['expected_points_mc']:.2f}",
            f"{p['p75_mc']:.2f}",
            f"{p['p90_mc']:.2f}",
        )

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Player prediction dashboard (Top N for target GW)."
    )
    parser.add_argument("--gw", type=int, required=True, help="Target gameweek")
    parser.add_argument("--top", type=int, default=10, help="Number of players to show")
    parser.add_argument("--sims", type=int, default=5000, help="Monte Carlo simulations")
    parser.add_argument(
        "--include-unavailable",
        action="store_true",
        help="Include injured/suspended/unavailable players in ranking",
    )

    args = parser.parse_args()
    rows = top_players_by_prediction(
        gw=args.gw,
        top_n=args.top,
        n_sims=args.sims,
        include_unavailable=args.include_unavailable,
    )
    render_dashboard(rows, gw=args.gw)


if __name__ == "__main__":
    main()
