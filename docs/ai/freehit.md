# AI Free Hit Squad Builder

The AI Free Hit module constructs a complete 15-man squad for a specific gameweek.

---

## Command

```
python ai.py freehit --gw <gw> --budget <float> --pool <N>
```

Example:

```
python ai.py freehit --gw 15 --budget 102 --pool 150
```

---

## Data Used

- global candidate pool (players sorted by form, minutes, FDR, rotation risk)
- team constraints:
  - 2 GK
  - 5 DEF
  - 5 MID
  - 3 FWD
  - max 3 per real club
  - total cost ≤ budget

No existing team is needed; Free Hit is built from scratch.

---

## AI Logic

AI prioritizes:

- nailed starters (low rotation risk)
- good recent form
- high expected minutes
- favorable fixtures (low FDR avg)
- positional balance
- club spread

AI must select a captain and vice-captain based on ceiling and reliability.

---

## Output Format

Strict JSON:

```
{
  "gameweek": <int>,
  "budget_used": float,
  "players": [
    {
      "id": int,
      "name": "string",
      "team": "string",
      "position": "GK|DEF|MID|FWD",
      "price": float,
      "reason": "string"
    }
  ],
  "captain_id": int,
  "vice_id": int,
  "summary": "string"
}
```

---

## Notes

- AI is forbidden from selecting injured or suspended players.
- All selections must obey club and positional limits.
- Model does not guess lineups beyond available minutes data.

