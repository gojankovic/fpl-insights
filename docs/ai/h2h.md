# AI H2H Predictor

The AI H2H module predicts a head-to-head result for a specific gameweek.

---

## Command

```
python ai.py h2h --teamA <id> --teamB <id> --gw <gw> [--mc]
```

Example:

```
python ai.py h2h --teamA 2709841 --teamB 3277875 --gw 15 --mc
```

`--mc` enables Monte Carlo baseline.

---

## Data Used

- Full season history for both teams via team_stats.json
- Particularly last 4–6 GWs for form trend analysis
- Starting XI and bench patterns
- Transfer aggression, chip usage
- Optional Monte Carlo expected values:
  ```
  {
    "team_a_expected": float,
    "team_b_expected": float
  }
  ```

AI uses only the last completed GW as valid squad composition.

---

## Output Format

Strict JSON:

```
{
  "gameweek": <int>,
  "team_a_expected_points": number,
  "team_b_expected_points": number,
  "win_probabilities": {
    "team_a": number,
    "team_b": number,
    "draw": number
  },
  "key_factors": ["string", ...],
  "who_is_favored": "A|B|Even",
  "confidence": "low|medium|high",
  "based_on_monte_carlo": true|false
}
```

---

## Logic Summary

- Trend analysis of points and ranks
- Captaincy effectiveness of each manager
- Reliability of players (minutes, form)
- Bench strength
- Stability vs volatility across GWs

If Monte Carlo baseline is provided, the model must anchor its reasoning to those expected values and avoid contradicting them.

