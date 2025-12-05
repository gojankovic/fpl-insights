from typing import Dict, Any, List

from utils.ai_transfer_validator import validate_transfer_suggestion


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

    first = suggestions[0]
    ok, reason = validate_transfer_suggestion(squad_state, first, candidate_pool)

    if not ok:
        return {
            "error": f"Invalid suggestion: {reason}",
            "raw": llm_json,
        }

    return {
        "json": llm_json,
        "error": None,
    }
