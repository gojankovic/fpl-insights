import json
from typing import Dict, Any, Optional

from utils.ai_data_builder import (
    build_squad_for_gw,
    build_team_json,
    build_squad_state,
    build_candidate_pool,
    reduce_candidate_pool_for_transfers,
)
from utils.ai_predictor import (
    ask_llm,
    build_captaincy_prompt,
    build_transfer_prompt,
    build_freehit_prompt,
)
from utils.ai_service_helpers import sanitize_llm_transfer_output
from utils.ai_predictor import build_h2h_prompt, ask_llm
from utils.ai_data_builder import load_team_json

# -------------------------------------------------
# CAPTAINCY ADVICE
# -------------------------------------------------


def captaincy_advice(entry_id: int, gw: int) -> Dict[str, Any]:
    """
    High-level service:
    - builds squad for target GW (using GW-1),
    - builds compact team context,
    - asks LLM for captaincy advice.
    """
    team_ctx = build_team_json(entry_id)
    squad = build_squad_for_gw(entry_id, gw)

    use_gw = squad[0]["last_gw_used"] if squad else gw - 1
    print(f"[AI] Captaincy analysis for GW{gw}, using squad from GW{use_gw}.")

    prompt = build_captaincy_prompt(gw, squad, team_ctx)
    rsp = ask_llm(prompt)

    if rsp["error"]:
        return {
            "error": rsp["error"],
            "raw": rsp["raw"],
        }

    return rsp["json"]


# -------------------------------------------------
# TRANSFER ADVICE
# -------------------------------------------------


def transfer_advice(
    entry_id: int,
    gw: int,
    candidate_pool_size: int = 120,
) -> Dict[str, Any]:
    """
    High-level service for transfer recommendations.

    Steps:
    - Build team context
    - Build squad_state for GW-1
    - Build global candidate pool
    - Reduce candidate pool (status, 3-per-club, etc.)
    - Build transfer prompt
    - Ask LLM
    - Validate output (position, budget, 3-per-club)
    """
    team_ctx = build_team_json(entry_id)
    squad_state = build_squad_state(entry_id, gw)
    pool_full = build_candidate_pool(limit=candidate_pool_size, gw=gw)
    pool_reduced = reduce_candidate_pool_for_transfers(squad_state, pool_full)

    print(
        f"[AI] Transfer advice for GW{gw}, "
        f"using last completed squad & bank from team_stats.json."
    )

    prompt = build_transfer_prompt(gw, team_ctx, squad_state, pool_reduced)
    rsp = ask_llm(prompt)

    if rsp["error"]:
        return {
            "error": rsp["error"],
            "raw": rsp["raw"],
        }

    # Validate the suggestion
    sanitized = sanitize_llm_transfer_output(
        rsp["json"],
        squad_state,
        pool_reduced,
    )

    return sanitized


# -------------------------------------------------
# FREE HIT ADVICE (GLOBAL, NO ENTRY)
# -------------------------------------------------
def freehit_advice(
    gw: int,
    candidate_pool_size: int = 150,
    budget: float = 100.0,
) -> Dict[str, Any]:
    """
    High-level service for Free Hit squad generation.
    Global — does NOT depend on a specific team.
    """

    # Build raw candidate pool
    pool_full = build_candidate_pool(limit=candidate_pool_size, gw=gw)

    # Filter obvious no-play players if we have status
    pool_filtered = [
        p for p in pool_full
        if p.get("status") not in ("i", "s", "u")  # injury/susp/unavailable
    ]

    # Build Free Hit state block
    fh_state = {
        "budget": budget,
        "max_from_club": 3,
        "requirements": {
            "GK": 2,
            "DEF": 5,
            "MID": 5,
            "FWD": 3
        }
    }

    print(
        f"[AI] Free Hit team generation for GW{gw} with budget {budget}, "
        f"using {len(pool_filtered)} candidates."
    )

    prompt = build_freehit_prompt(gw, fh_state, pool_filtered)
    rsp = ask_llm(prompt)

    if rsp["error"]:
        return {
            "error": rsp["error"],
            "raw": rsp["raw"],
        }

    return rsp["json"]


# -------------------------------------------------
# H2H prediction
# -------------------------------------------------
def h2h_prediction(
    entry_a: int,
    entry_b: int,
    gw: int,
    mc_baseline: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    High-level H2H predictor.
    Loads team data, builds prompt, queries LLM, returns parsed JSON.
    """

    team_a = load_team_json(entry_a)
    team_b = load_team_json(entry_b)

    if mc_baseline:
        print(f"[AI] Using Monte Carlo baseline: {mc_baseline}")

    print(f"[AI] H2H prediction for GW{gw}: {entry_a} vs {entry_b}")

    prompt = build_h2h_prompt(
        team_a=team_a,
        team_b=team_b,
        gw=gw,
        mc_baseline=mc_baseline
    )

    rsp = ask_llm(prompt)

    if rsp["error"]:
        return {
            "error": rsp["error"],
            "raw": rsp["raw"]
        }

    return rsp["json"]

