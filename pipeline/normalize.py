from typing import Any, Dict, Iterable, List, Tuple


def _parse_float(value):
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int_flag(value) -> int:
    return 1 if value else 0


def normalize_teams(bootstrap: Dict[str, Any]) -> List[Tuple]:
    teams = []
    for t in bootstrap["teams"]:
        teams.append((
            t["id"],
            t["code"],
            t["name"],
            t["short_name"],
            t["strength"],
            t["strength_overall_home"],
            t["strength_overall_away"],
            t["strength_attack_home"],
            t["strength_attack_away"],
            t["strength_defence_home"],
            t["strength_defence_away"],
            _parse_float(t.get("form")),
            t.get("draw"),
            t.get("win"),
            t.get("loss"),
            t.get("points"),
            t.get("position"),
            t.get("played"),
        ))
    return teams

def normalize_players(bootstrap: Dict[str, Any]) -> List[Tuple]:
    rows = []
    for p in bootstrap["elements"]:
        rows.append((
            p["id"],
            p["first_name"],
            p["second_name"],
            p["team"],
            p["element_type"],
            float(p["now_cost"]) / 10.0,
            p["total_points"],
            p["goals_scored"],
            p["assists"],
            p["clean_sheets"],
            _parse_float(p["selected_by_percent"]),
            p["minutes"],
            _parse_float(p["form"]),
            _parse_float(p["points_per_game"]),
            p["status"],
            p.get("chance_of_playing_next_round"),
            p["transfers_in_event"],
            p["transfers_out_event"],
            bool(p["in_dreamteam"]),
            p["saves"],
            p["yellow_cards"],
            p["red_cards"],
            p["bonus"],
            p["bps"],
            _parse_float(p["influence"]),
            _parse_float(p["creativity"]),
            _parse_float(p["threat"]),
            _parse_float(p["ict_index"]),
            _parse_float(p.get("expected_goals")),
            _parse_float(p.get("expected_assists")),
            _parse_float(p.get("expected_goal_involvements")),
            _parse_float(p.get("expected_goals_conceded")),
            _parse_float(p.get("expected_goals_per_90")),
            _parse_float(p.get("saves_per_90")),
            _parse_float(p.get("expected_assists_per_90")),
            _parse_float(p.get("expected_goal_involvements_per_90")),
            _parse_float(p.get("expected_goals_conceded_per_90")),
            _parse_float(p.get("goals_conceded_per_90")),
            p.get("starts"),
            _parse_float(p.get("starts_per_90")),
            _parse_float(p.get("clean_sheets_per_90")),
            p.get("chance_of_playing_this_round"),
            p.get("news"),
            p.get("news_added"),
            _parse_float(p.get("ep_next")),
            _parse_float(p.get("ep_this")),
        ))
    return rows


# --- gameweeks --- #
def normalize_events(bootstrap: Dict[str, Any]) -> List[Tuple]:
    rows = []
    for e in bootstrap["events"]:
        rows.append((
            e["id"],
            e["name"],
            e["deadline_time"],
            e.get("average_entry_score"),
            int(e.get("finished", False)),
            int(e.get("is_current", False)),
            int(e.get("is_next", False)),
            e.get("most_captained"),
            e.get("most_transferred_in"),
        ))
    return rows


def normalize_fixtures(fixtures: Iterable[Dict[str, Any]]) -> List[Tuple]:
    rows = []
    for f in fixtures:
        rows.append((
            f["id"],
            f.get("event"),
            f["team_h"],
            f["team_a"],
            f.get("team_h_score"),
            f.get("team_a_score"),
            f.get("team_h_difficulty"),
            f.get("team_a_difficulty"),
            _to_int_flag(f.get("finished", False)),
            f.get("kickoff_time"),
            _to_int_flag(f.get("started", False)),
            _to_int_flag(f.get("provisional_start_time", False)),
            f.get("pulse_id"),
        ))
    return rows


