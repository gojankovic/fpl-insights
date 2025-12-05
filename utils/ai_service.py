import json
from typing import Dict, Any, List, Optional

from utils.ai_data_builder import (
    load_team_json,
    build_squad_for_gw,
    build_team_json,
    build_squad_state,
    build_candidate_pool,
    reduce_candidate_pool_for_transfers,
)
from utils.ai_predictor import (
    predict_h2h,
    advise_captaincy,
    build_transfer_prompt, build_freehit_prompt,
)

from utils.ai_predictor import ask_llm
from utils.ai_service_helpers import sanitize_llm_transfer_output


# -------------------------------------------------
# AI SERVICE LAYER — clean and simple public API
# -------------------------------------------------

# -------------------------------------------------
# 1) H2H PREDICTION
# -------------------------------------------------

def h2h_prediction(entry_a: int, entry_b: int, gw: int,
                   mc_baseline: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    AI H2H predictor for a specific GW.

    Args:
        entry_a: ID prvog FPL tima
        entry_b: ID drugog FPL tima
        gw: gameweek koji analiziramo
        mc_baseline: opciono {"team_a_expected": x, "team_b_expected": y}

    Returns:
        Dict sa AI predikcijom H2H meča.
    """
    teamA = load_team_json(entry_a)
    teamB = load_team_json(entry_b)

    result = predict_h2h(teamA, teamB, gw, mc_baseline)
    return result



# -------------------------------------------------
# 2) CAPTAINCY ADVICE
# -------------------------------------------------

def captaincy_advice(entry_id: int, gw: int) -> Dict[str, Any]:
    """
    AI captaincy advisor for given GW.
    Uses squad of last completed GW before the target GW.
    """
    team_json = load_team_json(entry_id)
    squad = build_squad_for_gw(entry_id, gw)

    # Friendly for debugging:
    print(f"[AI] Captaincy analysis for GW{gw}, using squad from GW{squad[0]['last_gw_used']}.")

    return advise_captaincy(gw, squad, team_json)


# -------------------------------------------------
# 3) TRANSFER ADVICE
# -------------------------------------------------

def transfer_advice(entry_id: int, gw: int, candidate_pool_size: int = 120):
    """
    Main transfer advisor.
    Assembles dataset → reduces candidate pool → builds prompt → queries LLM → validates response.
    """

    # Build data sources
    team_json = build_team_json(entry_id)
    squad_state = build_squad_state(entry_id, gw)
    pool_full = build_candidate_pool(limit=candidate_pool_size, gw=gw)
    pool_reduced = reduce_candidate_pool_for_transfers(squad_state, pool_full)

    # Build prompt
    prompt = build_transfer_prompt(gw, team_json, squad_state, pool_reduced)

    # Ask LLM
    response = ask_llm(prompt)

    if response["error"]:
        return {
            "error": response["error"],
            "raw": response["raw"]
        }

    llm_json = response["json"]

    # Validate!
    sanitized = sanitize_llm_transfer_output(llm_json, squad_state, pool_reduced)

    return sanitized


# -------------------------------------------------
# 4) FREE HIT ADVICE
# -------------------------------------------------
def freehit_advice(gw: int, budget: float, pool_size: int = 150):
    """
    Free Hit AI builder:
    - Does NOT depend on user's existing team.
    - Builds full 15-man squad from scratch.
    """
    # Build candidate pool
    pool = build_candidate_pool(limit=pool_size, gw=gw)

    # Create simple FH state
    fh_state = {
        "target_gw": gw,
        "budget": budget,
        "max_from_club": 3,
        "requirements": {
            "GK": 2,
            "DEF": 5,
            "MID": 5,
            "FWD": 3
        }
    }

    print(f"[AI] Building Free Hit squad for GW{gw} with budget £{budget}m.")

    prompt = build_freehit_prompt(gw, fh_state, pool)
    resp = ask_llm(prompt)

    # If LLM failed completely
    if isinstance(resp, dict) and resp.get("error"):
        return {
            "error": resp["error"],
            "raw_response": resp.get("raw")
        }

    return resp


# -------------------------------------------------
# 5) ENTRY-POINT HELPERS (OPTIONAL)
# -------------------------------------------------

def pretty_print(obj: Dict[str, Any]):
    """Nice print in terminal."""
    print(json.dumps(obj, indent=2))

def validate_freehit_squad(squad: list):
    errors = []

    pos_count = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}
    seen = set()

    for p in squad:
        # count positions
        if p["pos"] not in pos_count:
            errors.append(f"Invalid position for {p['name']}: {p['pos']}")
        else:
            pos_count[p["pos"]] += 1

        # duplicate
        if p["id"] in seen:
            errors.append(f"Duplicate player: {p['name']}")
        seen.add(p["id"])

    if pos_count["GK"] != 2:
        errors.append(f"Expected 2 GKs, got {pos_count['GK']}")
    if pos_count["DEF"] != 5:
        errors.append(f"Expected 5 DEFs, got {pos_count['DEF']}")
    if pos_count["MID"] != 5:
        errors.append(f"Expected 5 MIDs, got {pos_count['MID']}")
    if pos_count["FWD"] != 3:
        errors.append(f"Expected 3 FWDs, got {pos_count['FWD']}")

    return errors