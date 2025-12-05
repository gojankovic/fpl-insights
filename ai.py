import argparse
import json

from utils.ai_service import (
    captaincy_advice,
    transfer_advice,
    freehit_advice,
    h2h_prediction
)


def run_captaincy(args):
    result = captaincy_advice(
        entry_id=args.team,
        gw=args.gw
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def run_transfers(args):
    result = transfer_advice(
        entry_id=args.team,
        gw=args.gw,
        candidate_pool_size=args.pool
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def run_freehit(args):
    result = freehit_advice(
        gw=args.gw,
        budget=args.budget,
        candidate_pool_size=args.pool
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def run_h2h(args):
    baseline = None

    if args.mc:
        from utils.montecarlo_service import calc_expected_points
        baseline = {
            "team_a_expected": calc_expected_points(args.teamA, args.gw),
            "team_b_expected": calc_expected_points(args.teamB, args.gw),
        }

    result = h2h_prediction(
        entry_a=args.teamA,
        entry_b=args.teamB,
        gw=args.gw,
        mc_baseline=baseline
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="FPL AI Tools CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # CAPTAINCY
    p_cap = sub.add_parser("captaincy", help="AI captaincy advisor")
    p_cap.add_argument("--team", type=int, required=True)
    p_cap.add_argument("--gw", type=int, required=True)
    p_cap.set_defaults(func=run_captaincy)

    # TRANSFERS
    p_trans = sub.add_parser("transfers", help="AI transfer advisor")
    p_trans.add_argument("--team", type=int, required=True)
    p_trans.add_argument("--gw", type=int, required=True)
    p_trans.add_argument("--pool", type=int, default=60)
    p_trans.set_defaults(func=run_transfers)

    # FREEHIT
    fh = sub.add_parser("freehit", help="AI Free Hit squad builder")
    fh.add_argument("--gw", type=int, required=True)
    fh.add_argument("--pool", type=int, default=150)
    fh.add_argument("--budget", type=float, default=100.0)
    fh.set_defaults(func=run_freehit)

    #HWH
    h2h = sub.add_parser("h2h", help="AI H2H squad builder")
    h2h.add_argument("--teamA", type=int, required=True)
    h2h.add_argument("--teamB", type=int, required=True)
    h2h.add_argument("--gw", type=int, required=True)
    h2h.add_argument("--mc", action="store_true", help="Include Monte Carlo baseline expected points")
    h2h.set_defaults(func=run_h2h)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
