# AI Captaincy Advisor

The AI Captaincy module recommends captain and vice-captain choices for a specific gameweek.

---

## Command

```
python ai.py captaincy --team <entry_id> --gw <gw>
```

Example:

```
python ai.py captaincy --team 2709841 --gw 15
```

---

## Data Used

- Last completed GW (e.g. for GW 15 → use GW 14 squad)
- Per-player:
  - minutes history
  - total points history
  - short-term form (last 4–6 matches)
  - captaincy pattern of the manager
- Season context from team_stats.json

AI does not invent fixtures; it works only with available historical data and FDR.

---

## Output Format

Strict JSON:

```
{
  "gameweek": <int>,
  "suggested_captain": {
    "id": <int>,
    "name": "string",
    "reason": "string"
  },
  "suggested_vice_captain": {
    "id": <int>,
    "name": "string",
    "reason": "string"
  },
  "other_viable_options": [
    {
      "id": <int>,
      "name": "string",
      "reason": "string"
    }
  ],
  "notes": "string"
}
```

---

## Logic Summary

The model evaluates:

- recent form
- explosiveness (double-digit hauls)
- minutes reliability
- consistency vs volatility
- historical captaincy trends of the manager

The recommended captain is chosen for highest predictive ceiling; vice-captain is chosen for safe reliability.

