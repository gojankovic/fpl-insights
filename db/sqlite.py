import sqlite3
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id                    INTEGER PRIMARY KEY,
        code                  INTEGER,
        name                  TEXT,
        short_name            TEXT,
        strength              INTEGER,
        strength_overall_home INTEGER,
        strength_overall_away INTEGER,
        strength_attack_home  INTEGER,
        strength_attack_away  INTEGER,
        strength_defence_home INTEGER,
        strength_defence_away INTEGER,
        form                  REAL,
        draw                  INTEGER,
        win                   INTEGER,
        loss                  INTEGER,
        points                INTEGER,
        position              INTEGER,
        played                INTEGER
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY,
        first_name TEXT,
        second_name TEXT,
        team_id INTEGER,
        element_type INTEGER,
        now_cost REAL,
        total_points INTEGER,
        goals_scored INTEGER,
        assists INTEGER,
        clean_sheets INTEGER,
        selected_by_percent REAL,
        minutes INTEGER,
        form REAL,
        points_per_game REAL,
        status TEXT,
        chance_of_playing_next_round INTEGER,
        transfers_in_event INTEGER,
        transfers_out_event INTEGER,
        in_dreamteam BOOLEAN,
        saves INTEGER,
        yellow_cards INTEGER,
        red_cards INTEGER,
        bonus INTEGER,
        bps INTEGER,
        influence REAL,
        creativity REAL,
        threat REAL,
        ict_index REAL,
        expected_goals REAL,
        expected_assists REAL,
        expected_goal_involvements REAL,
        expected_goals_conceded REAL,
        expected_goals_per_90 REAL,
        saves_per_90 REAL,
        expected_assists_per_90 REAL,
        expected_goal_involvements_per_90 REAL,
        expected_goals_conceded_per_90 REAL,
        goals_conceded_per_90 REAL,
        starts INTEGER,
        starts_per_90 REAL,
        clean_sheets_per_90 REAL,
        FOREIGN KEY (team_id) REFERENCES teams(id)
    );
    """)

    # EVENTS (GW)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        name TEXT,
        deadline_time TEXT,
        average_entry_score INTEGER,
        finished INTEGER,
        most_captained INTEGER,
        most_transferred_in INTEGER
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS fixtures (
        id INTEGER PRIMARY KEY,
        event INTEGER,
        team_h INTEGER,
        team_a INTEGER,
        team_h_score INTEGER,
        team_a_score INTEGER,
        difficulty_home INTEGER,
        difficulty_away INTEGER,
        finished INTEGER,
        kickoff_time TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS player_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        gameweek INTEGER,
        minutes INTEGER,
        total_points INTEGER,
        goals_scored INTEGER,
        assists INTEGER,
        clean_sheets INTEGER,
        opponent_team INTEGER,
        home_score INTEGER,
        away_score INTEGER,
        home BOOLEAN,
        bonus_points INTEGER,
        expected_goals REAL,
        expected_assists REAL,
        transfers_in INTEGER,
        transfers_out INTEGER,
        kickoff_time TEXT,
        FOREIGN KEY (player_id) REFERENCES players(id)
    );
    """)

    # Lightweight migration: add missing columns if schema is older.
    cur.execute("PRAGMA table_info(player_history)")
    existing_cols = {row[1] for row in cur.fetchall()}
    if "minutes" not in existing_cols:
        cur.execute("ALTER TABLE player_history ADD COLUMN minutes INTEGER")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    conn.commit()
    conn.close()
