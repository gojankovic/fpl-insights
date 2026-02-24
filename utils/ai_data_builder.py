import os
import json
from typing import Dict, Any, List, Optional

from db.sqlite import get_connection


# -------------------------------------------------
# LOAD TEAM JSON FROM team_stats.py OUTPUT
# -------------------------------------------------


def load_team_json(entry_id: int) -> Dict[str, Any]:
    """
    Load team_stats.json created by utils/team_stats.py.

    Expected basic structure (example):

    {
      "entry_id": 2709841,
      "team_name": "...",
      "manager": "...",
      "total_points": 900,
      "current_overall_rank": 123456,
      "chips": [...],
      "gw_data": [
        {
          "gw": 1,
          "points": 75,
          "overall_rank": 1200000,
          "gw_rank": 500000,
          "transfers": 0,
          "transfer_cost": 0,
          "value": 100.0,
          "bank": 0.5,
          "chip": null,
          "team": {
            "starting": [...],
            "bench": [...],
            "captain_id": ...,
            "vice_id": ...
          }
        },
        ...
      ]
    }
    """
    path = os.path.join("analysis_reports", str(entry_id), "team_stats.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"team_stats.json not found for entry {entry_id}. "
            f"Expected at: {path}. Run utils/team_stats.py first."
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------------------------------
# PLAYER META & HISTORY FROM SQLITE
# -------------------------------------------------


def get_player_meta(player_id: int) -> Dict[str, Any]:
    """
    Return basic player info from SQLite:
    - name
    - FPL team short code
    - position (GK/DEF/MID/FWD)
    """
    conn = get_connection()
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
    conn.close()

    if row is None:
        return {
            "id": player_id,
            "name": f"Unknown {player_id}",
            "team": None,
            "pos": None,
        }

    pos_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

    return {
        "id": row["id"],
        "name": f"{row['first_name']} {row['second_name']}".strip(),
        "team": row["short_name"],
        "pos": pos_map.get(row["element_type"]),
    }


def get_player_full_history(player_id: int) -> List[Dict[str, Any]]:
    """
    Return complete per-GW history from player_history.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM player_history
        WHERE player_id = ?
        ORDER BY gameweek ASC
        """,
        (player_id,),
    )
    rows = cur.fetchall()
    conn.close()

    history: List[Dict[str, Any]] = []
    for r in rows:
        history.append(
            {
                "gw": r["gameweek"],
                "points": r["total_points"],
                "goals": r["goals_scored"],
                "assists": r["assists"],
                "cs": r["clean_sheets"],
                "bonus": r["bonus_points"],
                "minutes": r["minutes"],
            }
        )
    return history


# -------------------------------------------------
# BUILD SQUAD FOR A GIVEN GW (ALWAYS USING GW-1)
# -------------------------------------------------


def build_squad_for_gw(entry_id: int, gw: int) -> List[Dict[str, Any]]:
    """
    Return squad used for analysis of target GW.

    IMPORTANT:
    - We NEVER use data from the GW we are predicting.
    - For GW X we always use the last completed GW < X.

    Example:
      predict GW15 -> use GW14 squad/state
      predict GW20 -> use GW19
    """
    team_json = load_team_json(entry_id)

    available_gws = sorted(g["gw"] for g in team_json["gw_data"])
    past_gws = [g for g in available_gws if g < gw]

    if not past_gws:
        raise ValueError(
            f"Cannot analyze GW {gw}: no earlier GW exists for entry {entry_id}. "
            f"Available GWs in team_stats.json: {available_gws}"
        )

    use_gw = past_gws[-1]
    gw_block = next(g for g in team_json["gw_data"] if g["gw"] == use_gw)

    squad: List[Dict[str, Any]] = []

    for section in ["starting", "bench"]:
        for p in gw_block["team"][section]:
            pid = p["id"]
            meta = get_player_meta(pid)
            history = get_player_full_history(pid)

            squad.append(
                {
                    "id": pid,
                    "name": meta["name"],
                    "team": meta["team"],
                    "pos": meta["pos"],
                    "gw_history": history[-6:],  # last 6 GWs for trend
                    "is_captain": pid == gw_block["team"]["captain_id"],
                    "is_vice": pid == gw_block["team"]["vice_id"],
                    "multiplier": 2 if pid == gw_block["team"]["captain_id"] else 1,
                    "last_gw_used": use_gw,
                    "is_starting": section == "starting",
                }
            )

    return squad


