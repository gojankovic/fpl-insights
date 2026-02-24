import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from db.sqlite import get_connection
from models.player_model import predict_player_points


def _position_label(element_type: int | None) -> str:
    return {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}.get(element_type, "?")


def _opponents_map(gw: int) -> Dict[int, List[str]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT f.team_h,
               f.team_a,
               f.difficulty_home,
               f.difficulty_away,
               th.short_name AS team_h_name,
               ta.short_name AS team_a_name
        FROM fixtures f
        JOIN teams th ON th.id = f.team_h
        JOIN teams ta ON ta.id = f.team_a
        WHERE f.event = ?
        """,
        (gw,),
    )
    rows = cur.fetchall()
    conn.close()

    out: Dict[int, List[str]] = {}
    for r in rows:
        home_team = r["team_h"]
        away_team = r["team_a"]
        home_opp = f"{r['team_a_name']}(H,d{r['difficulty_home']})"
        away_opp = f"{r['team_h_name']}(A,d{r['difficulty_away']})"
        out.setdefault(home_team, []).append(home_opp)
        out.setdefault(away_team, []).append(away_opp)
    return out


def _player_pool(include_unavailable: bool, pool_size: int) -> List[Any]:
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT p.id,
               p.first_name,
               p.second_name,
               p.team_id,
               p.element_type,
               p.status,
               p.total_points,
               t.short_name AS team
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
    """
    if not include_unavailable:
        query += " WHERE p.status NOT IN ('i', 's', 'u', 'o')"
    query += " ORDER BY p.total_points DESC LIMIT ?"

    cur.execute(query, (pool_size,))
    rows = cur.fetchall()
    conn.close()
    return rows


def top_players_by_prediction_range(
    gw_from: int,
    gw_to: int,
    top_n: int = 10,
    include_unavailable: bool = False,
    pool_size: int = 250,
) -> List[Dict[str, Any]]:
    gws = list(range(gw_from, gw_to + 1))
    opponents_by_gw = {gw: _opponents_map(gw) for gw in gws}
    players = _player_pool(include_unavailable=include_unavailable, pool_size=pool_size)

    out: List[Dict[str, Any]] = []
    for row in players:
        per_gw: List[Dict[str, Any]] = []
        total = 0.0
        for gw in gws:
            mean, _ = predict_player_points(row["id"], gw)
            opps = opponents_by_gw[gw].get(row["team_id"], ["BLANK"])
            per_gw.append(
                {
                    "gw": gw,
                    "points": float(mean),
                    "opponents": opps,
                }
            )
            total += float(mean)

        out.append(
            {
                "id": row["id"],
                "name": f"{row['first_name']} {row['second_name']}".strip(),
                "team": row["team"],
                "pos": _position_label(row["element_type"]),
                "status": row["status"],
                "predicted_total": total,
                "per_gw": per_gw,
            }
        )

    ranked = sorted(out, key=lambda x: x["predicted_total"], reverse=True)
    return ranked[:top_n]


def render_dashboard(rows: List[Dict[str, Any]], gw_from: int, gw_to: int) -> None:
    gws = list(range(gw_from, gw_to + 1))
    console = Console()
    title = f"Top Predicted Players GW{gw_from}" if gw_from == gw_to else f"Top Predicted Players GW{gw_from}-GW{gw_to}"
    table = Table(title=title)
    table.add_column("#", justify="right")
    table.add_column("Player")
    table.add_column("Team")
    table.add_column("Pos", justify="center")
    table.add_column("Pred Total", justify="right")
    for gw in gws:
        table.add_column(f"GW{gw}", justify="left")

    for i, p in enumerate(rows, start=1):
        gw_cells = []
        for item in p["per_gw"]:
            opp = "/".join(item["opponents"])
            gw_cells.append(f"{item['points']:.1f} {opp}")

        table.add_row(
            str(i),
            p["name"],
            p["team"] or "-",
            p["pos"],
            f"{p['predicted_total']:.2f}",
            *gw_cells,
        )

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Player prediction dashboard in terminal (single GW or GW range)."
    )
    parser.add_argument("--gw", type=int, help="Single target gameweek")
    parser.add_argument("--gw-from", type=int, help="Start GW for range")
    parser.add_argument("--gw-to", type=int, help="End GW for range")
    parser.add_argument("--top", type=int, default=10, help="Number of players to show")
    parser.add_argument("--pool", type=int, default=250, help="Player pool size to rank from")
    parser.add_argument(
        "--include-unavailable",
        action="store_true",
        help="Include injured/suspended/unavailable players in ranking",
    )

    args = parser.parse_args()
    if args.gw is None and (args.gw_from is None or args.gw_to is None):
        parser.error("Provide either --gw OR both --gw-from and --gw-to.")

    if args.gw is not None:
        gw_from = args.gw
        gw_to = args.gw
    else:
        gw_from = args.gw_from
        gw_to = args.gw_to
        if gw_to < gw_from:
            parser.error("--gw-to must be >= --gw-from.")

    rows = top_players_by_prediction_range(
        gw_from=gw_from,
        gw_to=gw_to,
        top_n=args.top,
        include_unavailable=args.include_unavailable,
        pool_size=args.pool,
    )
    render_dashboard(rows=rows, gw_from=gw_from, gw_to=gw_to)


if __name__ == "__main__":
    main()
