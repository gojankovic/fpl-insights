# AI Transfer Advisor

The AI Transfer module recommends realistic transfers for a specific gameweek.  
It is fully aligned with real FPL rules.

---

## Command

```
python ai.py transfers --team <entry_id> --gw <gw> --pool <N>
```

Example:

```
python ai.py transfers --team 2709841 --gw 15 --pool 120
```

---

## Data Used

- last completed GW squad (GW–1)
- player price from SQLite
- bank value from team_stats.json
- club counts per team
- global candidate pool (filtered)
- injury/suspension flags
- fixture difficulty (FDR next 3–5 GWs)
- recent form (last 3 matches)
- expected minutes
- rotation risk estimate

---

## Model Constraints

AI must obey:

### Budget  
`incoming_price <= outgoing_price + bank`

### Position matching  
GK→GK, DEF→DEF, MID→MID, FWD→FWD

### Club limits  
Max 3 players per club after transfers.

### Hit rules  
- default: 1 transfer  
- may propose 2 transfers with a −4 hit only if long-term improvement is meaningful  
- never more than −4  

### Valid reasons to sell
- low recent form  
- low minutes  
- rotation risk  
- suspension  
- injury  
- bad upcoming fixtures  

### Valid reasons to buy
- strong form  
- nailed starter  
- expected minutes ≥ 60  
- fixture improvement  
- price efficiency  

---

## Output Format

```
{
  "gameweek": <int>,
  "suggested_transfers": [
    {
      "out_id": int,
      "out_name": "string",
      "in_id": int,
      "in_name": "string",
      "reason": "string"
    }
  ],
  "hit_cost": 0|4,
  "rationale": "string"
}
```

All transfers are validated by `ai_transfer_validator.py`.