# -------------------------------------------------
# FIXTURE DIFFICULTY (FDR) FOR NEXT N GAMEWEEKS
# -------------------------------------------------


def get_team_fdr(team_id: int, gw_start: int, next_n: int = 5) -> Dict[str, Any]:
    """
    Returns FDR info for the next N fixtures starting from gw_start.

    Assumes fixtures table has columns:
    - event (GW)
    - team_h, team_a
    - difficulty_home, difficulty_away
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT event, team_h, team_a, difficulty_home, difficulty_away
        FROM fixtures
        WHERE event >= ? AND (team_h = ? OR team_a = ?)
        ORDER BY event ASC
        LIMIT ?
        """,
        (gw_start, team_id, team_id, next_n),
    )

    rows = cur.fetchall()
    conn.close()

    fdr_values: List[float] = []
    opponents: List[Dict[str, Any]] = []

    for r in rows:
        if r["team_h"] == team_id:
            fdr_values.append(r["difficulty_home"])
            opponents.append(
                {
                    "gw": r["event"],
                    "opp": r["team_a"],
                    "home": True,
                }
            )
        elif r["team_a"] == team_id:
            fdr_values.append(r["difficulty_away"])
            opponents.append(
                {
                    "gw": r["event"],
                    "opp": r["team_h"],
                    "home": False,
                }
            )

    avg_fdr = sum(fdr_values) / len(fdr_values) if fdr_values else None

    return {
        "avg_fdr": avg_fdr,
        "fixtures": opponents,
        "raw_values": fdr_values,
    }


