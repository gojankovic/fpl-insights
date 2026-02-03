import argparse
import os
import json

import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import matplotlib
matplotlib.use("Agg")  # headless backend za PNG
import matplotlib.pyplot as plt
import pandas as pd

from db.sqlite import get_connection


# ---------------------------
# API helpers
# ---------------------------

DEFAULT_TIMEOUT = 20


def _requests_session(retries: int = 3) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_SESSION = _requests_session()


def _get_json(url: str) -> dict:
    resp = _SESSION.get(url, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def api_entry(entry_id: int) -> dict:
    return _get_json(f"https://fantasy.premierleague.com/api/entry/{entry_id}/")


def api_history(entry_id: int) -> dict:
    return _get_json(f"https://fantasy.premierleague.com/api/entry/{entry_id}/history/")


def api_picks(entry_id: int, gw: int) -> dict:
    return _get_json(
        f"https://fantasy.premierleague.com/api/entry/{entry_id}/event/{gw}/picks/"
    )


# ---------------------------
# Chips
# ---------------------------

def extract_chips(history_json: dict) -> dict[int, str]:
    """
    Returns dict: { gw: "WC"/"BB"/"TC"/"FH" }
    """
    chip_map = {
        "wildcard": "WC",
        "freehit": "FH",
        "bboost": "BB",
        "3xc": "TC",
    }
    result: dict[int, str] = {}

    for chip in history_json.get("chips", []):
        gw = chip["event"]
        name = chip["name"]
        label = chip_map.get(name, name.upper())
        result[gw] = label

    return result


# ---------------------------
# DB helpers
# ---------------------------

POS_MAP = {
    1: "GK",
    2: "DEF",
    3: "MID",
    4: "FWD",
}


def fetch_player_meta(conn, player_id: int):
    """
    Fetch basic player info (name, team short, position string) from SQLite.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.id,
               p.first_name,
               p.second_name,
               p.team_id,
               p.element_type,
               t.short_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.id = ?
        """,
        (player_id,),
    )
    row = cur.fetchone()
    if row is None:
        return {
            "id": player_id,
            "name": f"#{player_id}",
            "team": None,
            "pos": None,
        }

    pid = row["id"]
    full_name = (row["first_name"] + " " + row["second_name"]).strip()
    team_short = row["short_name"]
    pos = POS_MAP.get(row["element_type"], None)

    return {
        "id": pid,
        "name": full_name,
        "team": team_short,
        "pos": pos,
    }


def fetch_player_gw_stats(conn, player_id: int, gw: int):
    """
    Fetch per-GW stats for player from player_history.
    We keep it minimal: total_points + goals + assists + clean_sheets + bonus.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT total_points,
               goals_scored,
               assists,
               clean_sheets,
               bonus_points
        FROM player_history
        WHERE player_id = ? AND gameweek = ?
        """,
        (player_id, gw),
    )
    row = cur.fetchone()
    if row is None:
        return {
            "total_points": 0,
            "goals_scored": 0,
            "assists": 0,
            "clean_sheets": 0,
            "bonus_points": 0,
        }

    return {
        "total_points": row["total_points"],
        "goals_scored": row["goals_scored"],
        "assists": row["assists"],
        "clean_sheets": row["clean_sheets"],
        "bonus_points": row["bonus_points"],
    }


# ---------------------------
# Rank plot
# ---------------------------

def rank_plot(df: pd.DataFrame, chips: dict[int, str], outdir: str, entry_id: int) -> None:
    """
    Renders rank_progression.png using df["event"] and df["overall_rank"].
    """
    plt.figure(figsize=(14, 6))
    plt.plot(df["event"], df["overall_rank"], marker="o", linewidth=3, color="#1DA1F2")
    plt.gca().invert_yaxis()

    plt.xticks(df["event"], [f"GW{gw}" for gw in df["event"]])
    plt.grid(axis="y", linestyle="--", alpha=0.3)
    plt.grid(axis="x", linestyle="--", alpha=0.07)
    plt.title(f"Rank progression for entry {entry_id}")
    plt.xlabel("Gameweek")
    plt.ylabel("Overall Rank")

    # chips
    for gw, label in chips.items():
        if gw in df["event"].values:
            plt.axvline(x=gw, color="gray", linestyle="--", linewidth=1)
            plt.text(
                gw,
                df["overall_rank"].max() * 1.01,
                label,
                ha="center",
                fontsize=10,
            )

    # labels on points
    for _, row in df.iterrows():
        plt.text(
            row["event"],
            row["overall_rank"],
            f"{row['overall_rank']:,}",
            fontsize=7,
            ha="center",
        )

    out_path = os.path.join(outdir, "rank_progression.png")
    plt.savefig(out_path, dpi=200)
    plt.close()


