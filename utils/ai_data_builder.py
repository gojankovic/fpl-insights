import os
import json
from typing import Dict, Any, List
from db.sqlite import get_connection
import requests


# -------------------------------------------------
# LOAD TEAM JSON FROM team_stats.py OUTPUT
# -------------------------------------------------

def load_team_json(entry_id: int) -> Dict[str, Any]:
    path = f"analysis_reports/{entry_id}/team_stats.json"
    if not os.path.exists(path):
        raise FileNotFoundError(f"team_stats.json not found for entry {entry_id}. Run team_stats.py first.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------------------------------
# PLAYER HISTORY & META FROM SQLITE
# -------------------------------------------------

def get_player_meta(player_id: int) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id,
               p.first_name,
               p.second_name,
               p.team_id,
               p.element_type,
               t.short_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.id = ?
    """, (player_id,))
    row = cur.fetchone()
    conn.close()

    if row is None:
        return {
            "id": player_id,
            "name": f"Unknown {player_id}",
            "team": None,
            "pos": None
        }

    pos_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

    return {
        "id": row["id"],
        "name": f"{row['first_name']} {row['second_name']}".strip(),
        "team": row["short_name"],
        "pos": pos_map.get(row["element_type"])
    }


def get_player_full_history(player_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM player_history
        WHERE player_id = ?
        ORDER BY gameweek ASC
    """, (player_id,))
    rows = cur.fetchall()
    conn.close()

    history = []
    for r in rows:
        history.append({
            "gw": r["gameweek"],
            "points": r["total_points"],
            "goals": r["goals_scored"],
            "assists": r["assists"],
            "cs": r["clean_sheets"],
            "bonus": r["bonus_points"],
            "minutes": r["minutes"]
        })
    return history

# -------------------------------------------------
# BUILD SQUAD FOR A GIVEN GW
# -------------------------------------------------

def build_squad_for_gw(entry_id: int, gw: int) -> List[Dict[str, Any]]:
    """
    Returns squad for analysis of target GW.
    Uses data from the latest COMPLETED gw strictly before the target GW.

    Example:
        predict GW15 -> use GW14 squad/state
        predict GW20 -> use GW19

    We never use information from the GW being predicted.
    """

    team_json = load_team_json(entry_id)

    # Which gameweeks exist?
    available_gws = sorted(g["gw"] for g in team_json["gw_data"])

    # GAMEWEEK MUST EXIST IN HISTORY (for predictions)
    past_gws = [g for g in available_gws if g < gw]

    if not past_gws:
        raise ValueError(
            f"Cannot analyze GW {gw}: no earlier GW exists for entry {entry_id}. "
            f"Available gameweeks: {available_gws}"
        )

    # We use the last completed GW before the target GW
    use_gw = past_gws[-1]

    gw_block = next(g for g in team_json["gw_data"] if g["gw"] == use_gw)

    squad = []

    # Combine starting + bench
    for section in ["starting", "bench"]:
        for p in gw_block["team"][section]:
            pid = p["id"]
            meta = get_player_meta(pid)
            history = get_player_full_history(pid)

            squad.append({
                "id": pid,
                "name": meta["name"],
                "team": meta["team"],
                "pos": meta["pos"],
                "gw_history": history[-6:],  # last 6 GWs for AI trend
                "is_captain": (pid == gw_block["team"]["captain_id"]),
                "is_vice": (pid == gw_block["team"]["vice_id"]),
                "multiplier": 2 if pid == gw_block["team"]["captain_id"] else 1,
                "last_gw_used": use_gw
            })

    return squad

# -------------------------------------------------
# FIXTURE DIFFICULTY (FDR) FOR NEXT N GAMEWEEKS
# -------------------------------------------------

def get_team_fdr(team_id: int, gw_start: int, next_n: int = 5):
    """
    Returns FDR info for the next N fixtures starting from gw_start.
    Pulls from SQLite fixtures table where we already have difficulty ratings.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT event, team_h, team_a, difficulty_home, difficulty_away
        FROM fixtures
        WHERE event >= ?
        ORDER BY event ASC
        LIMIT ?
    """, (gw_start, next_n))

    rows = cur.fetchall()
    conn.close()

    fdr_values = []
    opponents = []

    for r in rows:
        if r["team_h"] == team_id:
            fdr_values.append(r["difficulty_home"])
            opponents.append({
                "gw": r["event"],
                "opp": r["team_a"],
                "home": True
            })
        elif r["team_a"] == team_id:
            fdr_values.append(r["difficulty_away"])
            opponents.append({
                "gw": r["event"],
                "opp": r["team_h"],
                "home": False
            })
        else:
            # Not our team, skip
            continue

    avg_fdr = sum(fdr_values) / len(fdr_values) if fdr_values else None

    return {
        "avg_fdr": avg_fdr,
        "fixtures": opponents,
        "raw_values": fdr_values
    }

