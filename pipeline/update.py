from pathlib import Path
import json
import time

from db.sqlite import init_db, get_connection
from pipeline.fetch import (
    fetch_bootstrap_static,
    fetch_fixtures,
    fetch_player_summary,
    create_session,
)
from pipeline.normalize import (
    normalize_teams,
    normalize_players,
    normalize_events,
    normalize_fixtures,
    normalize_player_history,
)
from pipeline.load_to_sqlite import (
    replace_teams,
    replace_players,
    replace_events,
    replace_fixtures,
    replace_player_history,
)
from pipeline.schema_checker import check_schema_change

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def update_fpl_data():
    print("Initializing DB schema...")
    init_db()

    print("Fetching bootstrap-static...")
    bootstrap = fetch_bootstrap_static(write=False)
    check_schema_change(RAW_DIR, "bootstrap_static", bootstrap)
    (RAW_DIR / "bootstrap_static.json").write_text(
        json.dumps(bootstrap, indent=2),
        encoding="utf-8",
    )

    print("Fetching fixtures...")
    fixtures_raw = fetch_fixtures()

    print("Normalizing teams/players/events/fixtures...")
    teams_rows = normalize_teams(bootstrap)
    players_rows = normalize_players(bootstrap)
    events_rows = normalize_events(bootstrap)
    fixtures_rows = normalize_fixtures(fixtures_raw)

    conn = get_connection()
    try:
        conn.execute("BEGIN")
        print("Writing teams...")
        replace_teams(teams_rows, conn=conn)

        print("Writing players...")
        replace_players(players_rows, conn=conn)

        print("Writing events...")
        replace_events(events_rows, conn=conn)

        print("Writing fixtures...")
        replace_fixtures(fixtures_rows, conn=conn)

        print("Fetching player history (this might take a while)...")
        all_history_rows = []
        session = create_session()
        for p in bootstrap["elements"]:
            pid = p["id"]
            summary = fetch_player_summary(pid, session=session)
            all_history_rows.extend(normalize_player_history(pid, summary))
            time.sleep(0.1)

        print("Writing player history...")
        replace_player_history(all_history_rows, conn=conn)

        conn.commit()
    finally:
        conn.close()

    print("Done. fpl.db is updated.")