# ---------------------------
# Main analysis
# ---------------------------

def analyze(entry_id: int) -> None:
    print(f"[team_stats] Fetching entry {entry_id} ...")
    entry_info = api_entry(entry_id)
    history_json = api_history(entry_id)

    chips = extract_chips(history_json)

    df = pd.DataFrame(history_json["current"]).sort_values("event")

    df["overall_rank"] = df["overall_rank"]

    outdir = os.path.join("analysis_reports", str(entry_id))
    os.makedirs(outdir, exist_ok=True)

    conn = get_connection()
    conn.row_factory = conn.row_factory

    gw_data = []

    print("[team_stats] Collecting GW data from picks + SQLite ...")

    for _, row in df.iterrows():
        gw = int(row["event"])

        picks_json = api_picks(entry_id, gw)
        picks = picks_json.get("picks", [])

        captain_id = None
        vice_id = None

        starting_players = []
        bench_players = []

        starting_total = 0
        bench_total = 0

        for p in picks:
            player_id = p["element"]
            is_captain = p.get("is_captain", False)
            is_vice = p.get("is_vice_captain", False)
            position_slot = p["position"]  # 1–11 starter, 12–15 bench
            multiplier = p.get("multiplier", 1)

            if is_captain:
                captain_id = player_id
            if is_vice:
                vice_id = player_id

            meta = fetch_player_meta(conn, player_id)
            stats = fetch_player_gw_stats(conn, player_id, gw)

            total_points = stats["total_points"] * multiplier

            player_obj = {
                "id": meta["id"],
                "name": meta["name"],
                "team": meta["team"],
                "pos": meta["pos"],
                "total_points": total_points,
                "goals_scored": stats["goals_scored"],
                "assists": stats["assists"],
                "clean_sheets": stats["clean_sheets"],
                "bonus_points": stats["bonus_points"],
                "multiplier": multiplier,
                "is_captain": bool(is_captain),
                "is_vice": bool(is_vice),
                "slot": position_slot,
            }

            if position_slot <= 11:
                starting_players.append(player_obj)
                starting_total += total_points
            else:
                bench_players.append(player_obj)
                bench_total += total_points

        gw_obj = {
            "gw": gw,
            "points": row["points"],
            "overall_rank": row["overall_rank"],
            "gw_rank": row["rank_sort"],
            "transfers": row["event_transfers"],
            "transfer_cost": row["event_transfers_cost"],
            "value": row["value"] / 10,
            "bank": row["bank"] / 10,
            "chip": chips.get(gw),
            "team": {
                "starting": starting_players,
                "bench": bench_players,
                "captain_id": captain_id,
                "vice_id": vice_id,
                "starting_total": starting_total,
                "bench_total": bench_total,
            },
        }

        gw_data.append(gw_obj)

    # JSON output
    out_json = {
        "entry_id": entry_id,
        "team_name": entry_info.get("name"),
        "manager": f"{entry_info.get('player_first_name')} {entry_info.get('player_last_name')}",
        "total_points": entry_info.get("summary_overall_points"),
        "current_overall_rank": entry_info.get("summary_overall_rank"),
        "chips": chips,
        "gw_data": gw_data,
    }

    json_path = os.path.join(outdir, "team_stats.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(to_py(out_json), f, indent=2)

    print(f"[team_stats] Saved JSON: {json_path}")

    # rank PNG
    rank_plot(df, chips, outdir, entry_id)
    print(f"[team_stats] Saved rank graph: {os.path.join(outdir, 'rank_progression.png')}")

    conn.close()
    print("[team_stats] Done.")


def to_py(obj):
    """Recursively convert numpy/pandas types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: to_py(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_py(i) for i in obj]
    if isinstance(obj, (np.int64, np.int32, np.int16, int)):
        return int(obj)
    if isinstance(obj, (np.float64, np.float32, float)):
        return float(obj)
    if obj is None:
        return None
    return obj


# ---------------------------
# CLI
# ---------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", type=int, required=True, help="FPL entry ID")
    args = parser.parse_args()
    analyze(args.entry)