def build_fdr_map_for_all_teams(gw_start: int, next_n: int = 5):
    """
    Returns FDR map for ALL teams.

    Example:
    {
        "ARS": { avg_fdr: 2.2, fixtures: [...] },
        "MCI": { avg_fdr: 3.8, fixtures: [...] },
        ...
    }
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, short_name FROM teams")
    rows = cur.fetchall()
    conn.close()

    fdr_map = {}

    for r in rows:
        tid = r["id"]
        shortcode = r["short_name"]

        fdr_map[shortcode] = get_team_fdr(tid, gw_start, next_n)

    return fdr_map

# -------------------------------------------------
# HELPERS FOR PLAYER FORM AND MINUTES
# -------------------------------------------------

def average_last_n(history: List[Dict[str, Any]], n: int = 3) -> float:
    """
    Returns average total_points over last N matches.
    If fewer than N matches exist, use all available.
    """
    if not history:
        return 0.0
    last = history[-n:]
    pts = [h["points"] for h in last]
    return sum(pts) / len(pts)

def estimate_rotation_risk(history: List[Dict[str, Any]]) -> str:
    """
    Simple heuristic:
    - If last 3 GWs have 90,90,90 → 'low'
    - If any of last 3 < 45 minutes → 'medium'
    - If 2 of last 3 are 0 → 'high'
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

def detect_injury(player_id: int) -> bool:
    """
    Detects injury based ONLY on official FPL status flag.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM players WHERE id = ?", (player_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return False

    status = row["status"]

    # Injured or doubtful
    return status in ("i", "d")


def detect_suspension(player_id: int) -> bool:
    """
    Detects suspension based on FPL status flag.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM players WHERE id = ?", (player_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return False

    return row["status"] == "s"



# -------------------------------------------------
# BUILD TEAM JSON FOR AI
# -------------------------------------------------
def build_team_json(entry_id: int) -> Dict[str, Any]:
    """
    Reads team_stats.json and extracts only what exists.
    Uses fallbacks based on last completed GW.
    """
    raw = load_team_json(entry_id)

    # Find latest GW in data
    gw_blocks = raw["gw_data"]
    last_gw = max(gw_blocks, key=lambda g: g["gw"])

    # Determine current GW (fallback to last gw + 1)
    current_gw = raw.get("current_gw", last_gw["gw"] + 1)

    # Bank & team value live ONLY inside GW blocks → extract from last_gw
    bank = last_gw.get("bank", 0.0)
    team_value = last_gw.get("value", 0.0)

    return {
        "entry_id": entry_id,
        "current_gw": current_gw,
        "bank": bank,
        "team_value": team_value,
        "total_transfers": raw.get("total_transfers"),  # might not exist
        "chips_used": raw.get("chips_used", []),        # might not exist
        "next_fixtures_fdr": build_fdr_map_for_all_teams(current_gw, next_n=5)
    }


# -------------------------------------------------
# BUILD SQUAD STATE (THIS IS WHAT AI USES FOR TRANSFERS)
# -------------------------------------------------
def build_squad_state(entry_id: int, target_gw: int) -> Dict[str, Any]:
    """
    Squad state before a target GW.
    Uses last completed GW inside team_stats.json.
    """
    squad_list = build_squad_for_gw(entry_id, target_gw)
    team_json = load_team_json(entry_id)

    # GW data
    last_gw_block = max(team_json["gw_data"], key=lambda g: g["gw"])

    # Free transfers
    free_transfers = (
        last_gw_block.get("free_transfers") or
        last_gw_block.get("transfers") or
        1
    )

    # Bank
    bank = last_gw_block.get("bank", 0.0)

    # Build squad detail list
    squad = []
    club_counts = {}

    for p in squad_list:
        history = p["gw_history"]
        team = p["team"]

        squad.append({
            "id": p["id"],
            "name": p["name"],
            "team": team,
            "pos": p["pos"],
            "recent_form": average_last_n(history, 3),
            "expected_minutes": history[-1]["minutes"] if history else 0,
            "injury": detect_injury(p["id"]),
            "suspended": detect_suspension(p["id"]),
            "rotation_risk": estimate_rotation_risk(history),
        })

        club_counts[team] = club_counts.get(team, 0) + 1

    # Add prices
    conn = get_connection()
    cur = conn.cursor()

    for p in squad:
        cur.execute("SELECT now_cost FROM players WHERE id = ?", (p["id"],))
        row = cur.fetchone()
        p["price"] = row["now_cost"] if row else None

    conn.close()

    return {
        "free_transfers": free_transfers,
        "bank": bank,
        "squad": squad,
        "club_counts": club_counts
    }


