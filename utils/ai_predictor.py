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
    Sends a prompt to the LLM and expects a pure JSON object back.
    Uses OpenAI's response_format to enforce JSON and then parses it.
    Returns a dict:
      {
        "raw": original_text,
        "json": parsed_json_or_None,
        "error": error_message_or_None
      }
    """
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert Fantasy Premier League (FPL) analyst. "
                        "You MUST respond with a single valid JSON object only, "
                        "with no surrounding markdown or explanation."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as e:
        return {"raw": None, "json": None, "error": f"LLM request error: {e}"}

    raw = (response.choices[0].message.content or "").strip()

    try:
        parsed = json.loads(raw)
        return {"raw": raw, "json": parsed, "error": None}
    except json.JSONDecodeError as e:
        return {"raw": raw, "json": None, "error": f"JSON decode error: {e}"}


# -------------------------------------------------
# 1) TEAM-LEVEL ANALYSIS
# -------------------------------------------------

def build_team_prompt(team_json: Dict[str, Any]) -> str:
    """
    Build prompt for season-level team analysis / next-GW expectation.
    """
    return (
        "You are an expert Fantasy Premier League analyst.\n\n"
        "You will receive JSON for a single FPL team across the season. "
        "The JSON contains things like: entry_id, team_name, manager, total_points, "
        "rank history and a gw_data array with one object per gameweek "
        "(points, rank, transfers, chip, starting XI, bench, etc.).\n\n"
        "TASK:\n"
        "Based only on this JSON, estimate performance in the NEXT gameweek and "
        "summarize the key strengths and weaknesses of the team so far.\n\n"
        "You MUST respond with a JSON object with at least the following keys:\n"
        "- predicted_points: number (expected FPL points for the next GW)\n"
        "- key_players: array of objects with {\"id\": int, \"reason\": string}\n"
        "- weak_spots: array of strings (short bullet-style descriptions)\n"
        "- recommended_transfer: string (one concise suggestion or 'none')\n"
        "- confidence: one of 'low', 'medium', 'high'\n\n"
        "Use only the numbers and patterns you see in the JSON. "
        "Do not invent fixtures or external stats.\n\n"
        f"TEAM JSON:\n{json.dumps(team_json)}"
    )


def predict_team_performance(team_json: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_team_prompt(team_json)
    return ask_llm(prompt)


# -------------------------------------------------
# 2) PLAYER-LEVEL ANALYSIS
# -------------------------------------------------

def build_player_prompt(player_json: Dict[str, Any]) -> str:
    """
    Prompt for a single player's performance expectation.
    player_json can contain:
      - basic info (id, name, team, position)
      - per-gameweek stats (goals, assists, minutes, total_points, etc.)
    """
    return (
        "You are an FPL performance analyst.\n\n"
        "You will receive JSON describing one player: "
        "basic info plus per-gameweek stats from a local database.\n\n"
        "TASK:\n"
        "Estimate this player's expected FPL points in the NEXT gameweek, "
        "based on trends in recent matches (points, minutes, attacking returns).\n\n"
        "You MUST respond with a JSON object with at least:\n"
        "- expected_points: number\n"
        "- risk_level: 'low' | 'medium' | 'high'\n"
        "- reasoning: short string explaining the estimate using the given data\n\n"
        "Do not invent fixtures or extra stats. Only use the JSON.\n\n"
        f"PLAYER JSON:\n{json.dumps(player_json)}"
    )


def predict_player_performance(player_json: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_player_prompt(player_json)
    return ask_llm(prompt)


# -------------------------------------------------
# 3) SEASON-LONG TEAM COMPARISON
# -------------------------------------------------

def build_compare_prompt(team_a: Dict[str, Any], team_b: Dict[str, Any]) -> str:
    """
    Prompt for comparing two teams across the whole season.
    """
    return (
        "You are an expert FPL analyst.\n\n"
        "You will receive JSON for TWO different FPL teams, "
        "each with season history (points, ranks, transfers, chips, etc.).\n\n"
        "TASK:\n"
        "Compare the teams over the full season and decide who has been stronger so far.\n\n"
        "You MUST respond with a JSON object containing at least:\n"
        "- team_a_better_in: array of short strings\n"
        "- team_b_better_in: array of short strings\n"
        "- summary: short string comparing styles and strengths\n"
        "- overall_stronger_team: 'A' | 'B' | 'Even'\n\n"
        "Use ONLY the numbers and patterns in the JSON.\n\n"
        f"TEAM A JSON:\n{json.dumps(team_a)}\n\n"
        f"TEAM B JSON:\n{json.dumps(team_b)}"
    )


def compare_teams(team_a_json: Dict[str, Any], team_b_json: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_compare_prompt(team_a_json, team_b_json)
    return ask_llm(prompt)


# -------------------------------------------------
# 4) AI H2H PREDICTOR (GW-specific)
# -------------------------------------------------

def build_h2h_prompt(
    team_a: Dict[str, Any],
    team_b: Dict[str, Any],
    gw: int,
    mc_baseline: Optional[Dict[str, float]] = None,
) -> str:
    """
    Prompt for AI H2H prediction for a specific gameweek.
    Optional mc_baseline is a dict like:
      {"team_a_expected": float, "team_b_expected": float}
    coming from your numeric Monte Carlo model.
    """
    baseline_txt = json.dumps(mc_baseline) if mc_baseline is not None else "null"

    return (
        "You are an FPL head-to-head match analyst.\n\n"
        f"Target gameweek: {gw}.\n\n"
        "You will receive JSON for TEAM A and TEAM B, each containing season history "
        "plus per-GW details (points, ranks, transfers, chips, starting XI).\n"
        "You will also receive an OPTIONAL Monte Carlo baseline with expected points for "
        "this GW from a numeric model. It may be null.\n\n"
        "RULES:\n"
        "- Use ONLY the JSON and the numeric baseline if present.\n"
        "- Look especially at the last 4–6 GWs for trends (form, captain choices, hits).\n"
        "- Do not invent fixtures or odds outside what you can infer from the data.\n\n"
        "TASK:\n"
        "Predict this specific H2H outcome.\n\n"
        "You MUST respond with a JSON object containing at least:\n"
        "- gameweek: number\n"
        "- team_a_expected_points: number\n"
        "- team_b_expected_points: number\n"
        "- win_probabilities: object with numeric fields team_a, team_b, draw (0–100 each)\n"
        "- key_factors: array of short strings (why)\n"
        "- who_is_favored: 'A' | 'B' | 'Even'\n"
        "- confidence: 'low' | 'medium' | 'high'\n"
        "- based_on_monte_carlo: boolean\n\n"
        "TEAM SELECTION RULE:\n"
        "- You must treat ONLY players present in the LAST PLAYED GAMEWEEK (starting + bench) as the active roster for the upcoming GW.\n"
        "- DO NOT assume a player is on the team just because they appeared in older gameweeks.\n"
        "- Ignore players not present in latest_gw_squad.\n"
        f"TEAM A JSON:\n{json.dumps(team_a)}\n\n"
        f"TEAM B JSON:\n{json.dumps(team_b)}\n\n"
        f"MONTE CARLO BASELINE:\n{baseline_txt}"
    )

# -------------------------------------------------
# 5) AI CAPTAINCY ADVISOR
# -------------------------------------------------

def build_captaincy_prompt(
    gw: int,
    squad_players: List[Dict[str, Any]],
    context_team: Dict[str, Any],
) -> str:
    """
    squad_players: list of your players for the relevant GW, for example:
      [
        {
          "id": 177,
          "name": "Mohamed Salah",
          "team": "LIV",
          "pos": "MID",
          "gw_history": [... per-GW stats objects ...],
          "recent_form": float,
          "expected_minutes": int,
          "injury": bool,
          "suspended": bool,
          "rotation_risk": "low|medium|high|unknown"
        },
        ...
      ]
    context_team: your full season team_stats JSON, used to detect manager style.
    """
    return (
        "You are an FPL captaincy advisor.\n\n"
        f"Gameweek of interest: {gw}.\n\n"
        "You will receive:\n"
        "1) Full season context for the manager (TEAM JSON).\n"
        "2) A list of candidate players from this manager's current squad, "
        "with recent form, minutes, and simple flags (injury / suspension / rotation risk).\n\n"
        "RULES:\n"
        "- Use ONLY the provided stats. Do not invent fixtures or external injury info.\n"
        "- Focus on last 4–6 GWs for form.\n"
        "- Prefer nailed players with high expected minutes and strong recent form.\n"
        "- Vice-captain should be a stable alternative in case the captain does not play.\n\n"
        "TASK:\n"
        "Recommend CAPTAIN and VICE-CAPTAIN for this GW.\n\n"
        "You MUST respond with a JSON object containing at least:\n"
        "- gameweek: number\n"
        "- suggested_captain: object with fields id, name, reason\n"
        "- suggested_vice_captain: object with fields id, name, reason\n"
        "- other_viable_options: array of similar objects (id, name, reason)\n"
        "- notes: short string with any extra advice\n\n"
        f"TEAM CONTEXT JSON:\n{json.dumps(context_team)}\n\n"
        f"SQUAD PLAYERS JSON:\n{json.dumps(squad_players)}"
    )


def advise_captaincy(
    gw: int,
    squad_players: List[Dict[str, Any]],
    context_team: Dict[str, Any],
) -> Dict[str, Any]:
    prompt = build_captaincy_prompt(gw, squad_players, context_team)
    return ask_llm(prompt)


# -------------------------------------------------
# 6) AI TRANSFER RECOMMENDER
# -------------------------------------------------

def build_transfer_prompt(
    gw: int,
    current_team: Dict[str, Any],
    squad_state: Dict[str, Any],
    candidate_pool: List[Dict[str, Any]],
) -> str:
    """
    Build prompt for transfer advice.
    current_team: summary from build_team_json (bank, value, FDR map, etc.).
    squad_state: result from build_squad_state (squad list, club counts, free_transfers, bank).
    candidate_pool: reduced pool of good players (already cleaned / filtered).
    """
    return (
        "You are an advanced FPL transfer analyst.\n\n"
        f"Target gameweek: {gw}.\n\n"
        "You will receive three JSON blocks:\n"
        "1) TEAM JSON: season context, bank, team value, fixtures.\n"
        "2) SQUAD STATE: players currently owned (with form, minutes, flags), "
        "club_counts, free_transfers, bank.\n"
        "3) CANDIDATE POOL: list of strong players from the whole game, "
        "with price, form_last3, expected_minutes, injury/suspension flags, rotation_risk, "
        "and FDR for the next few gameweeks.\n\n"
        "You must obey standard FPL rules:\n"
        "- Budget: incoming_player.price <= outgoing_player.price + squad_state.bank\n"
        "- Position matching only: GK→GK, DEF→DEF, MID→MID, FWD→FWD\n"
        "- Max 3 players per club after transfers (use club_counts and team fields).\n"
        "- Never buy a player who is already owned.\n\n"
        "Transfer logic:\n"
        "- Suggest usually 1 transfer if free_transfers = 1.\n"
        "- You MAY suggest 2 transfers (-4 hit) if needed to afford a clearly better upgrade.\n"
        "- Never suggest more than 2 transfers or a hit worse than -4.\n"
        "- Prefer selling players with bad form, low minutes, clear rotation risk, "
        "suspension, or poor upcoming fixtures.\n"
        "- Prefer buying players with strong form, good minutes, low rotation risk, "
        "and good upcoming fixtures.\n\n"
        "Output:\n"
        "You MUST respond with a JSON object containing at least:\n"
        "- gameweek: number\n"
        "- suggested_transfers: array of objects with fields "
        "out_id, out_name, in_id, in_name, reason\n"
        "- hit_cost: number (0, 4, or possibly 8 if absolutely necessary)\n"
        "- rationale: short string explaining form, fixtures, nailedness and budget reasoning\n\n"
        "Use only UTF-8 characters, no escaped unicode sequences in names.\n\n"
        "TEAM JSON:\n"
        f"{json.dumps(current_team)}\n\n"
        "SQUAD STATE JSON:\n"
        f"{json.dumps(squad_state)}\n\n"
        "CANDIDATE POOL JSON:\n"
        f"{json.dumps(candidate_pool)}"
    )


# -------------------------------------------------
# 7) AI FREE HIT ADVISOR
# -------------------------------------------------

def build_freehit_prompt(
    gw: int,
    fh_state: Dict[str, Any],
    candidate_pool: List[Dict[str, Any]],
) -> str:
    """
    Build prompt for Free Hit squad construction.
    fh_state should contain:
      - budget: float
      - max_from_club: int (usually 3)
      - requirements: dict like {"GK":2,"DEF":5,"MID":5,"FWD":3}
    candidate_pool is a rich list of players with stats.
    """
    return (
        "You are an elite FPL strategist.\n\n"
        f"Your task is to build the best possible Free Hit squad for Gameweek {gw}.\n\n"
        "You will receive:\n"
        "- FH STATE: budget and positional requirements.\n"
        "- CANDIDATE POOL: list of players with team, position, price, form, minutes, "
        "injury/suspension flags, rotation risk and fixture difficulty for upcoming gameweeks.\n\n"
        "Free Hit rules:\n"
        f"- Budget: {fh_state.get('budget')} million total.\n"
        "- You must pick exactly the required number of players per position from fh_state.requirements.\n"
        "- Max 3 players per real-life club.\n"
        "- Prioritise nailed starters with strong recent form, good minutes, and good fixtures.\n"
        "- Avoid injured, suspended, or clear high-rotation players.\n\n"
        "Output:\n"
        "You MUST respond with a JSON object containing at least:\n"
        "- gameweek: number\n"
        "- budget_used: number\n"
        "- players: array of objects with fields id, name, team, position, price, reason\n"
        "- captain_id: id of selected captain\n"
        "- vice_id: id of selected vice-captain\n"
        "- summary: short string explaining the structure and key ideas\n\n"
        "FH STATE JSON:\n"
        f"{json.dumps(fh_state)}\n\n"
        "CANDIDATE POOL JSON:\n"
        f"{json.dumps(candidate_pool)}"
    )
