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
            starts_per_90, clean_sheets_per_90
        )  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
            finished, most_captained, most_transferred_in
        ) VALUES (?,?,?,?,?,?,?)
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
            difficulty_home, difficulty_away, finished, kickoff_time
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
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
            player_id, gameweek, minutes, total_points, goals_scored, assists,
            clean_sheets, opponent_team, home_score, away_score, home,
            bonus_points, expected_goals, expected_assists,
            transfers_in, transfers_out, kickoff_time
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    if own_conn:
        conn.commit()
        conn.close()
