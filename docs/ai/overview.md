# AI Module Overview

The FPLInsights AI module provides natural-language analysis and recommendations using OpenAI models.  
All AI features operate strictly on locally stored data (SQLite + team_stats.json) without querying the FPL API at runtime.

The AI system currently supports:

- Captaincy advisor (per-GW)
- Transfer advisor (per-GW, budget/club/position aware)
- Free Hit squad builder
- H2H match predictor (optionally using Monte Carlo baseline)
- General team and player analysis

Each AI function follows strict JSON-only output, validated by the application layer.

---

## Data Sources Used by AI

AI prompts rely on:

1. **team_stats.json**  
   Exported via `team_stats.py`, containing:
   - gw_data (starting XI, bench, transfers, chip usage)
   - team value, bank
   - rank progression

2. **SQLite database (`fpl.db`)**  
   Includes:
   - players (name, team, position, now_cost, status)
   - player_history (minutes, points, goals, assists, etc.)
   - fixtures + FDR difficulty ratings

3. **Derived AI datasets**  
   - squad_state (form, minutes, injury/suspension flags)
   - candidate_pool (filtered global list of available players)
   - freehit_context (positional requirements and budget)
   - optional Monte Carlo baseline for H2H

---

## CLI Commands

AI utilities are executed via:

```
python ai.py <command> [options]
```

Available commands:

```
captaincy   --team <entry_id> --gw <gw>
transfers   --team <entry_id> --gw <gw> --pool <N>
freehit     --gw <gw> --pool <N> --budget <float>
h2h         --teamA <id> --teamB <id> --gw <gw> [--mc]
```

Each command prints valid JSON to stdout.

---

## Architecture Summary

AI features are implemented across several modules:

| File | Purpose |
|------|---------|
| `ai_predictor.py` | LLM prompt construction and low-level model wrapper |
| `ai_data_builder.py` | Builds squad_state, candidate_pool, FDR maps, and Free Hit contexts |
| `ai_service.py` | Public high-level AI interface used by CLI |
| `ai_transfer_validator.py` | Validates the JSON returned by the model for transfers |
| `ai_service_helpers.py` | Internal helpers shared by services |

---

## Environment Setup

Add your API key to `.env`:

```
OPENAI_API_KEY=your_key_here
```

AI uses the `OpenAI` Python client.

---

## Notes

- All prompts enforce strict JSON outputs.
- AI outputs are validated before returning to the user.
- Only the last fully completed GW is considered when predicting the next GW.
- No future fixture guessing is permitted beyond provided FDR.