def normalize_player_history(player_id: int, player_summary: Dict[str, Any]) -> List[Tuple]:
    rows = []
    for gw in player_summary.get("history", []):
        rows.append((
            player_id,
            gw["round"],
            gw.get("minutes", 0),
            gw["total_points"],
            gw["goals_scored"],
            gw["assists"],
            gw["clean_sheets"],
            gw.get("starts", 0),
            gw.get("bps", 0),
            _parse_float(gw.get("ict_index")),
            _parse_float(gw.get("influence")),
            _parse_float(gw.get("creativity")),
            _parse_float(gw.get("threat")),
            _parse_float(gw.get("expected_goal_involvements")),
            _parse_float(gw.get("expected_goals_conceded")),
            gw.get("defensive_contribution", 0),
            gw.get("recoveries", 0),
            gw.get("tackles", 0),
            gw.get("clearances_blocks_interceptions", 0),
            gw.get("penalties_missed", 0),
            gw.get("penalties_saved", 0),
            gw.get("yellow_cards", 0),
            gw.get("red_cards", 0),
            gw.get("selected"),
            gw.get("transfers_balance"),
            gw.get("value"),
            gw.get("fixture"),
            gw.get("opponent_team"),
            gw.get("team_h_score"),
            gw.get("team_a_score"),
            gw.get("was_home", True),
            gw.get("bonus", 0),
            _parse_float(gw.get("expected_goals")),
            _parse_float(gw.get("expected_assists")),
            gw.get("transfers_in", 0),
            gw.get("transfers_out", 0),
            gw.get("modified"),
            gw.get("kickoff_time"),
        ))
    return rows


def normalize_player_fixtures(player_id: int, player_summary: Dict[str, Any]) -> List[Tuple]:
    rows = []
    for f in player_summary.get("fixtures", []):
        rows.append((
            player_id,
            f.get("id"),
            f.get("event"),
            f.get("event_name"),
            f.get("difficulty"),
            int(f.get("is_home", False)),
            f.get("team_h"),
            f.get("team_a"),
            f.get("team_h_score"),
            f.get("team_a_score"),
            _to_int_flag(f.get("finished", False)),
            _to_int_flag(f.get("started", False)),
            f.get("minutes"),
            _to_int_flag(f.get("provisional_start_time", False)),
            f.get("kickoff_time"),
            f.get("code"),
        ))
    return rows


def normalize_player_history_past(player_id: int, player_summary: Dict[str, Any]) -> List[Tuple]:
    rows = []
    for s in player_summary.get("history_past", []):
        rows.append((
            player_id,
            s.get("season_name"),
            s.get("total_points"),
            s.get("starts"),
            s.get("minutes"),
            _parse_float(s.get("starts_per_90")),
            s.get("clean_sheets"),
            _parse_float(s.get("clean_sheets_per_90")),
            s.get("goals_scored"),
            s.get("assists"),
            _parse_float(s.get("expected_goals")),
            _parse_float(s.get("expected_assists")),
            _parse_float(s.get("expected_goal_involvements")),
            _parse_float(s.get("expected_goals_conceded")),
            _parse_float(s.get("expected_goals_per_90")),
            _parse_float(s.get("expected_assists_per_90")),
            _parse_float(s.get("expected_goal_involvements_per_90")),
            _parse_float(s.get("expected_goals_conceded_per_90")),
            _parse_float(s.get("influence")),
            _parse_float(s.get("creativity")),
            _parse_float(s.get("threat")),
            _parse_float(s.get("ict_index")),
            s.get("bps"),
            s.get("bonus"),
            s.get("yellow_cards"),
            s.get("red_cards"),
            s.get("saves"),
            s.get("penalties_saved"),
            s.get("penalties_missed"),
            s.get("recoveries"),
            s.get("tackles"),
            s.get("defensive_contribution"),
            s.get("clearances_blocks_interceptions"),
            s.get("start_cost"),
            s.get("end_cost"),
            s.get("element_code"),
        ))
    return rows


def normalize_player_gw_snapshot(bootstrap: Dict[str, Any], snapshot_time: str) -> List[Tuple]:
    events = bootstrap.get("events", [])
    season = None
    current_event = None
    next_event = None

    for e in events:
        if season is None:
            deadline = e.get("deadline_time")
            if isinstance(deadline, str) and len(deadline) >= 4:
                try:
                    season = int(deadline[:4])
                except ValueError:
                    season = None
        if e.get("is_current"):
            current_event = e.get("id")
        if e.get("is_next"):
            next_event = e.get("id")

    rows = []
    for p in bootstrap.get("elements", []):
        rows.append((
            snapshot_time,
            season,
            current_event,
            next_event,
            p["id"],
            p.get("status"),
            p.get("chance_of_playing_next_round"),
            p.get("chance_of_playing_this_round"),
            float(p["now_cost"]) / 10.0,
            _parse_float(p.get("selected_by_percent")),
            p.get("transfers_in_event"),
            p.get("transfers_out_event"),
            _parse_float(p.get("form")),
            _parse_float(p.get("points_per_game")),
            _parse_float(p.get("ep_next")),
            _parse_float(p.get("ep_this")),
            p.get("minutes"),
            p.get("starts"),
            p.get("news"),
            p.get("news_added"),
        ))
    return rows