# -------------------------------------------------
# BUILD ENHANCED CANDIDATE POOL
# -------------------------------------------------

def build_candidate_pool(limit: int = 120, gw: int = None) -> List[Dict[str, Any]]:
    """
    Build the global candidate pool for AI.
    Now includes:
    - form_last3
    - expected_minutes
    - injury flag
    - suspension flag
    - rotation risk
    - FDR for next GWs
    """

    conn = get_connection()
    cur = conn.cursor()

    # Pull best players by total points
    cur.execute("""
        SELECT id, first_name, second_name, team_id, element_type, now_cost, total_points
        FROM players
        ORDER BY total_points DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()

    # team short names
    cur.execute("SELECT id, short_name FROM teams")
    teams_map = {r["id"]: r["short_name"] for r in cur.fetchall()}

    conn.close()

    pos_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

    # Next-gw context needed for FDR
    if gw is None:
        # fallback: use biggest GW in database
        gw = 1

    pool = []

    for r in rows:
        pid = r["id"]
        name = f"{r['first_name']} {r['second_name']}".strip()
        team_short = teams_map.get(r["team_id"])
        pos = pos_map.get(r["element_type"])
        price = r["now_cost"]

        # full history
        history = get_player_full_history(pid)
        form_last3 = average_last_n(history, 3)
        expected_minutes = history[-1]["minutes"] if history else 0

        inj = detect_injury(pid),
        susp = detect_suspension(pid)
        rotation = estimate_rotation_risk(history)

        # FDR
        fdr_info = get_team_fdr(r["team_id"], gw_start=gw, next_n=5)

        pool.append({
            "id": pid,
            "name": name,
            "team": team_short,
            "pos": pos,
            "price": price,
            "total_points": r["total_points"],
            "form_last3": form_last3,
            "expected_minutes": expected_minutes,
            "injury": inj,
            "suspended": susp,
            "rotation_risk": rotation,
            "fdr_next5": fdr_info,
            "recent_history": history[-6:]
        })

    return pool

from typing import Dict, Any, List


def reduce_candidate_pool_for_transfers(
    squad_state: Dict[str, Any],
    candidate_pool: List[Dict[str, Any]],
    max_per_position: int = 25,
) -> List[Dict[str, Any]]:
    """
    Reduce the global candidate pool to a smaller, high-quality subset.

    Heuristics:
    - keep only players that are not injured or suspended
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

    # helper: map rotation_risk to numeric priority
    rotation_priority = {"low": 0, "medium": 1, "high": 2, "unknown": 1}

    by_pos = {"GK": [], "DEF": [], "MID": [], "FWD": []}

    for p in candidate_pool:
        pid = p["id"]
        pos = p.get("pos")
        team = p.get("team")

        # Skip players already owned
        if pid in owned_ids:
            continue

        # Skip clubs that already have 3 players
        if team is not None and club_counts.get(team, 0) >= 3:
            continue

        # Skip clear injury / suspension
        if p.get("injury"):
            continue
        if p.get("suspended"):
            continue

        # Basic sanity: must have position and team
        if pos not in by_pos:
            continue

        by_pos[pos].append(p)

    reduced: List[Dict[str, Any]] = []

    for pos, players in by_pos.items():
        # Sort by our priority
        # lower rotation_priority is better, others descending
        players_sorted = sorted(
            players,
            key=lambda x: (
                rotation_priority.get(x.get("rotation_risk", "unknown"), 1),
                -(x.get("expected_minutes") or 0),
                -(x.get("form_last3") or 0.0),
                -(x.get("total_points") or 0),
            ),
        )

        # Take top N for this position
        reduced.extend(players_sorted[:max_per_position])

    return reduced


