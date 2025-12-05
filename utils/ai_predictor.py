import os
import json
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

# -------------------------------------------------
# OpenAI client setup
# -------------------------------------------------

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)


# -------------------------------------------------
# LOW-LEVEL LLM WRAPPER
# -------------------------------------------------
def ask_llm(prompt: str) -> Dict[str, Any]:
    """
    Sends a prompt to the LLM and extracts JSON safely.
    Supports markdown fences like ```json ... ```
    Returns:
      {
        "raw": str,
        "json": dict | None,
        "error": str | None
      }
    """
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "You are an expert FPL analyst. Always output strict JSON."},
            {"role": "user", "content": prompt}
        ],
    )

    raw = response.choices[0].message.content.strip()

    # Step 1: extract JSON block from markdown fences
    if "```" in raw:
        parts = raw.split("```")
        # find any part that looks like JSON
        for part in parts:
            part = part.strip()
            if part.startswith("{") and part.endswith("}"):
                raw = part
                break

    # Step 2: fallback — find first "{" and last "}"
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw[start:end + 1]
    else:
        return {"raw": raw, "json": None, "error": "No JSON object found in response."}

    # Step 3: decode JSON
    try:
        parsed = json.loads(candidate)
        return {"raw": raw, "json": parsed, "error": None}
    except json.JSONDecodeError as e:
        return {"raw": raw, "json": None, "error": f"JSON decode error: {e}"}


# -------------------------------------------------
# BASIC
# -------------------------------------------------

def build_team_prompt(team_json: Dict[str, Any]) -> str:
    return f"""
You are an expert Fantasy Premier League analyst.

You will receive JSON representing one FPL team across all gameweeks
(exported from a local database, not from the official API).

This JSON typically has fields like:
- entry_id
- team_name
- manager
- total_points
- current_overall_rank
- chips (by GW)
- gw_data: array of gameweeks, each containing:
  - gw, points, overall_rank, gw_rank, transfers, transfer_cost, value, bank, chip
  - team: starting, bench, captain_id, vice_id, starting_total, bench_total

USAGE:
- Look at patterns of points, rank movement, chip usage, bench strength.
- Look at most consistent and explosive players in starting XIs.
- Look how aggressive the manager is with transfers and hits.

TASK:
Predict performance for the NEXT gameweek in a realistic way.
Do NOT hallucinate unknown fixtures. You don't know exact opponents or odds,
you only know how this manager's team has performed so far.

Respond STRICTLY with a JSON object:

{{
  "predicted_points": number,
  "key_players": [
    {{
      "id": int,
      "reason": "short explanation"
    }}
  ],
  "weak_spots": [
    "short bullet explanation"
  ],
  "recommended_transfer": "one concise suggestion, or 'none' if you cannot say",
  "confidence": "low|medium|high"
}}

Here is the team JSON:
{json.dumps(team_json)}
"""


