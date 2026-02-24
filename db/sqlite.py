import sqlite3
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_columns(cur, table_name, columns):
    cur.execute(f"PRAGMA table_info({table_name})")
    existing_cols = {row[1] for row in cur.fetchall()}
    for col, ddl in columns.items():
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


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
        chance_of_playing_this_round INTEGER,
        news TEXT,
        news_added TEXT,
        ep_next REAL,
        ep_this REAL,
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
        is_current INTEGER,
        is_next INTEGER,
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
        kickoff_time TEXT,
        started INTEGER,
        provisional_start_time INTEGER,
        pulse_id INTEGER
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
        starts INTEGER,
        bps INTEGER,
        ict_index REAL,
        influence REAL,
        creativity REAL,
        threat REAL,
        expected_goal_involvements REAL,
        expected_goals_conceded REAL,
        defensive_contribution INTEGER,
        recoveries INTEGER,
        tackles INTEGER,
        clearances_blocks_interceptions INTEGER,
        penalties_missed INTEGER,
        penalties_saved INTEGER,
        yellow_cards INTEGER,
        red_cards INTEGER,
        selected INTEGER,
        transfers_balance INTEGER,
        value INTEGER,
        fixture INTEGER,
        opponent_team INTEGER,
        home_score INTEGER,
        away_score INTEGER,
        home BOOLEAN,
        bonus_points INTEGER,
        expected_goals REAL,
        expected_assists REAL,
        transfers_in INTEGER,
        transfers_out INTEGER,
        modified TEXT,
        kickoff_time TEXT,
        FOREIGN KEY (player_id) REFERENCES players(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS player_fixtures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        fixture_id INTEGER,
        event INTEGER,
        event_name TEXT,
        difficulty INTEGER,
        is_home INTEGER,
        team_h INTEGER,
        team_a INTEGER,
        team_h_score INTEGER,
        team_a_score INTEGER,
        finished INTEGER,
        started INTEGER,
        minutes INTEGER,
        provisional_start_time INTEGER,
        kickoff_time TEXT,
        code INTEGER,
        UNIQUE(player_id, fixture_id),
        FOREIGN KEY (player_id) REFERENCES players(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS player_history_past (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        season_name TEXT,
        total_points INTEGER,
        starts INTEGER,
        minutes INTEGER,
        starts_per_90 REAL,
        clean_sheets INTEGER,
        clean_sheets_per_90 REAL,
        goals_scored INTEGER,
        assists INTEGER,
        expected_goals REAL,
        expected_assists REAL,
        expected_goal_involvements REAL,
        expected_goals_conceded REAL,
        expected_goals_per_90 REAL,
        expected_assists_per_90 REAL,
        expected_goal_involvements_per_90 REAL,
        expected_goals_conceded_per_90 REAL,
        influence REAL,
        creativity REAL,
        threat REAL,
        ict_index REAL,
        bps INTEGER,
        bonus INTEGER,
        yellow_cards INTEGER,
        red_cards INTEGER,
        saves INTEGER,
        penalties_saved INTEGER,
        penalties_missed INTEGER,
        recoveries INTEGER,
        tackles INTEGER,
        defensive_contribution INTEGER,
        clearances_blocks_interceptions INTEGER,
        start_cost INTEGER,
        end_cost INTEGER,
        element_code INTEGER,
        UNIQUE(player_id, season_name),
        FOREIGN KEY (player_id) REFERENCES players(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS player_gw_snapshot (
        snapshot_time TEXT NOT NULL,
        season INTEGER,
        current_event INTEGER,
        next_event INTEGER,
        player_id INTEGER NOT NULL,
        status TEXT,
        chance_of_playing_next_round INTEGER,
        chance_of_playing_this_round INTEGER,
        now_cost REAL,
        selected_by_percent REAL,
        transfers_in_event INTEGER,
        transfers_out_event INTEGER,
        form REAL,
        points_per_game REAL,
        ep_next REAL,
        ep_this REAL,
        minutes INTEGER,
        starts INTEGER,
        news TEXT,
        news_added TEXT,
        PRIMARY KEY (snapshot_time, player_id),
        FOREIGN KEY (player_id) REFERENCES players(id)
    );
    """)

    # Lightweight migration for existing DBs.
    _ensure_columns(cur, "players", {
        "chance_of_playing_this_round": "chance_of_playing_this_round INTEGER",
        "news": "news TEXT",
        "news_added": "news_added TEXT",
        "ep_next": "ep_next REAL",
        "ep_this": "ep_this REAL",
    })

    _ensure_columns(cur, "events", {
        "is_current": "is_current INTEGER",
        "is_next": "is_next INTEGER",
    })

    _ensure_columns(cur, "fixtures", {
        "started": "started INTEGER",
        "provisional_start_time": "provisional_start_time INTEGER",
        "pulse_id": "pulse_id INTEGER",
    })

    _ensure_columns(cur, "player_history", {
        "minutes": "minutes INTEGER",
        "starts": "starts INTEGER",
        "bps": "bps INTEGER",
        "ict_index": "ict_index REAL",
        "influence": "influence REAL",
        "creativity": "creativity REAL",
        "threat": "threat REAL",
        "expected_goal_involvements": "expected_goal_involvements REAL",
        "expected_goals_conceded": "expected_goals_conceded REAL",
        "defensive_contribution": "defensive_contribution INTEGER",
        "recoveries": "recoveries INTEGER",
        "tackles": "tackles INTEGER",
        "clearances_blocks_interceptions": "clearances_blocks_interceptions INTEGER",
        "penalties_missed": "penalties_missed INTEGER",
        "penalties_saved": "penalties_saved INTEGER",
        "yellow_cards": "yellow_cards INTEGER",
        "red_cards": "red_cards INTEGER",
        "selected": "selected INTEGER",
        "transfers_balance": "transfers_balance INTEGER",
        "value": "value INTEGER",
        "fixture": "fixture INTEGER",
        "modified": "modified TEXT",
    })

    cur.execute("""
    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    # Performance indexes for prediction/backtest queries.
    cur.execute("CREATE INDEX IF NOT EXISTS idx_players_team_id ON players(team_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_finished ON events(finished)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_event ON fixtures(event)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_team_h_event ON fixtures(team_h, event)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_team_a_event ON fixtures(team_a, event)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_player_history_player_gw ON player_history(player_id, gameweek)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_player_history_gw ON player_history(gameweek)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_player_fixtures_player_event ON player_fixtures(player_id, event)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_player_fixtures_fixture_id ON player_fixtures(fixture_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_player_history_past_player ON player_history_past(player_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_player_gw_snapshot_player_time ON player_gw_snapshot(player_id, snapshot_time)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_player_gw_snapshot_event ON player_gw_snapshot(current_event, next_event)")

    conn.commit()
    conn.close()
