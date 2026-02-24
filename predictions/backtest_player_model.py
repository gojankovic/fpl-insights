import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
from rich.console import Console
from rich.table import Table

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from db.sqlite import get_connection
from models.player_model import predict_player_points


def _position_label(element_type: int | None) -> str:
    return {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}.get(element_type, "?")


def _load_eval_rows(gw_from: int, gw_to: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ph.player_id,
               ph.gameweek,
               ph.total_points,
               p.first_name,
               p.second_name,
               p.element_type,
               t.short_name AS team
        FROM player_history ph
        JOIN players p ON p.id = ph.player_id
        LEFT JOIN teams t ON t.id = p.team_id
        WHERE ph.gameweek BETWEEN ? AND ?
        """,
        (gw_from, gw_to),
    )
    rows = cur.fetchall()
    conn.close()

    out = []
    for r in rows:
        out.append(
            {
                "player_id": r["player_id"],
                "gw": r["gameweek"],
                "actual": float(r["total_points"] or 0.0),
                "name": f"{r['first_name']} {r['second_name']}".strip(),
                "pos": _position_label(r["element_type"]),
                "team": r["team"] or "-",
            }
        )
    return out


def _metrics(rows: List[Tuple[float, float]]) -> Dict[str, float]:
    if not rows:
        return {"mae": 0.0, "rmse": 0.0, "bias": 0.0}
    errors = np.array([pred - actual for pred, actual in rows], dtype=float)
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors ** 2))),
        "bias": float(np.mean(errors)),
    }


def run_backtest(gw_from: int, gw_to: int) -> Dict[str, Any]:
    eval_rows = _load_eval_rows(gw_from, gw_to)
    overall_pairs: List[Tuple[float, float]] = []
    by_pos_pairs: Dict[str, List[Tuple[float, float]]] = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    misses: List[Dict[str, Any]] = []

    for row in eval_rows:
        pred, _ = predict_player_points(row["player_id"], row["gw"])
        actual = row["actual"]
        overall_pairs.append((pred, actual))
        by_pos_pairs.setdefault(row["pos"], []).append((pred, actual))

        misses.append(
            {
                "name": row["name"],
                "team": row["team"],
                "pos": row["pos"],
                "gw": row["gw"],
                "pred": pred,
                "actual": actual,
                "abs_err": abs(pred - actual),
            }
        )

    worst = sorted(misses, key=lambda x: x["abs_err"], reverse=True)[:15]
    return {
        "overall": _metrics(overall_pairs),
        "by_pos": {pos: _metrics(pairs) for pos, pairs in by_pos_pairs.items()},
        "n": len(overall_pairs),
        "worst": worst,
    }


def render(result: Dict[str, Any], gw_from: int, gw_to: int):
    console = Console()
    title = f"Player Model Backtest GW{gw_from}-GW{gw_to} (n={result['n']})"

    t = Table(title=title)
    t.add_column("Scope")
    t.add_column("MAE", justify="right")
    t.add_column("RMSE", justify="right")
    t.add_column("Bias", justify="right")

    ov = result["overall"]
    t.add_row("ALL", f"{ov['mae']:.3f}", f"{ov['rmse']:.3f}", f"{ov['bias']:.3f}")
    for pos in ["GK", "DEF", "MID", "FWD"]:
        m = result["by_pos"][pos]
        t.add_row(pos, f"{m['mae']:.3f}", f"{m['rmse']:.3f}", f"{m['bias']:.3f}")
    console.print(t)

    w = Table(title="Worst 15 Misses")
    w.add_column("GW", justify="right")
    w.add_column("Player")
    w.add_column("Team")
    w.add_column("Pos", justify="center")
    w.add_column("Pred", justify="right")
    w.add_column("Actual", justify="right")
    w.add_column("AbsErr", justify="right")
    for row in result["worst"]:
        w.add_row(
            str(row["gw"]),
            row["name"],
            row["team"],
            row["pos"],
            f"{row['pred']:.2f}",
            f"{row['actual']:.2f}",
            f"{row['abs_err']:.2f}",
        )
    console.print(w)


def main():
    parser = argparse.ArgumentParser(description="Backtest player predicted points vs actual points.")
    parser.add_argument("--gw-from", type=int, required=True)
    parser.add_argument("--gw-to", type=int, required=True)
    args = parser.parse_args()

    if args.gw_to < args.gw_from:
        parser.error("--gw-to must be >= --gw-from")

    result = run_backtest(args.gw_from, args.gw_to)
    render(result, args.gw_from, args.gw_to)


if __name__ == "__main__":
    main()
