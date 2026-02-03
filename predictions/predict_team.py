import argparse
from typing import List, Optional

from predictions.team_basic import predict_team_points
from predictions.team_advanced import predict_team_points_advanced


def _parse_ids(raw: str) -> List[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def predict_team(
    starting: List[int],
    gw: int,
    mode: str = "advanced",
    bench: Optional[List[int]] = None,
    captain_id: Optional[int] = None,
    vice_captain_id: Optional[int] = None,
    triple_captain: bool = False,
    bench_boost: bool = False,
    n_sims: Optional[int] = None,
):
    """
    Single entrypoint for team prediction.
    mode: "basic" | "advanced"
    """
    if mode == "basic":
        return predict_team_points(starting, gw, n_sims=n_sims or 10000)

    return predict_team_points_advanced(
        starting=starting,
        gw=gw,
        captain_id=captain_id,
        vice_captain_id=vice_captain_id,
        bench=bench,
        triple_captain=triple_captain,
        bench_boost=bench_boost,
        n_sims=n_sims,
    )


def main():
    parser = argparse.ArgumentParser(description="FPLInsights Team Prediction")
    parser.add_argument("--team", required=True, help="Comma-separated 11 player IDs")
    parser.add_argument("--gw", type=int, required=True)
    parser.add_argument("--mode", choices=["basic", "advanced"], default="advanced")
    parser.add_argument("--bench", default="", help="Comma-separated 4 bench player IDs")
    parser.add_argument("--captain", type=int, default=None)
    parser.add_argument("--vice", type=int, default=None)
    parser.add_argument("--triple-captain", action="store_true")
    parser.add_argument("--bench-boost", action="store_true")
    parser.add_argument("--sims", type=int, default=None)

    args = parser.parse_args()

    starting = _parse_ids(args.team)
    bench = _parse_ids(args.bench) if args.bench else None

    dist = predict_team(
        starting=starting,
        gw=args.gw,
        mode=args.mode,
        bench=bench,
        captain_id=args.captain,
        vice_captain_id=args.vice,
        triple_captain=args.triple_captain,
        bench_boost=args.bench_boost,
        n_sims=args.sims,
    )

    print(dist.summary())


if __name__ == "__main__":
    main()
