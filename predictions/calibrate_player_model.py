import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
from rich.console import Console
from rich.table import Table

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from db.sqlite import get_connection
from models.player_model import predict_player_points, DEFAULT_MODEL_PARAMS


PARAMS_PATH = Path(__file__).resolve().parents[1] / "models" / "player_model_params.json"


def _load_eval_rows(gw_from: int, gw_to: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT player_id, gameweek, total_points
        FROM player_history
        WHERE gameweek BETWEEN ? AND ?
        """,
        (gw_from, gw_to),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "player_id": r["player_id"],
            "gw": int(r["gameweek"]),
            "actual": float(r["total_points"] or 0.0),
        }
        for r in rows
    ]


def _mae(params: Dict[str, float], rows: List[Dict[str, Any]]) -> float:
    errs = []
    for row in rows:
        pred, _ = predict_player_points(row["player_id"], row["gw"], params=params)
        errs.append(abs(pred - row["actual"]))
    return float(np.mean(errs)) if errs else 0.0


def _build_grid() -> List[Dict[str, float]]:
    grid: List[Dict[str, float]] = []
    for recent_decay in [0.80, 0.86]:
        for w_recent in [0.22, 0.30]:
            w_anchor = 0.15
            w_season = 1.0 - w_recent - w_anchor
            for shrink_k in [8.0, 12.0]:
                for fixture_scale in [0.90, 1.10]:
                    for dgw_factor in [0.78, 0.84]:
                        p = dict(DEFAULT_MODEL_PARAMS)
                        p["recent_decay"] = recent_decay
                        p["w_recent"] = w_recent
                        p["w_anchor"] = w_anchor
                        p["w_season"] = w_season
                        p["shrink_k"] = shrink_k
                        p["dgw_minutes_factor"] = dgw_factor
                        p["fixture_w_gk"] *= fixture_scale
                        p["fixture_w_def"] *= fixture_scale
                        p["fixture_w_mid"] *= fixture_scale
                        p["fixture_w_fwd"] *= fixture_scale
                        grid.append(p)
    return grid


def calibrate(
    gw_from: int,
    gw_to: int,
    sample_size: int,
    seed: int,
) -> Dict[str, Any]:
    rows = _load_eval_rows(gw_from, gw_to)
    rng = random.Random(seed)
    if sample_size > 0 and sample_size < len(rows):
        rows = rng.sample(rows, sample_size)

    baseline_params = dict(DEFAULT_MODEL_PARAMS)
    baseline_mae = _mae(baseline_params, rows)

    grid = _build_grid()
    scored: List[Tuple[float, Dict[str, float]]] = []
    for params in grid:
        score = _mae(params, rows)
        scored.append((score, params))
    scored.sort(key=lambda x: x[0])

    best_mae, best_params = scored[0]
    return {
        "baseline_mae": baseline_mae,
        "best_mae": best_mae,
        "improvement_pct": (baseline_mae - best_mae) / baseline_mae * 100.0 if baseline_mae > 0 else 0.0,
        "best_params": best_params,
        "top5": scored[:5],
        "n_rows": len(rows),
        "gw_from": gw_from,
        "gw_to": gw_to,
        "sample_size": sample_size,
        "seed": seed,
    }


def render(result: Dict[str, Any]) -> None:
    console = Console()
    t = Table(title="Player Model Calibration")
    t.add_column("Metric")
    t.add_column("Value", justify="right")
    t.add_row("GW range", f"{result['gw_from']}-{result['gw_to']}")
    t.add_row("Rows used", str(result["n_rows"]))
    t.add_row("Baseline MAE", f"{result['baseline_mae']:.4f}")
    t.add_row("Best MAE", f"{result['best_mae']:.4f}")
    t.add_row("Improvement", f"{result['improvement_pct']:.2f}%")
    console.print(t)

    top = Table(title="Top 5 Parameter Sets")
    top.add_column("#", justify="right")
    top.add_column("MAE", justify="right")
    top.add_column("w_season", justify="right")
    top.add_column("w_recent", justify="right")
    top.add_column("decay", justify="right")
    top.add_column("shrink_k", justify="right")
    top.add_column("fix_mid", justify="right")
    top.add_column("dgw", justify="right")
    for i, (mae, params) in enumerate(result["top5"], start=1):
        top.add_row(
            str(i),
            f"{mae:.4f}",
            f"{params['w_season']:.2f}",
            f"{params['w_recent']:.2f}",
            f"{params['recent_decay']:.2f}",
            f"{params['shrink_k']:.1f}",
            f"{params['fixture_w_mid']:.3f}",
            f"{params['dgw_minutes_factor']:.2f}",
        )
    console.print(top)


def main():
    parser = argparse.ArgumentParser(description="Calibrate player model parameters with grid search.")
    parser.add_argument("--gw-from", type=int, required=True)
    parser.add_argument("--gw-to", type=int, required=True)
    parser.add_argument("--sample-size", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--write", action="store_true", help="Write best params to models/player_model_params.json")
    args = parser.parse_args()

    if args.gw_to < args.gw_from:
        parser.error("--gw-to must be >= --gw-from")

    result = calibrate(
        gw_from=args.gw_from,
        gw_to=args.gw_to,
        sample_size=args.sample_size,
        seed=args.seed,
    )
    render(result)

    if args.write:
        PARAMS_PATH.write_text(
            json.dumps(result["best_params"], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        Console().print(f"[green]Saved calibrated params to {PARAMS_PATH}[/green]")


if __name__ == "__main__":
    main()
