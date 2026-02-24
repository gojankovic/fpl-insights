from typing import Iterable, Tuple

from db.sqlite import get_connection


def replace_teams(rows: Iterable[Tuple], conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM teams;")
    cur.executemany("""
        INSERT INTO teams (
            id, code, name, short_name, strength,
            strength_overall_home, strength_overall_away,
            strength_attack_home, strength_attack_away,
            strength_defence_home, strength_defence_away,
            form, draw, win, loss, points, position, played
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    if own_conn:
        conn.commit()
        conn.close()


def replace_players(rows: Iterable[Tuple], conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM players;")
    cur.executemany("""
        INSERT INTO players (
            id, first_name, second_name, team_id, element_type, now_cost,
            total_points, goals_scored, assists, clean_sheets, selected_by_percent,
            minutes, form, points_per_game, status, chance_of_playing_next_round,
            transfers_in_event, transfers_out_event, in_dreamteam, saves,
            yellow_cards, red_cards, bonus, bps, influence, creativity, threat,
            ict_index, expected_goals, expected_assists, expected_goal_involvements,
            expected_goals_conceded, expected_goals_per_90, saves_per_90,
            expected_assists_per_90, expected_goal_involvements_per_90,
            expected_goals_conceded_per_90, goals_conceded_per_90, starts,
            starts_per_90, clean_sheets_per_90, chance_of_playing_this_round,
            news, news_added, ep_next, ep_this
        )  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    if own_conn:
        conn.commit()
        conn.close()


def replace_events(rows: Iterable[Tuple], conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM events;")
    cur.executemany("""
        INSERT INTO events (
            id, name, deadline_time, average_entry_score,
            finished, is_current, is_next, most_captained, most_transferred_in
        ) VALUES (?,?,?,?,?,?,?,?,?)
    """, rows)
    if own_conn:
        conn.commit()
        conn.close()


def replace_fixtures(rows: Iterable[Tuple], conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM fixtures;")
    cur.executemany("""
        INSERT INTO fixtures (
            id, event, team_h, team_a, team_h_score, team_a_score,
            difficulty_home, difficulty_away, finished, kickoff_time,
            started, provisional_start_time, pulse_id
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    if own_conn:
        conn.commit()
        conn.close()


def replace_player_history(rows: Iterable[Tuple], conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM player_history;")
    cur.executemany("""
        INSERT INTO player_history (
            player_id, gameweek, minutes, total_points, goals_scored, assists, clean_sheets,
            starts, bps, ict_index, influence, creativity, threat,
            expected_goal_involvements, expected_goals_conceded,
            defensive_contribution, recoveries, tackles, clearances_blocks_interceptions,
            penalties_missed, penalties_saved, yellow_cards, red_cards,
            selected, transfers_balance, value, fixture,
            opponent_team, home_score, away_score, home, bonus_points,
            expected_goals, expected_assists, transfers_in, transfers_out, modified, kickoff_time
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    if own_conn:
        conn.commit()
        conn.close()


def replace_player_fixtures(rows: Iterable[Tuple], conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM player_fixtures;")
    cur.executemany("""
        INSERT OR REPLACE INTO player_fixtures (
            player_id, fixture_id, event, event_name, difficulty, is_home,
            team_h, team_a, team_h_score, team_a_score, finished, started,
            minutes, provisional_start_time, kickoff_time, code
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    if own_conn:
        conn.commit()
        conn.close()


def replace_player_history_past(rows: Iterable[Tuple], conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM player_history_past;")
    cur.executemany("""
        INSERT OR REPLACE INTO player_history_past (
            player_id, season_name, total_points, starts, minutes, starts_per_90,
            clean_sheets, clean_sheets_per_90, goals_scored, assists,
            expected_goals, expected_assists, expected_goal_involvements, expected_goals_conceded,
            expected_goals_per_90, expected_assists_per_90, expected_goal_involvements_per_90,
            expected_goals_conceded_per_90, influence, creativity, threat, ict_index,
            bps, bonus, yellow_cards, red_cards, saves, penalties_saved, penalties_missed,
            recoveries, tackles, defensive_contribution, clearances_blocks_interceptions,
            start_cost, end_cost, element_code
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    if own_conn:
        conn.commit()
        conn.close()


def append_player_gw_snapshot(rows: Iterable[Tuple], conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.executemany("""
        INSERT OR REPLACE INTO player_gw_snapshot (
            snapshot_time, season, current_event, next_event, player_id, status,
            chance_of_playing_next_round, chance_of_playing_this_round,
            now_cost, selected_by_percent, transfers_in_event, transfers_out_event,
            form, points_per_game, ep_next, ep_this, minutes, starts, news, news_added
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    if own_conn:
        conn.commit()
        conn.close()
