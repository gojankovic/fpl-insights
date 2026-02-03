# Testing Guide

This project uses `pytest` for automated tests. You can pass your own team and gameweek values without editing test files.

## Install test dependency

```bash
pip install -r requirements.txt
```

## Run all tests (defaults)

```bash
pytest -q
```

Defaults come from `tests/conftest.py`:
- team: `366,8,261,407,16,119,237,414,283,249,430`
- bench: `470,242,72,347`
- gw: `16`
- captain: `430`
- vice: `16`
- player-id: `414`

## Run tests with your own team

```bash
pytest -q \
  --team "1,2,3,4,5,6,7,8,9,10,11" \
  --bench "12,13,14,15" \
  --gw 22 \
  --captain 8 \
  --vice 4 \
  --player-id 177
```

Notes:
- `--team` must be 11 player IDs (starting XI).
- `--bench` should be 4 player IDs.
- `--player-id` is used in the player model test.

## Common issues

- If tests skip with a message about the SQLite DB, run `python update_fpl.py` first to generate/update `fpl.db`.

