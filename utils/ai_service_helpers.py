from copy import deepcopy
from typing import Dict, Any, List

from utils.ai_transfer_validator import (
    validate_transfer_suggestion,
    apply_transfer_suggestion,
)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_forced_sell(player: Dict[str, Any]) -> bool:
    status = str(player.get("status") or "").lower()
    if status in {"i", "s", "u", "o"}:
        return True

    chance = _coerce_float(player.get("chance_of_playing_next_round"))
    if chance is not None and chance <= 50:
        return True

    exp_mins = _coerce_float(player.get("expected_minutes"))
    if exp_mins is not None and exp_mins <= 25:
        return True

    return False


def _get_projection_score(player: Dict[str, Any]) -> float | None:
    return (
        _coerce_float(player.get("fixture_adjusted_points"))
        or _coerce_float(player.get("predicted_points_gw"))
    )


def _find_player(players: List[Dict[str, Any]], player_id: Any) -> Dict[str, Any] | None:
    for p in players:
        if p.get("id") == player_id:
            return p
    return None


def sanitize_llm_transfer_output(
    llm_json: Dict[str, Any],
    squad_state: Dict[str, Any],
    candidate_pool: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Ensure LLM transfer output is valid.
    If invalid, return an error structure.

    Expected LLM JSON format:

    {
      "gameweek": 15,
      "suggested_transfers": [
        {
          "out_id": int,
          "out_name": "string",
          "in_id": int,
          "in_name": "string",
          "reason": "..."
        }
      ],
      "hit_cost": 0,
      "rationale": "..."
    }
    """
    if "suggested_transfers" not in llm_json:
        return {
            "error": "LLM did not return 'suggested_transfers'.",
            "raw": llm_json,
        }

    suggestions = llm_json["suggested_transfers"]
    if not suggestions:
        return {
            "error": "LLM returned an empty transfer suggestion list.",
            "raw": llm_json,
        }
    if not isinstance(suggestions, list):
        return {
            "error": "'suggested_transfers' must be a list.",
            "raw": llm_json,
        }

    free_tf = int(squad_state.get("free_transfers", 1))
    allowed_extra = int(
        squad_state.get("allowed_extra", squad_state.get("allowed_extra_transfers", 0))
    )
    max_transfers = free_tf + allowed_extra
    transfer_count = len(suggestions)

    if transfer_count > max_transfers:
        return {
            "error": (
                f"Too many transfers: proposed {transfer_count}, "
                f"maximum allowed is {max_transfers}."
            ),
            "raw": llm_json,
        }

    expected_hit_cost = max(0, transfer_count - free_tf) * 4
    hit_cost = llm_json.get("hit_cost")
    if hit_cost is None:
        return {
            "error": "LLM output is missing 'hit_cost'.",
            "raw": llm_json,
        }
    try:
        hit_cost = int(hit_cost)
    except (TypeError, ValueError):
        return {
            "error": "'hit_cost' must be a numeric value.",
            "raw": llm_json,
        }
    if hit_cost != expected_hit_cost:
        return {
            "error": (
                f"Invalid hit_cost: got {hit_cost}, expected {expected_hit_cost} "
                f"for {transfer_count} transfer(s) with {free_tf} free transfer(s)."
            ),
            "raw": llm_json,
        }

    state = deepcopy(squad_state)
    for idx, suggestion in enumerate(suggestions, start=1):
        if not isinstance(suggestion, dict):
            return {
                "error": f"Transfer #{idx} is not a valid object.",
                "raw": llm_json,
            }

        ok, reason = validate_transfer_suggestion(state, suggestion, candidate_pool)
        if not ok:
            return {
                "error": f"Invalid transfer #{idx}: {reason}",
                "raw": llm_json,
            }

        out_player = _find_player(state["squad"], suggestion.get("out_id"))
        in_player = _find_player(candidate_pool, suggestion.get("in_id"))
        if out_player is None or in_player is None:
            return {
                "error": f"Invalid transfer #{idx}: could not resolve players for projection check.",
                "raw": llm_json,
            }

        if not _is_forced_sell(out_player):
            out_score = _get_projection_score(out_player)
            in_score = _get_projection_score(in_player)
            if out_score is not None and in_score is not None and in_score <= out_score + 0.05:
                return {
                    "error": (
                        f"Invalid transfer #{idx}: incoming projection must improve "
                        f"the outgoing one ({in_score:.2f} <= {out_score:.2f})."
                    ),
                    "raw": llm_json,
                }

        applied, apply_reason = apply_transfer_suggestion(state, suggestion, candidate_pool)
        if not applied:
            return {
                "error": f"Could not apply transfer #{idx}: {apply_reason}",
                "raw": llm_json,
            }

    return {
        "json": llm_json,
        "error": None,
    }