def build_fdr_map_for_all_teams(gw_start: int, next_n: int = 5) -> Dict[str, Any]:
    """
    Returns FDR map for ALL teams:

    {
      "ARS": { "avg_fdr": 2.2, "fixtures": [...] },
      "MCI": { "avg_fdr": 3.8, "fixtures": [...] },
      ...
    }
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, short_name FROM teams")
    rows = cur.fetchall()
    conn.close()

    fdr_map: Dict[str, Any] = {}

    for r in rows:
        tid = r["id"]
        shortcode = r["short_name"]
        fdr_map[shortcode] = get_team_fdr(tid, gw_start, next_n)

    return fdr_map


# -------------------------------------------------
# HELPERS FOR FORM / ROTATION
# -------------------------------------------------


def average_last_n(history: List[Dict[str, Any]], n: int = 3) -> float:
    """
    Average total_points over last N matches.
    If fewer than N matches exist, use all available.
    """
    if not history:
        return 0.0
    last = history[-n:]
    pts = [h["points"] for h in last]
    return float(sum(pts)) / len(pts)


def estimate_rotation_risk(history: List[Dict[str, Any]]) -> str:
    """
    Very simple rotation heuristic based on minutes in last 3 GWs:

    - last 3 all ≥ 85 minutes -> "low"
    - 2 or more zero-minute games -> "high"
    - any < 45 minutes           -> "medium"
    - otherwise                   -> "medium"
    """
    if not history or len(history) < 3:
        return "unknown"

    last3 = history[-3:]
    mins = [h["minutes"] for h in last3]

    if all(m >= 85 for m in mins):
        return "low"

    if mins.count(0) >= 2:
        return "high"

    if any(m < 45 for m in mins):
        return "medium"

    return "medium"


# -------------------------------------------------
# TEAM CONTEXT FOR AI (NO RAW gw_data DUMP)
# -------------------------------------------------


def build_team_json(entry_id: int, target_gw: Optional[int] = None) -> Dict[str, Any]:
    """
    Build a compact team context for AI prompts.

    We do NOT dump full gw_data here, to keep token usage reasonable.
    """
    raw = load_team_json(entry_id)

    gw_data = raw.get("gw_data", [])
    if not gw_data:
        raise ValueError("team_stats.json has empty gw_data.")

    if target_gw is None:
        last_gw_block = max(gw_data, key=lambda g: g["gw"])
    else:
        past_gws = [g for g in gw_data if g.get("gw") is not None and g["gw"] < target_gw]
        last_gw_block = max(past_gws, key=lambda g: g["gw"]) if past_gws else max(
            gw_data, key=lambda g: g["gw"]
        )

    return {
        "entry_id": raw.get("entry_id", entry_id),
        "team_name": raw.get("team_name"),
        "manager": raw.get("manager"),
        "total_points": raw.get("total_points"),
        "current_overall_rank": raw.get("current_overall_rank"),
        "chips": raw.get("chips", []),
        "last_gw": {
            "gw": last_gw_block.get("gw"),
            "points": last_gw_block.get("points"),
            "overall_rank": last_gw_block.get("overall_rank"),
            "gw_rank": last_gw_block.get("gw_rank"),
            "value": last_gw_block.get("value"),
            "bank": last_gw_block.get("bank"),
            "transfers": last_gw_block.get("transfers"),
            "transfer_cost": last_gw_block.get("transfer_cost"),
            "chip": last_gw_block.get("chip"),
        },
    }


# -------------------------------------------------
# BUILD SQUAD STATE FOR TRANSFER AI
# -------------------------------------------------


def build_squad_state(entry_id: int, target_gw: int, free_transfers: int, allowed_extra: int) -> Dict[str, Any]:
    """
    Build the squad state prior to a target GW.

    For GW X we use the squad from GW X-1.
    Bank + free transfers are taken from the last GW block
    in team_stats.json (same as used by team_stats logic).
    """
    squad_list = build_squad_for_gw(entry_id, target_gw)

    # Count clubs and enrich each player with status / price.
    squad: List[Dict[str, Any]] = []
    club_counts: Dict[Optional[str], int] = {}

    conn = get_connection()
    cur = conn.cursor()

    for p in squad_list:
        pid = p["id"]
        history = p["gw_history"]
        team = p["team"]

        cur.execute(
            """
            SELECT now_cost, status, chance_of_playing_next_round
            FROM players
            WHERE id = ?
            """,
            (pid,),
        )
        row = cur.fetchone()

        price = row["now_cost"] if row else None
        status = row["status"] if row else "a"
        chance = row["chance_of_playing_next_round"] if row else None

        injured = status == "i"
        suspended = status == "s"

        squad.append(
            {
                "id": pid,
                "name": p["name"],
                "team": team,
                "pos": p["pos"],
                "is_starting": p.get("is_starting", False),
                "recent_form": average_last_n(history, 3),
                "expected_minutes": history[-1]["minutes"] if history else 0,
                "rotation_risk": estimate_rotation_risk(history),
                "price": price,
                "status": status,
                "chance_of_playing_next_round": chance,
                "injury": injured,
                "suspended": suspended,
            }
        )

        club_counts[team] = club_counts.get(team, 0) + 1

    conn.close()

    # Bank + free transfers from team_stats.json
    team_json_raw = load_team_json(entry_id)
    gw_data = team_json_raw.get("gw_data", [])
    if not gw_data:
        raise ValueError("team_stats.json gw_data is empty when building squad_state.")

    last_gw_block = max(gw_data, key=lambda g: g["gw"])
    bank = last_gw_block.get("bank", 0.0)

    return {
        "allowed_extra": allowed_extra,
        "allowed_extra_transfers": allowed_extra,
        "free_transfers": free_transfers,
        "bank": bank,
        "squad": squad,
        "club_counts": club_counts,
    }


# -------------------------------------------------
# BUILD ENHANCED GLOBAL CANDIDATE POOL
# -------------------------------------------------


def build_candidate_pool(limit: int = 120, gw: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Build the global candidate pool for AI.

    Includes:
    - status / chance_of_playing_next_round
    - form_last3
    - expected_minutes
    - injury / suspension flags based on status
    - rotation risk
    - FDR for next GWs
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id,
               first_name,
               second_name,
               team_id,
               element_type,
               now_cost,
               total_points,
               status,
               chance_of_playing_next_round
        FROM players
        ORDER BY total_points DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()

    cur.execute("SELECT id, short_name FROM teams")
    teams_map = {r["id"]: r["short_name"] for r in cur.fetchall()}
    conn.close()

    pos_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

    if gw is None:
        # Fallback: just assume from GW1
        gw = 1

    pool: List[Dict[str, Any]] = []

    for r in rows:
        pid = r["id"]
        name = f"{r['first_name']} {r['second_name']}".strip()
        team_short = teams_map.get(r["team_id"])
        pos = pos_map.get(r["element_type"])
        price = r["now_cost"]
        status = r["status"]
        chance = r["chance_of_playing_next_round"]

        history = get_player_full_history(pid)
        form_last3 = average_last_n(history, 3)
        expected_minutes = history[-1]["minutes"] if history else 0

        rotation = estimate_rotation_risk(history)

        injured = status == "i"
        suspended = status == "s"

        fdr_info = get_team_fdr(r["team_id"], gw_start=gw, next_n=5)

        pool.append(
            {
                "id": pid,
                "name": name,
                "team": team_short,
                "pos": pos,
                "price": price,
                "total_points": r["total_points"],
                "status": status,
                "chance_of_playing_next_round": chance,
                "form_last3": form_last3,
                "expected_minutes": expected_minutes,
                "injury": injured,
                "suspended": suspended,
                "rotation_risk": rotation,
                "fdr_next5": fdr_info,
                "recent_history": history[-6:],
            }
        )

    return pool


# -------------------------------------------------
# CANDIDATE POOL REDUCTION FOR TRANSFERS
# -------------------------------------------------


def reduce_candidate_pool_for_transfers(
    squad_state: Dict[str, Any],
    candidate_pool: List[Dict[str, Any]],
    max_per_position: int = 25,
) -> List[Dict[str, Any]]:
    """
    Reduce the global candidate pool to a smaller, high-quality subset.

    Heuristics:
    - keep only players that are not injured or suspended (by status)
    - avoid obvious high rotation risk where possible
    - remove players already owned
    - avoid clubs where the team already has 3 players
    - within each position, sort by:
        1) rotation_risk (low > medium > high)
        2) expected_minutes (desc)
        3) form_last3 (desc)
        4) total_points (desc)
    - keep top N per position (GK/DEF/MID/FWD)
    """
    owned_ids = {p["id"] for p in squad_state["squad"]}
    club_counts = dict(squad_state.get("club_counts", {}))

    rotation_priority = {"low": 0, "medium": 1, "unknown": 1, "high": 2}
    by_pos: Dict[str, List[Dict[str, Any]]] = {"GK": [], "DEF": [], "MID": [], "FWD": []}

    for p in candidate_pool:
        pid = p["id"]
        pos = p.get("pos")
        team = p.get("team")

        if pos not in by_pos:
            continue

        # Skip already owned players
        if pid in owned_ids:
            continue

        # Respect 3-per-club rule
        if team is not None and club_counts.get(team, 0) >= 3:
            continue

        # Skip clear injured / suspended by status
        if p.get("status") in ("i", "s", "u"):
            continue

        by_pos[pos].append(p)

    reduced: List[Dict[str, Any]] = []

    for pos, players in by_pos.items():
        players_sorted = sorted(
            players,
            key=lambda x: (
                rotation_priority.get(x.get("rotation_risk", "unknown"), 1),
                -(x.get("expected_minutes") or 0),
                -(x.get("form_last3") or 0.0),
                -(x.get("total_points") or 0),
            ),
        )
        reduced.extend(players_sorted[:max_per_position])

    return reduced