def predict_team_performance(team_json: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_team_prompt(team_json)
    return ask_llm(prompt)


def build_player_prompt(player_json: Dict[str, Any]) -> str:
    """
    Prompt za jednog igrača (npr. history iz player_history).
    """
    return f"""
You are an FPL performance analyst.

Below is a JSON object describing a player's:
- basic info (id, name, team, position)
- per-gameweek stats from a local database (goals, assists, total_points, minutes, etc.)

Use ONLY this data. Do NOT invent fixtures, do NOT assume future transfers.

TASK:
Estimate this player's expected FPL points in the next gameweek,
based on trends: recent points, minutes, attacking/defensive returns.

Respond STRICTLY with JSON:

{{
  "expected_points": number,
  "risk_level": "low|medium|high",
  "reasoning": "short explanation using data from the JSON"
}}

Player JSON:
{json.dumps(player_json)}
"""


def predict_player_performance(player_json: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_player_prompt(player_json)
    return ask_llm(prompt)


def build_compare_prompt(team_a: Dict[str, Any], team_b: Dict[str, Any]) -> str:
    """
    Generalni prompt za poređenje dva tima (sezona).
    Ovo je više long-term stil, dok ćemo H2H ispod praviti GW-specific.
    """
    return f"""
You are an expert FPL analyst.

You are comparing TWO teams across their season data.
Each JSON is exported from a local database.

FIELDS:
Both teams have:
- meta: team_name, manager, total_points, current_overall_rank
- gw_data: per-GW history with points, rank, transfers, chips, starting XI etc.

TASK:
Make a SEASON-LONG comparison: who has been stronger so far and why.

Respond STRICTLY with JSON:

{{
  "team_a_better_in": ["short bullets"],
  "team_b_better_in": ["short bullets"],
  "summary": "short paragraph",
  "overall_stronger_team": "A|B|Even"
}}

TEAM A:
{json.dumps(team_a)}

TEAM B:
{json.dumps(team_b)}
"""


def compare_teams(team_a_json: Dict[str, Any], team_b_json: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_compare_prompt(team_a_json, team_b_json)
    return ask_llm(prompt)


# -------------------------------------------------
# AI H2H PREDICTOR (GW-specific)
# -------------------------------------------------

def build_h2h_prompt(
    team_a: Dict[str, Any],
    team_b: Dict[str, Any],
    gw: int,
    mc_baseline: Optional[Dict[str, float]] = None,
) -> str:
    """
    Prompt za AI H2H predict za KONKRETAN GW.

    mc_baseline je opciono:
      {{
        "team_a_expected": float,
        "team_b_expected": float
      }}
    iz tvog Monte Carlo modela, ako želiš da ga proslediš.
    """
    baseline_txt = json.dumps(mc_baseline) if mc_baseline else "null"

    return f"""
You are an FPL head-to-head match analyst.

You will receive:
- TEAM A JSON
- TEAM B JSON
Each JSON includes season data AND detailed info for each GW:
points, ranks, transfers, chip usage, starting XIs with player-level points.

You will ALSO receive optional Monte Carlo baseline expected points
for this specific gameweek from a separate numeric model.

Gameweek of interest: GW {gw}.

RULES:
- Use ONLY the JSON and the numeric baseline if provided.
- Look especially at the LAST 4-6 gameweeks for each team to understand trends.
- Consider captaincy patterns (aggressive vs safe), bench strength,
  and how often the manager's high-risk decisions paid off.
- Do NOT invent fixtures or odds. You are only predicting RELATIVE outcomes.

TASK:
Predict the H2H outcome for THIS GAMEWEEK, with confidence.

Respond STRICTLY with JSON:

{{
  "gameweek": {gw},
  "team_a_expected_points": number,
  "team_b_expected_points": number,
  "win_probabilities": {{
    "team_a": number,   // 0-100
    "team_b": number,   // 0-100
    "draw": number      // 0-100, all three should roughly sum to 100
  }},
  "key_factors": [
    "short bullet about main factor 1",
    "short bullet about main factor 2"
  ],
  "who_is_favored": "A|B|Even",
  "confidence": "low|medium|high",
  "based_on_monte_carlo": {str(mc_baseline is not None).lower()}
}}

TEAM A JSON:
{json.dumps(team_a)}

TEAM B JSON:
{json.dumps(team_b)}

MONTE CARLO BASELINE (can be null):
{baseline_txt}
"""


def predict_h2h(
    team_a_json: Dict[str, Any],
    team_b_json: Dict[str, Any],
    gw: int,
    mc_baseline: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    prompt = build_h2h_prompt(team_a_json, team_b_json, gw, mc_baseline)
    return ask_llm(prompt)


# -------------------------------------------------
# AI CAPTAINCY ADVISOR
# -------------------------------------------------

def build_captaincy_prompt(
    gw: int,
    squad_players: List[Dict[str, Any]],
    context_team: Dict[str, Any],
) -> str:
    """
    squad_players je lista igrača iz TVOG tima za taj GW, npr:
    [
      {
        "id": 177,
        "name": "Mohamed Salah",
        "team": "LIV",
        "pos": "MID",
        "gw_history": [... per-GW stats objects ...],
        "is_nailed": true/false,
        "injury_flag": "fit|doubt|out"
      },
      ...
    ]

    context_team je npr. tvoj team_stats.json (ceo), da vidi pattern kapitena.
    """
    return f"""
You are an FPL captaincy advisor.

You will receive:
1) Full season context for the manager (TEAM JSON).
2) A list of CANDIDATE PLAYERS from this manager's current squad,
   with per-gameweek stats and simple flags (nailed/injury).

Gameweek of interest: GW {gw}.

RULES:
- Use ONLY the given stats. Do not invent fixtures or odds.
- Focus on recent form (last 4-6 GWs), explosiveness (double-digit hauls),
  consistency (few blanks), and minutes reliability.
- Consider also how this manager usually picks captains (aggressive/safe).

TASK:
Recommend CAPTAIN and VICE-CAPTAIN for this gameweek.

Respond STRICTLY with JSON:

{{
  "gameweek": {gw},
  "suggested_captain": {{
    "id": int,
    "name": "string",
    "reason": "short explanation"
  }},
  "suggested_vice_captain": {{
    "id": int,
    "name": "string",
    "reason": "short explanation"
  }},
  "other_viable_options": [
    {{
      "id": int,
      "name": "string",
      "reason": "short explanation"
    }}
  ],
  "notes": "short extra advice if needed"
}}

TEAM CONTEXT JSON:
{json.dumps(context_team)}

SQUAD PLAYERS JSON:
{json.dumps(squad_players)}
"""


def advise_captaincy(
    gw: int,
    squad_players: List[Dict[str, Any]],
    context_team: Dict[str, Any],
) -> Dict[str, Any]:
    prompt = build_captaincy_prompt(gw, squad_players, context_team)
    return ask_llm(prompt)


# -------------------------------------------------
# AI TRANSFER RECOMMENDER
# -------------------------------------------------
def build_transfer_prompt(gw, current_team, squad_state, candidate_pool):
    """
    Final, optimized transfer prompt.
    All comments are removed inside the string so the model does not get distracted.
    """

    return f"""
You are an advanced FPL transfer analyst. 
Your task is to propose realistic, rules-accurate transfers for Gameweek {gw}.

============================================================
DATA AVAILABLE (DO NOT INVENT DATA)
============================================================
TEAM JSON  → season context, value, bank, transfers, fixtures.
SQUAD STATE → players owned, minutes, form, positional info, club counts.
CANDIDATE POOL → best available players with stats.

Use ONLY these data sources.

============================================================
STRICT FPL RULES YOU MUST OBEY
============================================================

BUDGET
- incoming_player.price ≤ outgoing_player.price + squad_state.bank

POSITION MATCHING
- GK→GK
- DEF→DEF
- MID→MID
- FWD→FWD

CLUB LIMIT
- After transfers: max 3 players per club.
- Use squad_state["club_counts"] to check limits.

OWNERSHIP RULE
- Never buy players already owned (use squad_state["squad"])

TRANSFER COUNT LOGIC
- If squad_state.free_transfers = 1 → normally suggest 1 transfer.
- You MAY suggest 2 transfers (-4 hit) if needed to afford a clearly superior improvement.
- Never propose more than 2 transfers.
- Never exceed a -4 hit.

SELL LOGIC (valid reasons to sell):
- poor recent form (low recent_form)
- low expected_minutes
- rotation risk ("rotation_risk" = "medium" or "high")
- suspension flag = true
- injury flag = true
- significantly worse upcoming fixtures (higher fdr_next5.avg_fdr)
- obvious downgrade compared to available alternatives at same price bracket

BUY LOGIC (valid reasons to buy):
- strong recent_form (clear trend across last 3–5 matches)
- expected_minutes ≥ 60
- nailed starter (rotation_risk = "low")
- good upcoming fixtures (low fdr_next5.avg_fdr)
- excellent value for price
- fits budget and positional structure
- improves team long-term

FIXTURE LOGIC (CRITICAL)
Use fdr_next5.avg_fdr:
- Lower avg_fdr = easier fixtures
Compare outgoing vs incoming fixtures:
- Prefer players with better next 3–5 GWs unless form strongly contradicts.

INJURY / SUSPENSION RULE
- Never call a player "injured" unless SQUAD STATE or CANDIDATE POOL explicitly shows "injury": true.
- If minutes = 0 but "injury" is false → treat neutrally (rest/rotation/suspension).
- If "suspended" = true → treat as suspension.

STYLE RULES
- Explanations must be short, clean, professional.
- Use plain UTF-8. Do not use escaped unicode or escaped symbols.
- Names like "Marcos Senesi Barón" must appear exactly as written.

============================================================
OUTPUT FORMAT (STRICT JSON ONLY)
============================================================

Return EXACTLY this structure:

{{
  "gameweek": {gw},
  "suggested_transfers": [
    {{
      "out_id": int,
      "out_name": "string",
      "in_id": int,
      "in_name": "string",
      "reason": "clear, short explanation"
    }}
  ],
  "hit_cost": 0,
  "rationale": "short summary explaining form, fixtures, nailedness, budget logic"
}}

No extra keys. No narrative text.

============================================================
TEAM JSON:
============================================================
{json.dumps(current_team)}

============================================================
SQUAD STATE JSON:
============================================================
{json.dumps(squad_state)}

============================================================
CANDIDATE POOL JSON:
============================================================
{json.dumps(candidate_pool)}
"""

# -------------------------------------------------
# AI FREE HIT ADVISOR (GW-specific)
# -------------------------------------------------
def build_freehit_prompt(gw: int, fh_state: Dict[str, Any], candidate_pool: List[Dict[str, Any]]):
    """
    Builds prompt instructing LLM to construct a Free Hit squad.
    """
    return f"""
You are an elite FPL strategist.
Your task is to build the best possible Free Hit squad for Gameweek {gw}.

===============================
FREE HIT RULES
===============================
1) Budget: {fh_state["budget"]} million.
2) You must pick exactly:
   - 2 GKs
   - 5 DEFs
   - 5 MIDs
   - 3 FWDs
3) Max 3 players per club.
4) Prioritise:
   - nailed starters
   - strong recent form
   - favourable fixtures (FDR next 3–5 GWs)
   - high expected minutes
   - no injuries or doubts
5) Include captain_id + vice_id.
6) Output STRICT JSON, no explanation text outside JSON.

===============================
OUTPUT JSON FORMAT
===============================
{{
  "gameweek": {gw},
  "budget_used": float,
  "players": [
    {{
      "id": int,
      "name": "string",
      "team": "string",
      "position": "GK/DEF/MID/FWD",
      "price": float,
      "reason": "short explanation"
    }}
  ],
  "captain_id": int,
  "vice_id": int,
  "summary": "short rationale"
}}

CANDIDATE POOL:
{json.dumps(candidate_pool)}
"""
